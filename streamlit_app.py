import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

st.set_page_config(layout="wide")

st.title("🚀 Nasdaq 资金流进阶版 Dashboard")

# 分组（关键升级）
SECTORS = {
    "AI/半导体": ["NVDA", "AMD", "AVGO", "QCOM", "TXN"],
    "云计算": ["MSFT", "AMZN", "GOOGL"],
    "平台/消费": ["AAPL", "META", "NFLX"],
    "其他": ["TSLA"]
}

ALL_TICKERS = sum(SECTORS.values(), [])

period = st.sidebar.selectbox("周期", ["5d","1mo","3mo","6mo"], index=1)

@st.cache_data(ttl=600)
def load_data(tickers):
    return yf.download(tickers, period=period, group_by="ticker", auto_adjust=True)

data = load_data(ALL_TICKERS)

rows = []

for sector, tickers in SECTORS.items():
    for t in tickers:
        try:
            df = data[t].dropna()

            close_now = df["Close"].iloc[-1]
            close_prev = df["Close"].iloc[0]
            volume = df["Volume"].iloc[-1]

            change = (close_now/close_prev - 1)

            # 👉 核心升级：资金动量
            "Momentum": money_momentum / 1e6, 

            # 👉 信号分类
            if change > 0 and volume > df["Volume"].mean():
                signal = "🔥 强势流入"
            elif change < 0 and volume > df["Volume"].mean():
                signal = "⚠️ 出货"
            elif change > 0:
                signal = "💤 弱上涨"
            else:
                signal = "🧨 弱势"

            rows.append({
                "Ticker": t,
                "Sector": sector,
                "Change %": round(change*100,2),
                "Volume": int(volume),
                "Momentum": money_momentum,
                "Signal": signal
            })
        except:
            pass

df = pd.DataFrame(rows)

# ===== 板块资金 =====
sector_flow = df.groupby("Sector")["Momentum"].sum().reset_index()

st.subheader("🏦 板块资金流")
st.subheader("🧠 市场结论")

top_sector = sector_flow.sort_values("Momentum", ascending=False).iloc[0]
total_flow = sector_flow["Momentum"].sum()

if total_flow > 0:
    mood = "风险偏好（Risk ON）"
else:
    mood = "风险规避（Risk OFF）"

st.success(f"""
🔥 主导板块：{top_sector['Sector']}

📊 资金状态：{mood}

👉 解读：资金正在向 {top_sector['Sector']} 集中
""")
fig_sector = px.bar(sector_flow, x="Sector", y="Momentum", text="Momentum")
st.plotly_chart(fig_sector, use_container_width=True)

# ===== 个股 =====
st.subheader("📊 个股资金信号")

st.dataframe(df.sort_values("Momentum", ascending=False), use_container_width=True)

# ===== 散点 =====
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
st.plotly_chart(fig, use_container_width=True)
