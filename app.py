import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from dotenv import load_dotenv

from utils.data_processing import validate_and_clean_csv, load_portfolio_data, save_portfolio_data
from utils.auth_manager import init_auth_state, is_authenticated, register_user, login_user, logout_user
from utils.portfolio_math import calculate_fifo_holdings, fetch_current_prices, calculate_portfolio_xirr
from utils.external_data import (
    fetch_sectors_for_tickers, 
    fetch_fundamentals_and_dividends, 
    fetch_news_for_tickers, 
    fetch_benchmark_performance
)
from utils.llm_agent import get_ai_response

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Stock Portfolio Analyst Agent",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed" # Hide sidebar by default since Settings is in the top right!
)

# Custom Premium Styling & Marquee CSS
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Outfit:wght@400;600;800&family=Roboto+Mono&display=swap');
    
    /* Main body background & font family */
    .stApp {
        background-color: #0c0f16;
        font-family: 'Inter', sans-serif;
        color: #e2e8f0;
    }
    
    /* Dynamic Glowing Banner Header */
    h1, h2, h3 {
        font-family: 'Outfit', sans-serif;
        font-weight: 800;
        background: linear-gradient(90deg, #3b82f6 0%, #10b981 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Smooth CSS Marquee Ticker */
    .marquee-container {
        width: 100%;
        overflow: hidden;
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid rgba(59, 130, 246, 0.2);
        border-radius: 8px;
        padding: 8px 15px;
        margin-bottom: 25px;
        backdrop-filter: blur(12px);
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
    }
    .marquee-text {
        display: inline-block;
        white-space: nowrap;
        animation: marquee-scroll 35s linear infinite;
        font-family: 'Roboto Mono', monospace;
        font-size: 13px;
        font-weight: 600;
    }
    .ticker-item {
        display: inline-block;
        margin-right: 35px;
    }
    .ticker-green {
        color: #10b981;
        text-shadow: 0 0 8px rgba(16, 185, 129, 0.4);
    }
    .ticker-red {
        color: #ef4444;
        text-shadow: 0 0 8px rgba(239, 68, 68, 0.4);
    }
    @keyframes marquee-scroll {
        0% { transform: translate3d(50%, 0, 0); }
        100% { transform: translate3d(-100%, 0, 0); }
    }
    
    /* Glassmorphism Card Panels */
    .glass-card {
        background: rgba(22, 30, 49, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        backdrop-filter: blur(12px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
    }
    
    /* Uploader Border & Styling overrides */
    .uploadedFile {
        background-color: rgba(30, 41, 59, 0.7);
        border-radius: 8px;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }
    
    /* Custom buttons */
    .stButton>button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: #ffffff !important;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 10px 20px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4);
    }
    
    /* Popover Settings Style */
    div[data-testid="stPopover"] {
        text-align: right;
    }
    
    /* Alert cards custom look */
    .validation-alert-green {
        background-color: rgba(16, 185, 129, 0.1);
        border-left: 5px solid #10b981;
        padding: 10px 15px;
        border-radius: 4px;
        margin-bottom: 10px;
        font-size: 14px;
        color: #a7f3d0;
    }
    
    /* Styled Chat Bubble Layout */
    .chat-bubble-user {
        background-color: #2563eb;
        border-radius: 12px 12px 0 12px;
        padding: 12px 18px;
        margin-bottom: 10px;
        max-width: 80%;
        float: right;
        clear: both;
        color: #ffffff;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
    }
    .chat-bubble-assistant {
        background-color: rgba(30, 41, 59, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px 12px 12px 0;
        padding: 15px 20px;
        margin-bottom: 15px;
        max-width: 85%;
        float: left;
        clear: both;
        color: #e2e8f0;
        backdrop-filter: blur(8px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.15);
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
init_auth_state()

if "cleaned_df" not in st.session_state:
    st.session_state.cleaned_df = None
if "validation_message" not in st.session_state:
    st.session_state.validation_message = ""
if "groq_api_key" not in st.session_state:
    st.session_state.groq_api_key = os.environ.get("GROQ_API_KEY", "")
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Sidebar Authentication Flow
with st.sidebar:
    if is_authenticated():
        st.write(f"Welcome, **{st.session_state.username}**!")
        if st.button("Log Out"):
            logout_user()
            st.session_state.cleaned_df = None
            st.rerun()
    else:
        st.write("### Guest Mode Active")
        st.info("You are using the app as a Guest. Your data will only be saved for this session.")
        st.write("---")
        st.write("### Register / Log In")
        auth_mode = st.radio("Select Action", ["Log In", "Register"], label_visibility="collapsed")
        auth_username = st.text_input("Username")
        auth_password = st.text_input("Password", type="password")
        if st.button(auth_mode):
            if auth_mode == "Register":
                success, msg = register_user(auth_username, auth_password)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                success, msg = login_user(auth_username, auth_password)
                if success:
                    st.success(msg)
                    loaded_df = load_portfolio_data()
                    st.session_state.cleaned_df = loaded_df if not loaded_df.empty else None
                    st.rerun()
                else:
                    st.error(msg)

# Caching wrappers for API data
@st.cache_data(ttl=300)
def get_cached_prices(tickers):
    return fetch_current_prices(tickers)

@st.cache_data(ttl=600)
def get_cached_sectors(tickers):
    return fetch_sectors_for_tickers(tickers)

@st.cache_data(ttl=600)
def get_cached_fundamentals(tickers):
    return fetch_fundamentals_and_dividends(tickers)

@st.cache_data(ttl=300)
def get_cached_news(tickers):
    return fetch_news_for_tickers(tickers)

@st.cache_data(ttl=3600)
def get_cached_benchmark(start_date, end_date):
    return fetch_benchmark_performance(start_date, end_date)

# Helper function to build dynamic ticker string based on active holdings
def get_ticker_html(active_holdings, current_prices):
    base_tickers = [
        ("SPY", 523.41, 1.25),
        ("QQQ", 439.18, 1.02),
        ("DIA", 390.50, 0.45)
    ]
    
    html = '<div class="marquee-container"><div class="marquee-text">'
    for name, price, change in base_tickers:
        sign = "+" if change >= 0 else ""
        color_class = "ticker-green" if change >= 0 else "ticker-red"
        arrow = "▲" if change >= 0 else "▼"
        html += f'<span class="ticker-item">📊 {name} <span class="{color_class}">{price:,.2f} ({sign}{change:,.2f}%) {arrow}</span></span>'
        
    for ticker, holding in active_holdings.items():
        price = current_prices.get(ticker, 0.0)
        avg_cost = holding["avg_cost"]
        if avg_cost > 0:
            change = ((price - avg_cost) / avg_cost) * 100
        else:
            change = 0.0
            
        sign = "+" if change >= 0 else ""
        color_class = "ticker-green" if change >= 0 else "ticker-red"
        arrow = "▲" if change >= 0 else "▼"
        html += f'<span class="ticker-item">💼 {ticker} <span class="{color_class}">${price:,.2f} ({sign}{change:,.2f}%) {arrow}</span></span>'
        
    html += '</div></div>'
    return html

# Populate data if CSV is uploaded
active_holdings = {}
current_prices = {}
realized_gains = {}

if st.session_state.cleaned_df is None and is_authenticated():
    loaded_df = load_portfolio_data()
    if not loaded_df.empty:
        st.session_state.cleaned_df = loaded_df

if st.session_state.cleaned_df is not None:
    active_holdings, realized_gains = calculate_fifo_holdings(st.session_state.cleaned_df)
    tickers = list(active_holdings.keys())
    current_prices = get_cached_prices(tickers)

# Render Banner
st.markdown(get_ticker_html(active_holdings, current_prices), unsafe_allow_html=True)

# ----------------- HEADER & CONFIG POPULAR OVER (TOP RIGHT) -----------------
header_col1, header_col2 = st.columns([5, 1])

with header_col1:
    st.title("Stock Portfolio Analyst Agent")
    st.subheader("Your AI-powered assistant for portfolio visualization, FIFO cost lot tracking, and market analytics")

with header_col2:
    st.write("") # Spacer
    st.write("") # Spacer
    with st.popover("⚙️ Settings", use_container_width=True):
        st.markdown("### ⚙️ System Settings")
        
        # User API Key Override
        user_key = st.text_input(
            "Groq API Key", 
            value=st.session_state.groq_api_key, 
            type="password",
            help="Securely supply your Groq Console API key"
        )
        if user_key != st.session_state.groq_api_key:
            st.session_state.groq_api_key = user_key
            os.environ["GROQ_API_KEY"] = user_key
            st.rerun()
            
        if st.session_state.groq_api_key:
            st.success("✔ Key Validated")
            st.info("✔ Groq Client Ready")
        else:
            st.warning("⚠️ API Key Missing")
            
        st.markdown("---")
        st.markdown("### 📊 Data Status")
        if st.session_state.cleaned_df is not None:
            st.success("✔ Active Portfolio: Loaded")
            status_file = "uploaded_data.csv"
            if "loaded_sample_flag" in st.session_state and st.session_state.loaded_sample_flag:
                status_file = "sample_portfolio.csv"
            st.caption(f"Filename: `{status_file}`")
            st.caption(f"Refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        else:
            st.caption("No portfolio loaded yet")

# Navigation tabs setup
tabs = st.tabs([
    "📂 Data Upload", 
    "📊 Consolidated Portfolio View", 
    "⏳ Historical Performance", 
    "🤖 AI Analyst Chat"
])

# ----------------- TAB 1: DATA UPLOAD -----------------
with tabs[0]:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.write("### 📤 Upload Your Transaction History")
    st.write(
        "To begin, please upload a CSV containing your stock transactions. "
        "The CSV must strictly contain the following headers: `ticker`, `date`, `transaction_type`, `quantity`, and `price`."
    )
    
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader(
            "Choose a CSV file (FIFO format)", 
            type="csv",
            help="Supported columns: ticker, date, transaction_type (Buy/Sell), quantity, price"
        )
    with col2:
        st.write("##### **Need test data?**")
        st.write("Click the button below to load the default sample portfolio provided for this week's bootcamp.")
        load_sample = st.button("📊 Load Sample Portfolio")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    data_source = None
    if uploaded_file is not None:
        data_source = uploaded_file
        st.session_state.loaded_sample_flag = False
    elif load_sample:
        if os.path.exists("sample_portfolio.csv"):
            data_source = "sample_portfolio.csv"
            st.session_state.loaded_sample_flag = True
        else:
            st.error("Sample CSV file not found in directory. Did you delete 'sample_portfolio.csv'?")
            
    if data_source is not None:
        try:
            cleaned_df, msg = validate_and_clean_csv(data_source)
            st.session_state.cleaned_df = cleaned_df
            st.session_state.validation_message = msg
            save_portfolio_data(cleaned_df)
            active_holdings, realized_gains = calculate_fifo_holdings(cleaned_df)
            st.cache_data.clear() # clear cache to get fresh prices
            current_prices = get_cached_prices(list(active_holdings.keys()))
            st.rerun()
        except ValueError as ve:
            st.session_state.cleaned_df = None
            st.session_state.validation_message = ""
            st.error(f"❌ Validation Error: {str(ve)}")
            
    if st.session_state.cleaned_df is not None:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write("##### **Validation Status**")
        st.markdown('<div class="validation-alert-green">✔ CSV structure valid.</div>', unsafe_allow_html=True)
        st.markdown('<div class="validation-alert-green">✔ Mandatory columns present: ticker, date, transaction_type, quantity, price</div>', unsafe_allow_html=True)
        st.markdown('<div class="validation-alert-green">✔ Data types validated.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        df = st.session_state.cleaned_df
        total_tx = len(df)
        unique_tickers = df["ticker"].nunique()
        start_date = df["date"].min().strftime('%Y-%m-%d')
        end_date = df["date"].max().strftime('%Y-%m-%d')
        
        met_col1, met_col2, met_col3 = st.columns(3)
        with met_col1:
            st.markdown(f'<div class="glass-card" style="text-align: center;"><p style="font-size: 14px; color: #64748b; margin-bottom: 5px;">Total Transactions</p><h1>{total_tx}</h1></div>', unsafe_allow_html=True)
        with met_col2:
            st.markdown(f'<div class="glass-card" style="text-align: center;"><p style="font-size: 14px; color: #64748b; margin-bottom: 5px;">Unique Tickers</p><h1>{unique_tickers}</h1></div>', unsafe_allow_html=True)
        with met_col3:
            st.markdown(f'<div class="glass-card" style="text-align: center;"><p style="font-size: 14px; color: #64748b; margin-bottom: 5px;">Date Range</p><h3>{start_date}<br>to {end_date}</h3></div>', unsafe_allow_html=True)
            
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write("### 📋 Uploaded Transactions Preview")
        st.dataframe(
            df.style.format({
                'price': '${:,.2f}',
                'quantity': '{:,.2f}'
            }),
            use_container_width=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

# ----------------- TAB 2: PORTFOLIO VIEW -----------------
with tabs[1]:
    st.write("### 📊 Consolidated Portfolio View")
    if st.session_state.cleaned_df is None:
        st.info("⚠️ Please upload your transaction data in the **Data Upload** tab to view your active holdings and portfolio metrics.")
    else:
        active_tickers = list(active_holdings.keys())
        sectors_mapping = get_cached_sectors(active_tickers)
        fundamentals = get_cached_fundamentals(active_tickers)
        
        filtered_tickers = st.multiselect(
            "Filter by Tickers", 
            options=active_tickers, 
            default=active_tickers,
            help="Select specific tickers to isolate in the allocation pie chart and holdings data grid"
        )
        
        if not filtered_tickers:
            st.warning("Please select at least one ticker to visualize your portfolio data.")
        else:
            filtered_holdings = {t: h for t, h in active_holdings.items() if t in filtered_tickers}
            
            total_cost_basis = sum(h["total_cost"] for h in filtered_holdings.values())
            total_market_val = sum(h["shares"] * current_prices.get(ticker, 0.0) for ticker, h in filtered_holdings.items())
            total_unrealized_gain = total_market_val - total_cost_basis
            total_realized_gain = sum(realized_gains.get(t, 0.0) for t in filtered_tickers)
            
            unrealized_pct = (total_unrealized_gain / total_cost_basis * 100) if total_cost_basis > 0 else 0.0
            
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Portfolio Market Value", f"${total_market_val:,.2f}")
            mc2.metric("Total Cost Basis", f"${total_cost_basis:,.2f}")
            mc3.metric("Total Unrealized Gain", f"${total_unrealized_gain:,.2f}", delta=f"{unrealized_pct:+.2f}%")
            mc4.metric("Total Realized Gain", f"${total_realized_gain:,.2f}")
            
            st.write("")
            pc_col1, pc_col2 = st.columns(2)
            
            with pc_col1:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.write("##### **Portfolio Allocation (%)**")
                
                pie_data = pd.DataFrame([
                    {
                        "Ticker": ticker, 
                        "Market Value": h["shares"] * current_prices.get(ticker, 0.0)
                    }
                    for ticker, h in filtered_holdings.items()
                ])
                
                fig = px.pie(
                    pie_data, 
                    values="Market Value", 
                    names="Ticker",
                    hole=0.4,
                    color_discrete_sequence=px.colors.sequential.Plotly3
                )
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color="#e2e8f0",
                    margin=dict(t=20, b=20, l=10, r=10),
                    legend=dict(orientation="h", y=-0.1)
                )
                st.plotly_chart(fig, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
            with pc_col2:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.write("##### **Sector Distribution**")
                
                sector_data = []
                for ticker, h in filtered_holdings.items():
                    sec = sectors_mapping.get(ticker, "Other")
                    val = h["shares"] * current_prices.get(ticker, 0.0)
                    sector_data.append({"Sector": sec, "Value": val})
                    
                sector_df = pd.DataFrame(sector_data).groupby("Sector").sum().reset_index()
                
                fig2 = px.pie(
                    sector_df,
                    values="Value",
                    names="Sector",
                    hole=0.4,
                    color_discrete_sequence=px.colors.sequential.Aggrnyl
                )
                fig2.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color="#e2e8f0",
                    margin=dict(t=20, b=20, l=10, r=10),
                    legend=dict(orientation="h", y=-0.1)
                )
                st.plotly_chart(fig2, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # Heuristic AI Summary Card
            st.markdown('<div class="glass-card" style="background-color: rgba(59, 130, 246, 0.05); border-left: 5px solid #3b82f6;">', unsafe_allow_html=True)
            st.write("🤖 **AI Summary**")
            if len(pie_data) > 0:
                top_holding = pie_data.sort_values(by="Market Value", ascending=False).iloc[0]
                top_pct = (top_holding["Market Value"] / total_market_val) * 100
                st.write(
                    f"Your portfolio has a heavy {top_pct:.1f}% concentration in **{top_holding['Ticker']}**. "
                    f"Sector analysis shows significant alignment in the **{list(sector_df['Sector'])[0]}** space. "
                    "Consider rebalancing into diversified sectors for risk management."
                )
            st.markdown('</div>', unsafe_allow_html=True)

            # 3. Detailed Holdings Table
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.write("### 🔑 FIFO Active Holdings Summary")
            
            holdings_rows = []
            for ticker, h in filtered_holdings.items():
                price = current_prices.get(ticker, 0.0)
                m_val = h["shares"] * price
                unrealized = m_val - h["total_cost"]
                unrealized_pct = (unrealized / h["total_cost"] * 100) if h["total_cost"] > 0 else 0.0
                
                holdings_rows.append({
                    "Ticker": ticker,
                    "Name": fundamentals.get(ticker, {}).get("name", ticker),
                    "Sector": sectors_mapping.get(ticker, "Other"),
                    "Shares Owned": h["shares"],
                    "Avg Cost Basis": h["avg_cost"],
                    "Total Cost": h["total_cost"],
                    "Current Price": price,
                    "Market Value": m_val,
                    "Unrealized Gain/Loss": unrealized,
                    "Gain %": unrealized_pct
                })
                
            holdings_df = pd.DataFrame(holdings_rows)
            
            def style_gains(val):
                color = '#10b981' if val >= 0 else '#ef4444'
                return f'color: {color}; font-weight: 600;'

            st.dataframe(
                holdings_df.style.format({
                    'Shares Owned': '{:,.2f}',
                    'Avg Cost Basis': '${:,.2f}',
                    'Total Cost': '${:,.2f}',
                    'Current Price': '${:,.2f}',
                    'Market Value': '${:,.2f}',
                    'Unrealized Gain/Loss': '${:+,.2f}',
                    'Gain %': '{:+.2f}%'
                }).map(style_gains, subset=['Unrealized Gain/Loss', 'Gain %']),
                use_container_width=True
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Key Dividends and PE Multiples summary (Fundamental section)
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.write("### 🏢 Key Fundamentals & Dividend Schedules")
            fundamentals_rows = []
            for ticker in filtered_tickers:
                fund = fundamentals.get(ticker, {})
                fundamentals_rows.append({
                    "Ticker": ticker,
                    "Company Name": fund.get("name", ticker),
                    "Trailing P/E Ratio": fund.get("pe_ratio", "N/A"),
                    "Dividend Yield": fund.get("dividend_yield", "0.00%"),
                    "Ex-Dividend Date": fund.get("dividend_date", "N/A"),
                    "Market Capitalization": f"${fund.get('market_cap', 0)/1e9:.2f}B" if fund.get('market_cap', 0) > 0 else "N/A"
                })
            st.dataframe(pd.DataFrame(fundamentals_rows), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

# ----------------- TAB 3: HISTORICAL PERFORMANCE -----------------
with tabs[2]:
    st.write("### ⏳ Historical Performance & Benchmark Indexing")
    if st.session_state.cleaned_df is None:
        st.info("⚠️ Please upload your transaction data in the **Data Upload** tab to calculate performance metrics.")
    else:
        df = st.session_state.cleaned_df
        min_date_val = df["date"].min().to_pydatetime()
        max_date_val = df["date"].max().to_pydatetime()
        
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        col_dr1, col_dr2 = st.columns([1, 2])
        with col_dr1:
            dr_input = st.date_input(
                "Input Date Range",
                value=(min_date_val, max_date_val),
                min_value=min_date_val - timedelta(days=365),
                max_value=max_date_val + timedelta(days=365)
            )
        st.markdown('</div>', unsafe_allow_html=True)
        
        start_filter = min_date_val
        end_filter = max_date_val
        if isinstance(dr_input, tuple) and len(dr_input) == 2:
            start_filter, end_filter = dr_input
            start_filter = datetime(start_filter.year, start_filter.month, start_filter.day)
            end_filter = datetime(end_filter.year, end_filter.month, end_filter.day)
            
        df_filtered = df[(df["date"] >= start_filter) & (df["date"] <= end_filter)]
        
        if df_filtered.empty:
            st.warning("No transactions found within the selected date range.")
        else:
            filtered_holdings_math, filtered_realized_gains = calculate_fifo_holdings(df_filtered)
            benchmark_df = get_cached_benchmark(start_filter, end_filter)
            
            xirr = calculate_portfolio_xirr(df_filtered, current_prices, filtered_holdings_math)
            xirr_pct = xirr * 100
            
            buys = df_filtered[df_filtered["transaction_type"] == "Buy"]
            sells = df_filtered[df_filtered["transaction_type"] == "Sell"]
            
            total_cash_invested = sum(buys["quantity"] * buys["price"])
            total_proceeds_received = sum(sells["quantity"] * sells["price"])
            total_market_val = sum(h["shares"] * current_prices.get(ticker, 0.0) for ticker, h in filtered_holdings_math.items())
            
            net_worth_inflows = total_proceeds_received + total_market_val
            total_profit = net_worth_inflows - total_cash_invested
            total_roi = (total_profit / total_cash_invested * 100) if total_cash_invested > 0 else 0.0
            
            hc1, hc2, hc3 = st.columns(3)
            hc1.metric("Total Investment", f"${total_cash_invested:,.2f}")
            hc2.metric("Total Proceeds", f"${total_proceeds_received:,.2f}", delta=f"${total_profit:+.2f} Profit")
            hc3.metric("Annualized Return (XIRR)", f"{xirr_pct:.1f}%")
            
            st.write("")
            
            # Bar Chart: Cumulative Cashflow
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.write("##### **Cumulative Cashflow**")
            
            df_sorted = df_filtered.sort_values("date")
            cumulative_cash = []
            running_cash = 0.0
            dates_list = []
            
            for _, row in df_sorted.iterrows():
                val = row["quantity"] * row["price"]
                if row["transaction_type"] == "Buy":
                    running_cash += val
                else:
                    running_cash -= val
                cumulative_cash.append(running_cash)
                dates_list.append(row["date"])
                
            dates_list.append(datetime.now())
            cumulative_cash.append(running_cash)
            
            cashflow_plot_df = pd.DataFrame({
                "Date": dates_list,
                "Cumulative Cashflow": cumulative_cash
            })
            
            fig_cash = px.bar(
                cashflow_plot_df,
                x="Date",
                y="Cumulative Cashflow",
                color="Cumulative Cashflow",
                color_continuous_scale=px.colors.sequential.Bluyl
            )
            fig_cash.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color="#e2e8f0",
                xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
            )
            st.plotly_chart(fig_cash, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Line Chart: Portfolio Value Curve with S&P 500
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.write("##### **Portfolio Value vs. S&P 500 Index**")
            
            portfolio_val_line = []
            benchmark_val_line = []
            timeline_dates = []
            
            if not benchmark_df.empty:
                for idx, row in benchmark_df.iterrows():
                    curr_date = row["date"]
                    if isinstance(curr_date, str):
                        curr_date = pd.to_datetime(curr_date)
                        
                    tx_up_to_date = df_filtered[df_filtered["date"] <= curr_date]
                    
                    if not tx_up_to_date.empty:
                        h_on_date, _ = calculate_fifo_holdings(tx_up_to_date)
                        p_cost = sum(h["total_cost"] for h in h_on_date.values())
                        cum_index_pct = float(row["cumulative_return"])
                        p_value_spy_indicative = p_cost * cum_index_pct
                        
                        timeline_dates.append(curr_date)
                        portfolio_val_line.append(p_cost)
                        benchmark_val_line.append(p_value_spy_indicative)
                        
                comp_df = pd.DataFrame({
                    "Date": timeline_dates,
                    "Your Portfolio Value (Cash Allocated)": portfolio_val_line,
                    "S&P 500 Comparative Value": benchmark_val_line
                })
                
                fig_val = go.Figure()
                fig_val.add_trace(go.Scatter(
                    x=comp_df["Date"], 
                    y=comp_df["Your Portfolio Value (Cash Allocated)"], 
                    name="Your Portfolio Capital Contributions ($)",
                    line=dict(color="#3b82f6", width=3)
                ))
                fig_val.add_trace(go.Scatter(
                    x=comp_df["Date"], 
                    y=comp_df["S&P 500 Comparative Value"], 
                    name="Benchmark Index S&P 500 equivalent ($)",
                    line=dict(color="#10b981", width=3, dash='dash')
                ))
                fig_val.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color="#e2e8f0",
                    xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
                    yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
                    margin=dict(t=10, b=10, l=10, r=10),
                    legend=dict(orientation="h", y=-0.15)
                )
                st.plotly_chart(fig_val, use_container_width=True)
            else:
                fig_fallback = px.line(cashflow_plot_df, x="Date", y="Cumulative Cashflow")
                st.plotly_chart(fig_fallback, use_container_width=True)
                
            st.markdown('</div>', unsafe_allow_html=True)

# ----------------- TAB 4: AI ANALYST CHAT -----------------
with tabs[3]:
    st.write("### 🤖 Chat with your Stock Analyst Agent")
    if st.session_state.cleaned_df is None:
        st.info("⚠️ Please upload your transaction data in the **Data Upload** tab to provide financial context to your AI Analyst.")
    else:
        # Layout metrics variables
        active_tickers = list(active_holdings.keys())
        sectors_mapping = get_cached_sectors(active_tickers)
        fundamentals = get_cached_fundamentals(active_tickers)
        news_articles = get_cached_news(active_tickers)
        
        total_market_val = sum(h["shares"] * current_prices.get(ticker, 0.0) for ticker, h in active_holdings.items())
        total_cost_basis = sum(h["total_cost"] for h in active_holdings.values())
        total_unrealized_gain = total_market_val - total_cost_basis
        total_unrealized_pct = (total_unrealized_gain / total_cost_basis * 100) if total_cost_basis > 0 else 0.0
        total_realized_gain = sum(realized_gains.values())
        
        total_tx = len(df)
        unique_tickers = df["ticker"].nunique()
        
        # 1. AI Context Alert Header exactly like screenshot!
        st.markdown(
            f'<div class="glass-card" style="background-color: rgba(16, 185, 129, 0.05); border-left: 5px solid #10b981; padding: 15px 20px;">'
            f'🤖 <strong>AI Context:</strong> Actively analyzing <strong>{unique_tickers}</strong> tickers based on '
            f'<strong>{total_tx}</strong> historical transactions. Current portfolio value: <strong>${total_market_val:,.2f}</strong>.'
            f'</div>',
            unsafe_allow_html=True
        )
        
        # 2. Interactive suggest chips above the chat box!
        st.write("###### **Suggested Questions:**")
        chip_col1, chip_col2, chip_col3 = st.columns(3)
        suggested_query = None
        
        with chip_col1:
            if st.button("🔍 What is my biggest risk?", use_container_width=True):
                suggested_query = "What is my biggest risk based on my current portfolio holdings?"
        with chip_col2:
            if st.button("💡 What do you recommend now?", use_container_width=True):
                suggested_query = "What key investment recommendations or rebalancing strategies do you recommend based on my asset weights?"
        with chip_col3:
            if st.button("📅 Any upcoming dividends?", use_container_width=True):
                suggested_query = "Summarize my upcoming dividends and yields. Are there any ex-dividend dates I should watch?"

        # 3. Chat conversation log container
        chat_container = st.container()
        
        # Render previous messages
        with chat_container:
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.markdown(f'<div class="chat-bubble-user">{msg["content"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-bubble-assistant">{msg["content"]}</div>', unsafe_allow_html=True)

        # 4. Handle text inputs / queries
        user_input = st.chat_input("Ask your AI Analyst about your portfolio risk, performance, or potential strategy...")
        
        # If suggest chip or chat input is triggered
        query = user_input or suggested_query
        
        if query:
            # Check if key is available
            if not st.session_state.groq_api_key:
                st.error("❌ Groq API Key is not configured. Please enter your API Key in the Settings popover at the top right to start chatting!")
            else:
                # Add user message to history
                st.session_state.chat_history.append({"role": "user", "content": query})
                
                # Show user query immediately in UI
                with chat_container:
                    st.markdown(f'<div class="chat-bubble-user">{query}</div>', unsafe_allow_html=True)
                
                # Compile complete portfolio context dynamically
                holdings_context = []
                for ticker, h in active_holdings.items():
                    price = current_prices.get(ticker, 0.0)
                    m_val = h["shares"] * price
                    unreal = m_val - h["total_cost"]
                    unreal_p = (unreal / h["total_cost"] * 100) if h["total_cost"] > 0 else 0.0
                    
                    holdings_context.append({
                        "ticker": ticker,
                        "name": fundamentals.get(ticker, {}).get("name", ticker),
                        "shares": h["shares"],
                        "avg_cost": h["avg_cost"],
                        "price": price,
                        "market_value": m_val,
                        "gain": unreal,
                        "gain_pct": unreal_p
                    })
                    
                sector_weights_context = {}
                for ticker, h in active_holdings.items():
                    sec = sectors_mapping.get(ticker, "Other")
                    val = h["shares"] * current_prices.get(ticker, 0.0)
                    sector_weights_context[sec] = sector_weights_context.get(sec, 0.0) + val
                    
                dividends_context = []
                for ticker in active_tickers:
                    fund = fundamentals.get(ticker, {})
                    dividends_context.append({
                        "ticker": ticker,
                        "yield": fund.get("dividend_yield", "0.00%"),
                        "date": fund.get("dividend_date", "N/A")
                    })
                    
                news_headlines_context = []
                for art in news_articles:
                    news_headlines_context.append({
                        "ticker": art["ticker"],
                        "title": art["title"],
                        "publisher": art["publisher"]
                    })
                    
                portfolio_context = {
                    "total_value": total_market_val,
                    "total_cost": total_cost_basis,
                    "unrealized_gain": total_unrealized_gain,
                    "unrealized_pct": total_unrealized_pct,
                    "realized_gain": total_realized_gain,
                    "active_holdings": holdings_context,
                    "sector_weights": sector_weights_context,
                    "dividends": dividends_context,
                    "news_headlines": news_headlines_context
                }
                
                # Fetch AI response
                with st.spinner("Analyzing portfolio context and generating institutional response..."):
                    ai_response = get_ai_response(
                        messages=st.session_state.chat_history,
                        api_key=st.session_state.groq_api_key,
                        portfolio_context=portfolio_context
                    )
                
                # Save AI response
                st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
                st.rerun()

        # Display News feed below the chat so they can read current happenings too!
        st.markdown('<div class="glass-card" style="margin-top: 30px;">', unsafe_allow_html=True)
        st.write("### 📰 Recent Portfolio Holdings News")
        if news_articles:
            for art in news_articles:
                st.markdown(
                    f"**{art['ticker']}**: [{art['title']}]({art['link']}) "
                    f"*(Source: {art['publisher']} - {art['date']})*"
                )
        else:
            st.write("No recent articles found for active holdings.")
        st.markdown('</div>', unsafe_allow_html=True)
