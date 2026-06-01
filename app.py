import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from utils.data_processing import validate_and_clean_csv

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

# 1. Top Real-Time Ticker Banner (Mock indices & changes for now, will connect live later)
st.markdown("""
<div class="marquee-container">
    <div class="marquee-text">
        <span class="ticker-item">📊 SPY <span class="ticker-green">5,234.11 (+1.25%) ▲</span></span>
        <span class="ticker-item">📈 QQQ <span class="ticker-green">16,391.88 (+1.02%) ▲</span></span>
        <span class="ticker-item">🍏 AAPL <span class="ticker-green">192.25 (+0.84%) ▲</span></span>
        <span class="ticker-item">💻 MSFT <span class="ticker-green">421.15 (+1.48%) ▲</span></span>
        <span class="ticker-item">🚀 NVDA <span class="ticker-green">903.65 (+2.10%) ▲</span></span>
        <span class="ticker-item">📉 TSLA <span class="ticker-red">174.60 (-1.15%) ▼</span></span>
        <span class="ticker-item">🛒 AMZN <span class="ticker-green">185.50 (+0.45%) ▲</span></span>
        <span class="ticker-item">🛰️ ASTS <span class="ticker-green">8.75 (+4.20%) ▲</span></span>
    </div>
</div>
""", unsafe_allow_html=True)

# Main Title & Subheader
st.title("Stock Portfolio Analyst Agent")
st.subheader("Your AI-powered assistant for portfolio visualization, FIFO cost lot tracking, and market analytics")

# Session State Initialization
if "cleaned_df" not in st.session_state:
    st.session_state.cleaned_df = None
if "validation_message" not in st.session_state:
    st.session_state.validation_message = ""

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
    
    # Grid for options
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # File uploader
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
    
    # File processing logic
    data_source = None
    if uploaded_file is not None:
        data_source = uploaded_file
    elif load_sample:
        # Load the sample CSV file
        if os.path.exists("sample_portfolio.csv"):
            data_source = "sample_portfolio.csv"
        else:
            st.error("Sample CSV file not found in directory. Did you delete 'sample_portfolio.csv'?")
            
    if data_source is not None:
        try:
            # Validate and clean the data
            cleaned_df, msg = validate_and_clean_csv(data_source)
            st.session_state.cleaned_df = cleaned_df
            st.session_state.validation_message = msg
            st.success(msg)
        except ValueError as ve:
            st.session_state.cleaned_df = None
            st.session_state.validation_message = ""
            st.error(f"❌ Validation Error: {str(ve)}")
            
    # Display the loaded data if it exists in session state
    if st.session_state.cleaned_df is not None:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write("### 📋 Uploaded Transactions Preview")
        
        # Display high-level metric cards
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
        
        # Sleek Dataframe display
        st.write("")
        st.dataframe(
            df.style.format({
                'price': '${:,.2f}',
                'quantity': '{:,.2f}'
            }),
            use_container_width=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

# ----------------- TAB 2: PORTFOLIO VIEW (PLACEHOLDER) -----------------
with tabs[1]:
    st.write("### 📊 Consolidated Portfolio View")
    if st.session_state.cleaned_df is None:
        st.info("⚠️ Please upload your transaction data in the **Data Upload** tab to view your active holdings and portfolio metrics.")
    else:
        st.success("✅ Cleaned transaction data loaded. Holding data and allocation charts will be available in Phase 3.")

# ----------------- TAB 3: HISTORICAL PERFORMANCE (PLACEHOLDER) -----------------
with tabs[2]:
    st.write("### ⏳ Historical Performance & XIRR")
    if st.session_state.cleaned_df is None:
        st.info("⚠️ Please upload your transaction data in the **Data Upload** tab to calculate lifetime performance and compare against the S&P 500.")
    else:
        st.success("✅ Cleaned transaction data loaded. XIRR mathematical computations will be implemented in Phase 3.")

# ----------------- TAB 4: AI ANALYST CHAT (PLACEHOLDER) -----------------
with tabs[3]:
    st.write("### 🤖 AI Analyst Chat")
    if st.session_state.cleaned_df is None:
        st.info("⚠️ Please upload your transaction data in the **Data Upload** tab to provide financial context to your AI Analyst.")
    else:
        st.success("✅ Cleaned transaction data loaded. The Groq LLM client and chat panel will be integrated in Phase 5.")
