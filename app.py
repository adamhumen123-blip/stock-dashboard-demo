import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Institutional Stock Dashboard", layout="wide")

st.title("📊 Institutional Stock Dashboard")

# ============================
# INPUT SECTION
# ============================
ticker = st.text_input("Enter Stock Ticker", "AAPL").upper()
view_mode = st.radio("View Mode", ["TTM", "Quarterly", "Yearly"], horizontal=True)

# ============================
# SAFE CACHED DATA LOADER
# ============================
@st.cache_data(ttl=86400, show_spinner=False)
def load_data(ticker):
    stock = yf.Ticker(ticker)

    return {
        "info": stock.info,
        "financials": stock.financials.T,
        "quarterly_financials": stock.quarterly_financials.T,
        "balance_sheet": stock.balance_sheet.T,
        "cashflow": stock.cashflow.T,
        "quarterly_cashflow": stock.quarterly_cashflow.T
    }

data = load_data(ticker)

info = data["info"]
financials = data["financials"]
quarterly = data["quarterly_financials"]
balance = data["balance_sheet"]
cashflow = data["cashflow"]
quarterly_cashflow = data["quarterly_cashflow"]

# ============================
# TABS
# ============================
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Main", "Cash", "Debt", "Valuation", "Shares"]
)

# =========================================================
# MAIN TAB
# =========================================================
with tab1:
    st.subheader("Key Performance Metrics")

    col1, col2, col3, col4 = st.columns(4)

    market_cap = info.get("marketCap", 0) or 0
    pe = info.get("trailingPE", None)
    eps = info.get("trailingEps", None)
    revenue = info.get("totalRevenue", 0) or 0

    col1.metric("Market Cap", f"${market_cap/1e9:.2f}B")
    col2.metric("PE Ratio", round(pe, 2) if pe else "N/A")
    col3.metric("EPS (TTM)", round(eps, 2) if eps else "N/A")
    col4.metric("Revenue (TTM)", f"${revenue/1e9:.2f}B")

    st.markdown("---")

    df = financials if view_mode == "Yearly" else quarterly

    if not df.empty and "Total Revenue" in df.columns:
        chart_df = df[["Total Revenue", "Net Income"]].dropna()

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=chart_df.index,
            y=chart_df["Total Revenue"],
            name="Revenue"
        ))
        fig.add_trace(go.Scatter(
            x=chart_df.index,
            y=chart_df["Net Income"],
            name="Net Income",
            yaxis="y2"
        ))

        fig.update_layout(
            template="plotly_dark",
            yaxis=dict(title="Revenue"),
            yaxis2=dict(title="Net Income", overlaying="y", side="right"),
            height=500
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Financial data unavailable.")

# =========================================================
# CASH TAB
# =========================================================
with tab2:
    st.subheader("Cash Flow & Efficiency")

    df_cf = cashflow if view_mode == "Yearly" else quarterly_cashflow

    if not df_cf.empty and "Total Cash From Operating Activities" in df_cf.columns:
        capex = df_cf.get("Capital Expenditures", 0)
        fcf = df_cf["Total Cash From Operating Activities"] - capex

        latest_fcf = fcf.iloc[0] if len(fcf) > 0 else 0
        st.metric("Free Cash Flow (Latest)", f"${latest_fcf/1e9:.2f}B")

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_cf.index,
            y=fcf,
            name="Free Cash Flow"
        ))

        fig.update_layout(template="plotly_dark", height=450)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Cash flow data unavailable.")

# =========================================================
# DEBT TAB
# =========================================================
with tab3:
    st.subheader("Leverage & Debt Analysis")

    total_debt = info.get("totalDebt", 0) or 0
    cash = info.get("totalCash", 0) or 0
    net_debt = total_debt - cash

    col1, col2 = st.columns(2)
    col1.metric("Total Debt", f"${total_debt/1e9:.2f}B")
    col2.metric("Net Debt", f"${net_debt/1e9:.2f}B")

    if not balance.empty and "Total Liab" in balance.columns:
        df_debt = balance[["Total Liab"]].dropna()

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_debt.index,
            y=df_debt["Total Liab"],
            name="Total Liabilities"
        ))

        fig.update_layout(template="plotly_dark", height=450)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Debt data unavailable.")

# =========================================================
# VALUATION TAB
# =========================================================
with tab4:
    st.subheader("Valuation Metrics")

    ev = info.get("enterpriseValue", 0) or 0
    ebitda = info.get("ebitda", None)

    ev_ebitda = ev / ebitda if ebitda and ebitda != 0 else None

    col1, col2 = st.columns(2)
    col1.metric("Enterprise Value", f"${ev/1e9:.2f}B")
    col2.metric("EV / EBITDA", round(ev_ebitda, 2) if ev_ebitda else "N/A")

    st.markdown("---")
    st.subheader("DCF Model")

    growth = st.slider("Revenue Growth (%)", 1, 20, 8)
    discount = st.slider("Discount Rate (%)", 5, 20, 10)

    base_revenue = revenue
    shares = info.get("sharesOutstanding", 1) or 1

    future_value = 0
    for i in range(1, 6):
        future_rev = base_revenue * ((1 + growth/100) ** i)
        discounted = future_rev / ((1 + discount/100) ** i)
        future_value += discounted

    intrinsic = future_value / shares
    st.metric("Estimated Intrinsic Value", f"${intrinsic:.2f}")

# =========================================================
# SHARES TAB
# =========================================================
with tab5:
    st.subheader("Shares & Dilution Analysis")

    shares_out = info.get("sharesOutstanding", 0) or 0
    float_shares = info.get("floatShares", 0) or 0

    col1, col2 = st.columns(2)
    col1.metric("Shares Outstanding", f"{shares_out/1e9:.2f}B")
    col2.metric("Float Shares", f"{float_shares/1e9:.2f}B")

    if not balance.empty and "Common Stock" in balance.columns:
        df_shares = balance[["Common Stock"]].dropna()

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_shares.index,
            y=df_shares["Common Stock"],
            name="Common Stock Trend"
        ))

        fig.update_layout(template="plotly_dark", height=450)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Shares history unavailable.")
