import os
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import yfinance as yf

st.set_page_config(page_title="Nasdaq 胜率系统版", layout="wide")

st.title("🚀 Nasdaq 自动记录 + 胜率分析系统")
st.caption("仅供研究，不构成投资建议。Yahoo/yfinance 数据可能延迟。")

LOG_FILE = "signals_log.csv"

SECTORS = {
    "AI/半导体": ["NVDA", "AMD", "AVGO", "QCOM", "TXN", "MU", "AMAT", "LRCX", "ADI"],
    "云计算/软件": ["MSFT", "AMZN", "GOOGL", "ADBE", "INTU", "PANW"],
    "平台/消费科技": ["AAPL", "META", "NFLX", "BKNG"],
    "电动车/成长": ["TSLA"],
    "防御/消费": ["COST", "PEP"],
    "医疗科技": ["AMGN", "ISRG", "VRTX"],
    "通信/网络": ["CSCO", "TMUS"],
}

ALL_TICKERS = sorted(list(set(sum(SECTORS.values(), []))))
INDEX_TICKERS = ["QQQ", "SPY"]

period = st.sidebar.selectbox("周期", ["5d", "1mo", "3mo", "6mo", "1y"], index=1)
mode = st.sidebar.radio("查看模式", ["全部", "只看机会", "只看风险", "只看强趋势"], index=0)
min_change = st.sidebar.slider("最小涨跌幅绝对值 (%)", 0.0, 20.0, 0.0, 0.5)
auto_refresh = st.sidebar.checkbox("每 5 分钟自动刷新", value=True)
refresh = st.sidebar.button("🔄 手动刷新数据")

if auto_refresh:
    st_autorefresh(interval=5 * 60 * 1000, key="nasdaq_auto_refresh")
    st.sidebar.caption("已开启：每 5 分钟自动刷新。")

@st.cache_data(ttl=300)
def load_data(tickers, selected_period):
    return yf.download(
        tickers,
        period=selected_period,
        group_by="ticker",
        auto_adjust=True,
        progress=False,
    )

@st.cache_data(ttl=3600)
def load_history(ticker):
    return yf.download(
        ticker,
        period="3mo",
        auto_adjust=True,
        progress=False,
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

            recent_returns = df0["Close"].tail(5).pct_change().dropna()
            up_days = int((recent_returns > 0).sum())
            down_days = int((recent_returns < 0).sum())

            volume_strength = df0["Volume"].tail(5).iloc[-1] / df0["Volume"].tail(5).mean()

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

            trend_score = trend_base * 10 + up_days * 3 - down_days * 3 + volume_strength * 2 + change * 100
            risk_score = down_days * 4 + max(-change * 100, 0) + (volume_ratio * 2 if change < 0 else 0)
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
                "Signal": signal,
            })

        except Exception:
            pass

df = pd.DataFrame(rows)

if df.empty:
    st.error("数据获取失败，请刷新页面或稍后再试。")
    st.stop()

buy_candidates = df[
    (df["Signal"] == "🔥 强势流入") &
    (df["Trend Score"] > 20) &
    (df["Change %"] > 1)
].sort_values("Score", ascending=False).head(5)

sell_candidates = df[
    (df["Signal"] == "⚠️ 放量下跌") &
    (df["Risk Score"] > 10)
].sort_values("Risk Score", ascending=False).head(5)

today = datetime.now().strftime("%Y-%m-%d")
now_time = datetime.now().strftime("%H:%M:%S")

log_rows = []

for _, row in buy_candidates.iterrows():
    log_rows.append({
        "Date": today,
        "Time": now_time,
        "Type": "BUY_WATCH",
        "Ticker": row["Ticker"],
        "Sector": row["Sector"],
        "Entry Price": row["Price"],
        "Change %": row["Change %"],
        "Trend Score": row["Trend Score"],
        "Risk Score": row["Risk Score"],
        "Score": row["Score"],
        "Signal": row["Signal"],
    })

for _, row in sell_candidates.iterrows():
    log_rows.append({
        "Date": today,
        "Time": now_time,
        "Type": "RISK_WATCH",
        "Ticker": row["Ticker"],
        "Sector": row["Sector"],
        "Entry Price": row["Price"],
        "Change %": row["Change %"],
        "Trend Score": row["Trend Score"],
        "Risk Score": row["Risk Score"],
        "Score": row["Score"],
        "Signal": row["Signal"],
    })

new_log = pd.DataFrame(log_rows)

if os.path.exists(LOG_FILE):
    old_log = pd.read_csv(LOG_FILE)
else:
    old_log = pd.DataFrame()

if not new_log.empty:
    combined_log = pd.concat([old_log, new_log], ignore_index=True)
    combined_log = combined_log.drop_duplicates(
        subset=["Date", "Type", "Ticker"],
        keep="last"
    )
    combined_log.to_csv(LOG_FILE, index=False)
else:
    combined_log = old_log

def calc_forward_returns(log_df):
    if log_df.empty:
        return log_df

    results = []

    for _, row in log_df.iterrows():
        ticker = row["Ticker"]
        signal_date = pd.to_datetime(row["Date"])
        entry_price = row["Entry Price"]

        try:
            hist = load_history(ticker)
            hist = hist.reset_index()
            hist["Date"] = pd.to_datetime(hist["Date"]).dt.tz_localize(None)

            future = hist[hist["Date"] > signal_date].copy()

            result = row.to_dict()

            for days in [1, 3, 5]:
                if len(future) >= days:
                    future_price = future["Close"].iloc[days - 1]
                    ret = (future_price / entry_price - 1) * 100
                    result[f"T+{days} Return %"] = round(ret, 2)
                else:
                    result[f"T+{days} Return %"] = None

            results.append(result)

        except Exception:
            result = row.to_dict()
            result["T+1 Return %"] = None
            result["T+3 Return %"] = None
            result["T+5 Return %"] = None
            results.append(result)

    return pd.DataFrame(results)

performance_log = calc_forward_returns(combined_log) if not combined_log.empty else pd.DataFrame()

filtered_df = df[df["Change %"].abs() >= min_change]

if mode == "只看机会":
    filtered_df = filtered_df[filtered_df["Signal"] == "🔥 强势流入"]
elif mode == "只看风险":
    filtered_df = filtered_df[filtered_df["Signal"] == "⚠️ 放量下跌"]
elif mode == "只看强趋势":
    filtered_df = filtered_df[filtered_df["Trend Score"] > 20]

st.subheader("📌 市场基准")

index_rows = []
for idx in INDEX_TICKERS:
    try:
        idx_df = get_single_df(data, idx)
        idx_change = idx_df["Close"].iloc[-1] / idx_df["Close"].iloc[0] - 1
        index_rows.append({"Index": idx, "Change %": round(idx_change * 100, 2)})
    except Exception:
        pass

index_df = pd.DataFrame(index_rows)

c1, c2, c3, c4 = st.columns(4)

if not index_df.empty:
    c1.metric("QQQ", f"{index_df[index_df['Index']=='QQQ']['Change %'].iloc[0]:.2f}%")
    c2.metric("SPY", f"{index_df[index_df['Index']=='SPY']['Change %'].iloc[0]:.2f}%")
else:
    c1.metric("QQQ", "N/A")
    c2.metric("SPY", "N/A")

strong_count = len(df[df["Signal"] == "🔥 强势流入"])
risk_count = len(df[df["Signal"] == "⚠️ 放量下跌"])

c3.metric("强势 / 风险", f"{strong_count} / {risk_count}")
c4.metric("更新时间", datetime.now().strftime("%H:%M:%S"))

sector_flow = df.groupby("Sector")["Momentum"].sum().reset_index()
sector_trend = df.groupby("Sector")["Trend Score"].mean().reset_index()

st.subheader("🏦 板块资金流")
fig_sector = px.bar(
    sector_flow.sort_values("Momentum", ascending=False),
    x="Sector",
    y="Momentum",
    text="Momentum",
)
st.plotly_chart(fig_sector, use_container_width=True)

st.subheader("📈 板块趋势评分")
fig_sector_trend = px.bar(
    sector_trend.sort_values("Trend Score", ascending=False),
    x="Sector",
    y="Trend Score",
    text="Trend Score",
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
""")

st.subheader("🟢 策略信号")

left_exec, right_exec = st.columns(2)

with left_exec:
    st.markdown("### 🟢 买入观察")
    st.dataframe(
        buy_candidates[["Ticker", "Sector", "Price", "Change %", "Trend Score", "Score", "Signal"]],
        use_container_width=True,
    )

with right_exec:
    st.markdown("### 🔴 风险/卖出观察")
    st.dataframe(
        sell_candidates[["Ticker", "Sector", "Price", "Change %", "Risk Score", "Score", "Signal"]],
        use_container_width=True,
    )

st.subheader("📊 胜率系统")

if not performance_log.empty:
    closed_log = performance_log.dropna(subset=["T+1 Return %"])

    p1, p2, p3, p4 = st.columns(4)

    p1.metric("累计信号", len(performance_log))

    if not closed_log.empty:
        buy_log = closed_log[closed_log["Type"] == "BUY_WATCH"]
        risk_log = closed_log[closed_log["Type"] == "RISK_WATCH"]

        buy_win_rate = (buy_log["T+1 Return %"] > 0).mean() * 100 if not buy_log.empty else 0
        risk_win_rate = (risk_log["T+1 Return %"] < 0).mean() * 100 if not risk_log.empty else 0

        p2.metric("BUY T+1 胜率", f"{buy_win_rate:.1f}%")
        p3.metric("RISK T+1 命中率", f"{risk_win_rate:.1f}%")
        p4.metric("可验证信号", len(closed_log))

        type_perf = closed_log.groupby("Type")[["T+1 Return %", "T+3 Return %", "T+5 Return %"]].mean().reset_index()

        st.markdown("### 信号类型平均表现")
        st.dataframe(type_perf, use_container_width=True)

        sector_perf = closed_log.groupby("Sector")[["T+1 Return %", "T+3 Return %", "T+5 Return %"]].mean().reset_index()

        st.markdown("### 板块信号表现")
        st.dataframe(sector_perf, use_container_width=True)

        fig_perf = px.bar(
            sector_perf,
            x="Sector",
            y="T+1 Return %",
            title="各板块 T+1 平均表现",
        )
        st.plotly_chart(fig_perf, use_container_width=True)
    else:
        p2.metric("BUY T+1 胜率", "等待数据")
        p3.metric("RISK T+1 命中率", "等待数据")
        p4.metric("可验证信号", 0)
else:
    st.info("暂无信号记录。")

st.subheader("📒 信号记录与后续表现")

if not performance_log.empty:
    st.dataframe(
        performance_log.sort_values(["Date", "Time"], ascending=False),
        use_container_width=True,
    )

    csv = performance_log.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "下载胜率记录 CSV",
        data=csv,
        file_name="signals_performance_log.csv",
        mime="text/csv",
    )
else:
    st.info("暂无历史记录。")

st.subheader("🎯 今日重点标的")

top_opportunities = df[df["Signal"] == "🔥 强势流入"].sort_values("Score", ascending=False).head(5)
top_trends = df.sort_values("Trend Score", ascending=False).head(5)
top_risks = df[df["Signal"] == "⚠️ 放量下跌"].sort_values("Risk Score", ascending=False).head(5)

left, middle, right = st.columns(3)

with left:
    st.markdown("### 🔥 Top 机会榜")
    st.dataframe(top_opportunities, use_container_width=True)

with middle:
    st.markdown("### 📈 Top 趋势榜")
    st.dataframe(top_trends, use_container_width=True)

with right:
    st.markdown("### ⚠️ Top 风险榜")
    st.dataframe(top_risks, use_container_width=True)

st.subheader("📊 个股资金与趋势信号")
st.dataframe(filtered_df.sort_values("Score", ascending=False), use_container_width=True)

st.subheader("🧭 市场结构图")

fig = px.scatter(
    filtered_df,
    x="Trend Score",
    y="Momentum",
    color="Sector",
    size="Volume Ratio",
    hover_name="Ticker",
    text="Ticker",
    title="趋势评分 × 资金动量",
)

fig.update_traces(textposition="top center")
st.plotly_chart(fig, use_container_width=True)

st.info("""
说明：

BUY_WATCH 胜率：T+1 收益 > 0 视为命中。  
RISK_WATCH 命中率：T+1 收益 < 0 视为命中。  

T+1 / T+3 / T+5 是信号出现后第 1 / 3 / 5 个交易日的价格变化。
样本越多，统计才越有意义。
""")
