import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

st.set_page_config(page_title="Nasdaq Money Flow", layout="wide")

st.title("🚀 Nasdaq 资金流进阶版 Dashboard")

SECTORS = {
    "AI/半导体": ["NVDA", "AMD", "AVGO", "QCOM", "TXN"],
    "云计算": ["MSFT", "AMZN", "GOOGL"],
    "平台/消费": ["AAPL", "META", "NFLX"],
    "其他": ["TSLA"]
}

ALL_TICKERS = sum(SECTORS.values(), [])

period = st.sidebar.selectbox("周期", ["5d", "1mo", "3mo", "6mo"], index=1)

@st.cache_data(ttl=600)
def load_data(tickers, period):
    return yf.download(
        tickers,
        period=period,
        group_by="ticker",
        auto_adjust=True,
        progress=False
    )

data = load_data(ALL_TICKERS, period)

rows = []

for sector, tickers in SECTORS.items():
    for t in tickers:
        try:
            df0 = data[t].dropna()

            close_now = df0["Close"].iloc[-1]
            close_prev = df0["Close"].iloc[0]
            volume = df0["Volume"].iloc[-1]
            avg_volume = df0["Volume"].mean()

            change = close_now / close_prev - 1
            money_momentum = change * volume

            if change > 0 and volume > avg_volume:
                signal = "🔥 强势流入"
            elif change < 0 and volume > avg_volume:
                signal = "⚠️ 出货"
            elif change > 0:
                signal = "💤 弱上涨"
            else:
                signal = "🧨 弱势"

            rows.append({
                "Ticker": t,
                "Sector": sector,
                "Change %": round(change * 100, 2),
                "Volume": int(volume),
                "Momentum": round(money_momentum / 1e6, 2),
                "Signal": signal
            })

        except Exception:
            pass

df = pd.DataFrame(rows)

if df.empty:
    st.error("数据获取失败，请稍后刷新。")
    st.stop()

sector_flow = df.groupby("Sector")["Momentum"].sum().reset_index()

st.subheader("🏦 板块资金流（百万单位）")
fig_sector = px.bar(
    sector_flow.sort_values("Momentum", ascending=False),
    x="Sector",
    y="Momentum",
    text="Momentum"
)
st.plotly_chart(fig_sector, use_container_width=True)

st.subheader("🧠 市场结论")

top_sector = sector_flow.sort_values("Momentum", ascending=False).iloc[0]
total_flow = sector_flow["Momentum"].sum()

mood = "风险偏好（Risk ON）" if total_flow > 0 else "风险规避（Risk OFF）"

st.success(f"""
🔥 主导板块：{top_sector['Sector']}

📊 资金状态：{mood}

👉 解读：资金正在向 **{top_sector['Sector']}** 集中
""")

st.subheader("📊 个股资金信号")
st.dataframe(df.sort_values("Momentum", ascending=False), use_container_width=True)

st.subheader("🧭 市场结构")
fig = px.scatter(
    df,
    x="Change %",
    y="Momentum",
    color="Sector",
    size="Volume",
    hover_name="Ticker",
    text="Ticker"
)
fig.update_traces(textposition="top center")
st.plotly_chart(fig, use_container_width=True)
st.subheader("🎯 今日重点标的")

top_long = df[(df["Signal"] == "🔥 强势流入")].sort_values("Momentum", ascending=False).head(3)
top_short = df[(df["Signal"] == "⚠️ 出货")].sort_values("Momentum", ascending=False).head(3)

c1, c2 = st.columns(2)

with c1:
    st.markdown("### 🔥 候选做多")
    st.dataframe(top_long[["Ticker","Change %","Momentum"]])

with c2:
    st.markdown("### ⚠️ 风险/做空观察")
    st.dataframe(top_short[["Ticker","Change %","Momentum"]])
