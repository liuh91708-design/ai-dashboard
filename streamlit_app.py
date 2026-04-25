import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

st.set_page_config(page_title="Nasdaq Top30 Money Flow Dashboard", layout="wide")

st.title("🚀 Nasdaq Top30 资金流 Dashboard")
st.caption("数据来自 Yahoo Finance，仅供研究，不构成投资建议。")

TICKERS = [
    "AAPL","MSFT","NVDA","GOOGL","GOOG","AMZN","META","AVGO","TSLA","COST",
    "NFLX","AMD","PEP","ADBE","CSCO","TMUS","INTC","QCOM","TXN","AMAT",
    "INTU","AMGN","ISRG","BKNG","VRTX","MU","LRCX","ADP","ADI","PANW"
]

period = st.sidebar.selectbox(
    "选择周期",
    ["5d", "1mo", "3mo", "6mo", "1y"],
    index=1
)

selected = st.sidebar.multiselect(
    "选择股票",
    TICKERS,
    default=["AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA"]
)

@st.cache_data(ttl=900)
def load_data(tickers, period):
    data = yf.download(
        tickers,
        period=period,
        group_by="ticker",
        auto_adjust=True,
        progress=False
    )
    return data

if not selected:
    st.warning("请至少选择一只股票")
    st.stop()

data = load_data(selected, period)

rows = []

for ticker in selected:
    try:
        df = data[ticker].dropna() if len(selected) > 1 else data.dropna()

        if df.empty:
            continue

        close_now = df["Close"].iloc[-1]
        close_prev = df["Close"].iloc[0]
        volume_now = df["Volume"].iloc[-1]

        change_pct = (close_now / close_prev - 1) * 100
        money_flow = close_now * volume_now

        rows.append({
            "Ticker": ticker,
            "Price": round(close_now, 2),
            "Change %": round(change_pct, 2),
            "Volume": int(volume_now),
            "Money Flow": round(money_flow / 1e9, 2)
        })

    except Exception:
        pass

summary = pd.DataFrame(rows)

if summary.empty:
    st.error("数据获取失败，请刷新页面或稍后再试。")
    st.stop()

col1, col2, col3 = st.columns(3)

col1.metric("股票数量", len(summary))
col2.metric("最大涨幅", f"{summary['Change %'].max():.2f}%")
col3.metric("最大资金流", f"{summary['Money Flow'].max():.2f}B")

st.subheader("📊 Nasdaq Top30 概览")
st.dataframe(summary.sort_values("Money Flow", ascending=False), use_container_width=True)

st.subheader("💰 资金流排名")
fig_flow = px.bar(
    summary.sort_values("Money Flow", ascending=False),
    x="Ticker",
    y="Money Flow",
    text="Money Flow",
    title="成交金额估算：Price × Volume（十亿美元）"
)
st.plotly_chart(fig_flow, use_container_width=True)

st.subheader("📈 涨跌幅对比")
fig_change = px.bar(
    summary.sort_values("Change %", ascending=False),
    x="Ticker",
    y="Change %",
    text="Change %",
    title="周期涨跌幅"
)
st.plotly_chart(fig_change, use_container_width=True)

st.subheader("🧭 市场强弱象限图")
fig_scatter = px.scatter(
    summary,
    x="Change %",
    y="Money Flow",
    size="Volume",
    hover_name="Ticker",
    text="Ticker",
    title="涨跌幅 × 资金流"
)
fig_scatter.update_traces(textposition="top center")
st.plotly_chart(fig_scatter, use_container_width=True)

st.subheader("📌 简单交易观察")

leaders = summary.sort_values("Money Flow", ascending=False).head(5)
strong = summary[summary["Change %"] > 0].sort_values("Money Flow", ascending=False).head(5)
weak = summary[summary["Change %"] < 0].sort_values("Money Flow", ascending=False).head(5)

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("### 🔥 资金流最大")
    st.dataframe(leaders[["Ticker", "Money Flow", "Change %"]], use_container_width=True)

with c2:
    st.markdown("### ✅ 放量上涨")
    st.dataframe(strong[["Ticker", "Money Flow", "Change %"]], use_container_width=True)

with c3:
    st.markdown("### ⚠️ 放量下跌")
    st.dataframe(weak[["Ticker", "Money Flow", "Change %"]], use_container_width=True)

st.info("提示：资金流这里只是用 Price × Volume 做的成交金额估算，不是真正机构净流入。真正净流入需要更专业的数据源。")
