import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Nasdaq 趋势评分盯盘版", layout="wide")

st.title("🚀 Nasdaq 趋势评分盯盘版 Dashboard")
st.caption("资金流、趋势评分为估算模型，仅供研究，不构成投资建议。")

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
    ["全部", "只看机会", "只看风险", "只看强趋势"],
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

            if len(df0) < 5:
                continue

            close_now = df0["Close"].iloc[-1]
            close_prev = df0["Close"].iloc[0]
            volume = df0["Volume"].iloc[-1]
            avg_volume = df0["Volume"].mean()

            change = close_now / close_prev - 1
            volume_ratio = volume / avg_volume
            money_momentum = change * volume

            recent_close = df0["Close"].tail(5)
            recent_returns = recent_close.pct_change().dropna()

            up_days = int((recent_returns > 0).sum())
            down_days = int((recent_returns < 0).sum())

            recent_volume = df0["Volume"].tail(5)
            volume_strength = recent_volume.iloc[-1] / recent_volume.mean()

            ma5 = df0["Close"].rolling(5).mean().iloc[-1]
            ma20 = df0["Close"].rolling(20).mean().iloc[-1] if len(df0) >= 20 else ma5

            if close_now > ma5 and ma5 >= ma20:
                trend = "上升趋势"
                trend_base = 2
            elif close_now < ma5 and ma5 <= ma20:
                trend = "下降趋势"
                trend_base = -2
            else:
                trend = "震荡"
                trend_base = 0

            if change > 0 and volume_ratio > 1:
                signal = "🔥 强势流入"
            elif change < 0 and volume_ratio > 1:
                signal = "⚠️ 放量下跌"
            elif change > 0:
                signal = "💤 弱上涨"
            else:
                signal = "🧨 弱势"

            trend_score = (
                trend_base * 10
                + up_days * 3
                - down_days * 3
                + volume_strength * 2
                + change * 100
            )

            risk_score = (
                down_days * 4
                + max(-change * 100, 0)
                + (volume_ratio * 2 if change < 0 else 0)
            )

            score = change * 100 + volume_ratio * 2 + money_momentum / 1e7 + trend_score

            rows.append({
                "Ticker": t,
                "Sector": sector,
                "Price": round(close_now, 2),
                "Change %": round(change * 100, 2),
                "Volume Ratio": round(volume_ratio, 2),
                "Momentum": round(money_momentum / 1e6, 2),
                "Trend": trend,
                "Up Days(5)": up_days,
                "Down Days(5)": down_days,
                "Trend Score": round(trend_score, 2),
                "Risk Score": round(risk_score, 2),
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
elif mode == "只看强趋势":
    filtered_df = filtered_df[filtered_df["Trend Score"] > 20]

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
sector_trend = df.groupby("Sector")["Trend Score"].mean().reset_index()

st.subheader("🏦 板块资金流（百万单位）")

fig_sector = px.bar(
    sector_flow.sort_values("Momentum", ascending=False),
    x="Sector",
    y="Momentum",
    text="Momentum",
    title="板块资金动量"
)
st.plotly_chart(fig_sector, use_container_width=True)

st.subheader("📈 板块趋势评分")

fig_sector_trend = px.bar(
    sector_trend.sort_values("Trend Score", ascending=False),
    x="Sector",
    y="Trend Score",
    text="Trend Score",
    title="板块平均趋势评分"
)
st.plotly_chart(fig_sector_trend, use_container_width=True)

st.subheader("🧠 自动市场结论")

top_sector = sector_flow.sort_values("Momentum", ascending=False).iloc[0]
top_trend_sector = sector_trend.sort_values("Trend Score", ascending=False).iloc[0]
total_flow = sector_flow["Momentum"].sum()
avg_trend_score = df["Trend Score"].mean()

if total_flow > 0 and strong_count > risk_count and avg_trend_score > 10:
    market_status = "风险偏好（Risk ON）+ 趋势增强"
elif total_flow < 0 and risk_count > strong_count:
    market_status = "风险规避（Risk OFF）"
elif avg_trend_score > 10:
    market_status = "趋势偏强，但资金分化"
else:
    market_status = "分化震荡"

st.success(f"""
🔥 资金主导板块：{top_sector["Sector"]}

📈 趋势最强板块：{top_trend_sector["Sector"]}

📊 市场状态：{market_status}

👉 当前市场重点观察 **{top_sector["Sector"]}** 与 **{top_trend_sector["Sector"]}**。
""")

st.subheader("🚨 实时预警")

alerts = []

for _, row in df.iterrows():
    if row["Signal"] == "🔥 强势流入" and row["Change %"] >= 3 and row["Trend Score"] > 20:
        alerts.append(f"🔥 {row['Ticker']} 强势趋势：涨幅 {row['Change %']}%，趋势评分 {row['Trend Score']}")

    if row["Signal"] == "⚠️ 放量下跌" and row["Change %"] <= -3 and row["Risk Score"] > 10:
        alerts.append(f"⚠️ {row['Ticker']} 风险加速：跌幅 {row['Change %']}%，风险评分 {row['Risk Score']}")

if alerts:
    for alert in alerts:
        st.warning(alert)
else:
    st.info("暂无强预警信号。")

st.subheader("🎯 今日重点标的")

top_opportunities = df[df["Signal"] == "🔥 强势流入"].sort_values("Score", ascending=False).head(5)
top_trends = df.sort_values("Trend Score", ascending=False).head(5)
top_risks = df[df["Signal"] == "⚠️ 放量下跌"].sort_values("Risk Score", ascending=False).head(5)

left, middle, right = st.columns(3)

with left:
    st.markdown("### 🔥 Top 机会榜")
    st.dataframe(
        top_opportunities[["Ticker", "Sector", "Price", "Change %", "Volume Ratio", "Momentum", "Trend Score", "Score"]],
        use_container_width=True
    )

with middle:
    st.markdown("### 📈 Top 趋势榜")
    st.dataframe(
        top_trends[["Ticker", "Sector", "Price", "Change %", "Trend", "Up Days(5)", "Trend Score"]],
        use_container_width=True
    )

with right:
    st.markdown("### ⚠️ Top 风险榜")
    st.dataframe(
        top_risks[["Ticker", "Sector", "Price", "Change %", "Down Days(5)", "Risk Score"]],
        use_container_width=True
    )

st.subheader("📊 个股资金与趋势信号")

st.dataframe(
    filtered_df.sort_values("Score", ascending=False),
    use_container_width=True
)

st.subheader("🧭 市场结构图")

fig = px.scatter(
    filtered_df,
    x="Trend Score",
    y="Momentum",
    color="Sector",
    size="Volume Ratio",
    hover_name="Ticker",
    text="Ticker",
    title="趋势评分 × 资金动量 × 成交量倍率"
)

fig.update_traces(textposition="top center")
st.plotly_chart(fig, use_container_width=True)

st.info("""
信号解释：

🔥 强势流入 = 上涨 + 成交量高于均量  
⚠️ 放量下跌 = 下跌 + 成交量高于均量  
💤 弱上涨 = 上涨但量能一般  
🧨 弱势 = 下跌且缺乏强势资金  

Trend Score 越高，代表短期连续性、趋势结构、量能配合越强。  
Risk Score 越高，代表下跌连续性和放量风险越强。  

注意：这不是机构真实净流入，也不是买卖建议，只是辅助观察模型。
""")
