import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from dotenv import load_dotenv

from utils.data_processing import validate_and_clean_csv
from utils.portfolio_math import calculate_fifo_holdings, fetch_current_prices, calculate_portfolio_xirr

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Stock Portfolio Analyst Agent",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
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
</style>
""", unsafe_allow_html=True)

# Helper function to fetch prices with Streamlit caching
@st.cache_data(ttl=300)
def get_cached_prices(tickers):
    return fetch_current_prices(tickers)

# Helper function to build dynamic ticker string based on active holdings
def get_ticker_html(active_holdings, current_prices):
    base_tickers = [
        ("SPY", 523.41, 1.25),
        ("QQQ", 439.18, 1.02),
        ("DIA", 390.50, 0.45)
    ]
    
    html = '<div class="marquee-container"><div class="marquee-text">'
    
    # Add major indices first
    for name, price, change in base_tickers:
        sign = "+" if change >= 0 else ""
        color_class = "ticker-green" if change >= 0 else "ticker-red"
        arrow = "▲" if change >= 0 else "▼"
        html += f'<span class="ticker-item">📊 {name} <span class="{color_class}">{price:,.2f} ({sign}{change:,.2f}%) {arrow}</span></span>'
        
    # Add active holdings
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

# Load data logic to sync prices
active_holdings = {}
current_prices = {}
realized_gains = {}

if "cleaned_df" not in st.session_state:
    st.session_state.cleaned_df = None
if "validation_message" not in st.session_state:
    st.session_state.validation_message = ""

# Populate data if CSV is uploaded
if st.session_state.cleaned_df is not None:
    active_holdings, realized_gains = calculate_fifo_holdings(st.session_state.cleaned_df)
    tickers = list(active_holdings.keys())
    current_prices = get_cached_prices(tickers)

# Render Banner
st.markdown(get_ticker_html(active_holdings, current_prices), unsafe_allow_html=True)

# Main Title & Subheader
st.title("Stock Portfolio Analyst Agent")
st.subheader("Your AI-powered assistant for portfolio visualization, FIFO cost lot tracking, and market analytics")

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
            "Choose a CSV file", 
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
    elif load_sample:
        if os.path.exists("sample_portfolio.csv"):
            data_source = "sample_portfolio.csv"
        else:
            st.error("Sample CSV file not found in directory. Did you delete 'sample_portfolio.csv'?")
            
    if data_source is not None:
        try:
            cleaned_df, msg = validate_and_clean_csv(data_source)
            st.session_state.cleaned_df = cleaned_df
            st.session_state.validation_message = msg
            st.success(msg)
            # Force refresh session state prices
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
        st.write("### 📋 Uploaded Transactions Preview")
        
        df = st.session_state.cleaned_df
        total_tx = len(df)
        unique_tickers = df["ticker"].nunique()
        buy_tx = len(df[df["transaction_type"] == "Buy"])
        sell_tx = len(df[df["transaction_type"] == "Sell"])
        
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Total Transactions", total_tx)
        m_col2.metric("Unique Tickers", unique_tickers)
        m_col3.metric("Buy Trades", buy_tx)
        m_col4.metric("Sell Trades", sell_tx)
        
        st.write("")
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
        # 1. High level metric cards
        total_cost_basis = sum(h["total_cost"] for h in active_holdings.values())
        total_market_val = sum(h["shares"] * current_prices.get(ticker, 0.0) for ticker, h in active_holdings.items())
        total_unrealized_gain = total_market_val - total_cost_basis
        total_realized_gain = sum(realized_gains.values())
        
        unrealized_pct = (total_unrealized_gain / total_cost_basis * 100) if total_cost_basis > 0 else 0.0
        
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric(
            "Portfolio Market Value", 
            f"${total_market_val:,.2f}",
            delta=None
        )
        mc2.metric(
            "Total Cost Basis", 
            f"${total_cost_basis:,.2f}"
        )
        mc3.metric(
            "Total Unrealized Gain/Loss", 
            f"${total_unrealized_gain:,.2f}",
            delta=f"{unrealized_pct:+.2f}%"
        )
        mc4.metric(
            "Total Realized Gain/Loss", 
            f"${total_realized_gain:,.2f}",
            delta=None
        )
        
        # 2. Plots & Charts (Pie charts)
        st.write("")
        pc_col1, pc_col2 = st.columns(2)
        
        with pc_col1:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.write("##### **Holdings Allocation (Current Value)**")
            
            pie_data = pd.DataFrame([
                {
                    "Ticker": ticker, 
                    "Market Value": h["shares"] * current_prices.get(ticker, 0.0),
                    "Shares": h["shares"]
                }
                for ticker, h in active_holdings.items()
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
            # Sector distribution placeholder (we will load active sectors from yfinance in Phase 4)
            # Default placeholder mappings for the sample assets:
            mock_sectors = {
                "MSFT": "Technology",
                "GOOGL": "Technology",
                "NVDA": "Technology",
                "CRM": "Technology",
                "ASTS": "Telecommunications"
            }
            
            sector_data = []
            for ticker, h in active_holdings.items():
                sec = mock_sectors.get(ticker, "Financials/Other")
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

        # 3. Detailed Holdings Table
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write("### 🔑 FIFO Active Holdings Summary")
        
        holdings_rows = []
        for ticker, h in active_holdings.items():
            price = current_prices.get(ticker, 0.0)
            m_val = h["shares"] * price
            unrealized = m_val - h["total_cost"]
            unrealized_pct = (unrealized / h["total_cost"] * 100) if h["total_cost"] > 0 else 0.0
            
            holdings_rows.append({
                "Ticker": ticker,
                "Shares Owned": h["shares"],
                "Avg Cost Basis": h["avg_cost"],
                "Total Cost": h["total_cost"],
                "Current Price": price,
                "Market Value": m_val,
                "Unrealized Gain/Loss": unrealized,
                "Gain %": unrealized_pct
            })
            
        holdings_df = pd.DataFrame(holdings_rows)
        
        # Color coding style logic
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

# ----------------- TAB 3: HISTORICAL PERFORMANCE -----------------
with tabs[2]:
    st.write("### ⏳ Historical Performance & Annualized Return")
    if st.session_state.cleaned_df is None:
        st.info("⚠️ Please upload your transaction data in the **Data Upload** tab to calculate lifetime performance and compare against the S&P 500.")
    else:
        # Calculate XIRR
        xirr = calculate_portfolio_xirr(st.session_state.cleaned_df, current_prices, active_holdings)
        xirr_pct = xirr * 100
        
        # Lifetime metrics
        df = st.session_state.cleaned_df
        buys = df[df["transaction_type"] == "Buy"]
        sells = df[df["transaction_type"] == "Sell"]
        
        total_cash_invested = sum(buys["quantity"] * buys["price"])
        total_proceeds_received = sum(sells["quantity"] * sells["price"])
        
        # Calculate current active valuation
        total_market_val = sum(h["shares"] * current_prices.get(ticker, 0.0) for ticker, h in active_holdings.items())
        total_realized_gain = sum(realized_gains.values())
        
        net_worth_inflows = total_proceeds_received + total_market_val
        total_profit = net_worth_inflows - total_cash_invested
        total_roi = (total_profit / total_cash_invested * 100) if total_cash_invested > 0 else 0.0
        
        hc1, hc2, hc3, hc4 = st.columns(4)
        hc1.metric(
            "Portfolio XIRR (Annualized)", 
            f"{xirr_pct:.2f}%",
            delta=None
        )
        hc2.metric(
            "Lifetime Money Invested", 
            f"${total_cash_invested:,.2f}"
        )
        hc3.metric(
            "Lifetime Money Proceeds", 
            f"${total_proceeds_received:,.2f}"
        )
        hc4.metric(
            "Total Lifetime ROI", 
            f"{total_roi:+.2f}%",
            delta=f"${total_profit:+.2f} Profit"
        )
        
        # Performance comparison chart
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write("##### **Consolidated Portfolio Cumulative Investment Value**")
        
        # Create a basic cumulative investment over time chart
        df_sorted = df.sort_values("date")
        cumulative_invested = []
        running_cash = 0.0
        dates_list = []
        
        for _, row in df_sorted.iterrows():
            val = row["quantity"] * row["price"]
            if row["transaction_type"] == "Buy":
                running_cash += val
            else:
                running_cash -= val
            cumulative_invested.append(running_cash)
            dates_list.append(row["date"])
            
        # Append today
        dates_list.append(datetime.now())
        cumulative_invested.append(running_cash)
        
        chart_df = pd.DataFrame({
            "Date": dates_list,
            "Total Cash Allocated": cumulative_invested
        })
        
        fig3 = px.line(
            chart_df, 
            x="Date", 
            y="Total Cash Allocated",
            title="Net Capital Contributions Over Time ($)",
            markers=True
        )
        fig3.update_traces(line_color="#3b82f6", line_width=3)
        fig3.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color="#e2e8f0",
            xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
        )
        st.plotly_chart(fig3, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ----------------- TAB 4: AI ANALYST CHAT (PLACEHOLDER) -----------------
with tabs[3]:
    st.write("### 🤖 AI Analyst Chat")
    if st.session_state.cleaned_df is None:
        st.info("⚠️ Please upload your transaction data in the **Data Upload** tab to provide financial context to your AI Analyst.")
    else:
        st.success("✅ Cleaned transaction data loaded. The Groq LLM client and chat panel will be integrated in Phase 5.")
