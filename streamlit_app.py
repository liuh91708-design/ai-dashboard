import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Nasdaq 盯盘版 Dashboard", layout="wide")

st.title("🚀 Nasdaq 盯盘版 Dashboard")
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

mode = st.sidebar.radio(
    "查看模式",
    ["全部", "只看机会", "只看风险"],
    index=0
)

signal_filter = st.sidebar.multiselect(
    "筛选信号",
    ["🔥 强势流入", "⚠️ 放量下跌", "💤 弱上涨", "🧨 弱势"],
    default=["🔥 强势流入", "⚠️ 放量下跌", "💤 弱上涨", "🧨 弱势"]
)

min_change = st.sidebar.slider("最小涨跌幅绝对值 (%)", 0.0, 20.0, 0.0, 0.5)

refresh = st.sidebar.button("🔄 手动刷新数据")

@st.cache_data(ttl=600)
def load_data(tickers, period):
    return yf.download(
        tickers,
        period=period,
        group_by="ticker",
        auto_adjust=True,
        progress=False
    )

if refresh:
    st.cache_data.clear()

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
            volume_ratio = volume / avg_volume
            money_momentum = change * volume

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
filtered_df = filtered_df[filtered_df["Change %"].abs() >= min_change]

if mode == "只看机会":
    filtered_df = filtered_df[filtered_df["Signal"] == "🔥 强势流入"]
elif mode == "只看风险":
    filtered_df = filtered_df[filtered_df["Signal"] == "⚠️ 放量下跌"]

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

c1, c2, c3, c4 = st.columns(4)

if not index_df.empty:
    qqq_change = index_df[index_df["Index"] == "QQQ"]["Change %"].iloc[0]
    spy_change = index_df[index_df["Index"] == "SPY"]["Change %"].iloc[0]
    c1.metric("QQQ", f"{qqq_change:.2f}%")
    c2.metric("SPY", f"{spy_change:.2f}%")
else:
    c1.metric("QQQ", "N/A")
    c2.metric("SPY", "N/A")

strong_count = len(df[df["Signal"] == "🔥 强势流入"])
risk_count = len(df[df["Signal"] == "⚠️ 放量下跌"])

c3.metric("强势 / 风险", f"{strong_count} / {risk_count}")
c4.metric("更新时间", datetime.now().strftime("%H:%M:%S"))

sector_flow = df.groupby("Sector")["Momentum"].sum().reset_index()

st.subheader("🏦 板块资金流（百万单位）")

fig_sector = px.bar(
    sector_flow.sort_values("Momentum", ascending=False),
    x="Sector",
    y="Momentum",
    text="Momentum",
    title="板块资金动量"
)
st.plotly_chart(fig_sector, use_container_width=True)

st.subheader("🧠 自动市场结论")

top_sector = sector_flow.sort_values("Momentum", ascending=False).iloc[0]
total_flow = sector_flow["Momentum"].sum()

if total_flow > 0 and strong_count > risk_count:
    market_status = "风险偏好（Risk ON）"
elif total_flow < 0 and risk_count > strong_count:
    market_status = "风险规避（Risk OFF）"
else:
    market_status = "分化震荡"

st.success(f"""
🔥 主导板块：{top_sector["Sector"]}

📊 市场状态：{market_status}

👉 当前资金主要集中在 **{top_sector["Sector"]}**。
""")

st.subheader("🚨 实时预警")

alerts = []

for _, row in df.iterrows():
    if row["Signal"] == "🔥 强势流入" and row["Change %"] >= 3:
        alerts.append(f"🔥 {row['Ticker']} 强势流入：涨幅 {row['Change %']}%，量能倍率 {row['Volume Ratio']}")

    if row["Signal"] == "⚠️ 放量下跌" and row["Change %"] <= -3:
        alerts.append(f"⚠️ {row['Ticker']} 放量下跌：跌幅 {row['Change %']}%，量能倍率 {row['Volume Ratio']}")

if alerts:
    for alert in alerts:
        st.warning(alert)
else:
    st.info("暂无强预警信号。")

st.subheader("🎯 今日重点标的")

top_opportunities = df[df["Signal"] == "🔥 强势流入"].sort_values("Score", ascending=False).head(5)
top_risks = df[df["Signal"] == "⚠️ 放量下跌"].sort_values("Momentum", ascending=True).head(5)

left, right = st.columns(2)

with left:
    st.markdown("### 🔥 Top 机会榜")
    st.dataframe(
        top_opportunities[["Ticker", "Sector", "Price", "Change %", "Volume Ratio", "Momentum", "Score"]],
        use_container_width=True
    )

with right:
    st.markdown("### ⚠️ Top 风险榜")
    st.dataframe(
        top_risks[["Ticker", "Sector", "Price", "Change %", "Volume Ratio", "Momentum", "Score"]],
        use_container_width=True
    )

st.subheader("📊 个股资金信号")

st.dataframe(
    filtered_df.sort_values("Score", ascending=False),
    use_container_width=True
)

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

st.info("""
信号解释：

🔥 强势流入 = 上涨 + 成交量高于均量  
⚠️ 放量下跌 = 下跌 + 成交量高于均量  
💤 弱上涨 = 上涨但量能一般  
🧨 弱势 = 下跌且缺乏强势资金  

注意：这不是机构真实净流入，只是基于价格和成交量的估算模型。
""")
