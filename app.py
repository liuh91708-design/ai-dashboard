import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")

st.title("🚀 AI投资决策系统")

# 股票池
TICKERS = {
    "算力": ["NVDA", "AMD"],
    "云": ["MSFT", "AMZN"],
    "平台": ["META", "GOOGL"],
    "工业": ["ABB", "SI"],
}

@st.cache_data
def load_data(ticker):
    return yf.download(ticker, period="6mo")

def calc_return(df):
    return (df["Close"].iloc[-1] / df["Close"].iloc[0] - 1)

# 板块强度计算
st.subheader("📊 板块强度")

cols = st.columns(len(TICKERS))
sector_values = {}

for i, (sector, stocks) in enumerate(TICKERS.items()):
    returns = []
    for s in stocks:
        df = load_data(s)
        r = calc_return(df)
        returns.append(r)
    avg = sum(returns) / len(returns)
    sector_values[sector] = avg
    cols[i].metric(sector, f"{avg:.2%}")

# 市场判断
st.subheader("🧠 AI市场阶段判断")

compute = sector_values["算力"]
cloud = sector_values["云"]
platform = sector_values["平台"]

if compute > cloud and compute > platform:
    st.error("🔥 早期AI炒作阶段 → 注意减仓算力")
elif cloud > compute:
    st.success("✅ AI变现阶段 → 持有云厂")
elif platform > cloud:
    st.warning("⚠️ 应用扩散阶段 → 关注平台")
else:
    st.info("😐 中性阶段")

# 图表
st.subheader("📈 个股走势")

for sector, stocks in TICKERS.items():
    st.write(f"### {sector}")
    for s in stocks:
        df = load_data(s)
        st.line_chart(df["Close"])
