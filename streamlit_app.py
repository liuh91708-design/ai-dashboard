import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

st.set_page_config(page_title="Nasdaq 交易监控 Dashboard", layout="wide")

st.title("🚀 Nasdaq 交易监控 Dashboard")
st.caption("资金流为估算指标：涨跌幅 × 成交量，仅供研究，不构成投资建议。")

SECTORS = {
    "AI/半导体": ["NVDA", "AMD", "AVGO", "QCOM", "TXN", "MU", "AMAT", "LRCX", "ADI"],
    "云计算/软件": ["MSFT", "AMZN", "GOOGL", "ADBE", "INTU", "PANW"],
    "平台/消费科技": ["AAPL", "META", "NFLX", "BKNG"],
    "电动车/成长": ["TSLA"],
    "防御/消费": ["COST", "PEP"],
    "医疗科技": ["AMGN", "ISRG", "VRTX"],
    "通信/网络": ["CSCO", "TMUS"]
}

ALL_TICKERS = sorted(list(set(sum(SECTORS.values(), []))))
INDEX_TICKERS = ["QQQ", "SPY"]

period = st.sidebar.selectbox("周期", ["5d", "1mo", "3mo", "6mo", "1y"], index=1)
signal_filter = st.sidebar.multiselect(
    "筛选信号",
    ["🔥 强势流入", "⚠️ 放量下跌", "💤 弱上涨", "🧨 弱势"],
    default=["🔥 强势流入", "⚠️ 放量下跌", "💤 弱上涨", "🧨 弱势"]
)

@st.cache_data(ttl=600)
def load_data(tickers, period):
    return yf.download(
        tickers,
        period=period,
        group_by="ticker",
        auto_adjust=True,
        progress=False
    )

def get_single_df(data, ticker):
    if isinstance(data.columns, pd.MultiIndex):
        return data[ticker].dropna()
    return data.dropna()

data = load_data(ALL_TICKERS + INDEX_TICKERS, period)

rows = []

for sector, tickers in SECTORS.items():
    for t in tickers:
        try:
            df0 = get_single_df(data, t)

            close_now = df0["Close"].iloc[-1]
            close_prev = df0["Close"].iloc[0]
            volume = df0["Volume"].iloc[-1]
            avg_volume = df0["Volume"].mean()

            change = close_now / close_prev - 1
            money_momentum = change * volume
            volume_ratio = volume / avg_volume

            if change > 0 and volume_ratio > 1:
                signal = "🔥 强势流入"
            elif change < 0 and volume_ratio > 1:
                signal = "⚠️ 放量下跌"
            elif change > 0:
                signal = "💤 弱上涨"
            else:
                signal = "🧨 弱势"

            score = change * 100 + volume_ratio * 2 + money_momentum / 1e7

            rows.append({
                "Ticker": t,
                "Sector": sector,
                "Price": round(close_now, 2),
                "Change %": round(change * 100, 2),
                "Volume Ratio": round(volume_ratio, 2),
                "Momentum": round(money_momentum / 1e6, 2),
                "Score": round(score, 2),
                "Signal": signal
            })

        except Exception:
            pass

df = pd.DataFrame(rows)

if df.empty:
    st.error("数据获取失败，请刷新页面或稍后再试。")
    st.stop()

filtered_df = df[df["Signal"].isin(signal_filter)]

# 指数对照
index_rows = []
for idx in INDEX_TICKERS:
    try:
        idx_df = get_single_df(data, idx)
        idx_change = idx_df["Close"].iloc[-1] / idx_df["Close"].iloc[0] - 1
        index_rows.append({
            "Index": idx,
            "Change %": round(idx_change * 100, 2)
        })
    except Exception:
        pass

index_df = pd.DataFrame(index_rows)

st.subheader("📌 市场基准")
c1, c2, c3 = st.columns(3)

if not index_df.empty:
    qqq_change = index_df[index_df["Index"] == "QQQ"]["Change %"].iloc[0]
    spy_change = index_df[index_df["Index"] == "SPY"]["Change %"].iloc[0]
    c1.metric("QQQ", f"{qqq_change:.2f}%")
    c2.metric("SPY", f"{spy_change:.2f}%")
else:
    c1.metric("QQQ", "N/A")
    c2.metric("SPY", "N/A")

strong_count = len(df[df["Signal"] == "🔥 强势流入"])
weak_count = len(df[df["Signal"] == "⚠️ 放量下跌"])
c3.metric("强势 / 放量下跌", f"{strong_count} / {weak_count}")

# 板块资金
sector_flow = df.groupby("Sector")["Momentum"].sum().reset_index()

st.subheader("🏦 板块资金流（百万单位）")
fig_sector = px.bar(
    sector_flow.sort_values("Momentum", ascending=False),
    x="Sector",
    y="Momentum",
    text="Momentum"
)
st.plotly_chart(fig_sector, use_container_width=True)

# 市场结论
st.subheader("🧠 自动市场结论")

top_sector = sector_flow.sort_values("Momentum", ascending=False).iloc[0]
total_flow = sector_flow["Momentum"].sum()

if total_flow > 0 and strong_count > weak_count:
    mood = "风险偏好（Risk ON）"
elif total_flow < 0 and weak_count > strong_count:
    mood = "风险规避（Risk OFF）"
else:
    mood = "分化震荡"

st.success(f"""
🔥 主导板块：{top_sector['Sector']}

📊 市场状态：{mood}

👉 当前资金主要集中在 **{top_sector['Sector']}**。
""")

# 今日重点标的
st.subheader("🎯 今日重点标的")

top_long = df[df["Signal"] == "🔥 强势流入"].sort_values("Score", ascending=False).head(5)
top_risk = df[df["Signal"] == "⚠️ 放量下跌"].sort_values("Momentum").head(5)

left, right = st.columns(2)

with left:
    st.markdown("### 🔥 候选做多 / 强势观察")
    st.dataframe(top_long[["Ticker", "Sector", "Change %", "Volume Ratio", "Momentum", "Score"]], use_container_width=True)

with right:
    st.markdown("### ⚠️ 风险 / 出货观察")
    st.dataframe(top_risk[["Ticker", "Sector", "Change %", "Volume Ratio", "Momentum", "Score"]], use_container_width=True)

# 个股表格
st.subheader("📊 个股资金信号")
st.dataframe(
    filtered_df.sort_values("Score", ascending=False),
    use_container_width=True
)

# 市场结构图
st.subheader("🧭 市场结构图")
fig = px.scatter(
    filtered_df,
    x="Change %",
    y="Momentum",
    color="Sector",
    size="Volume Ratio",
    hover_name="Ticker",
    text="Ticker",
    title="涨跌幅 × 资金动量 × 成交量倍率"
)
fig.update_traces(textposition="top center")
st.plotly_chart(fig, use_container_width=True)

# 信号说明
st.info("""
信号解释：
🔥 强势流入 = 上涨 + 成交量高于均量  
⚠️ 放量下跌 = 下跌 + 成交量高于均量  
💤 弱上涨 = 上涨但量能一般  
🧨 弱势 = 下跌且缺乏强势资金  
""")
