# Stock Portfolio Analyst Agent

An AI-powered US Stock Portfolio Analyst built with Streamlit, `yfinance`, and Groq LLM (`llama-3.1-8b-instant`). Part of The Gen Academy (Week 1 Project).

## Features
- **Data Upload**: Upload standard transaction CSV history with automatic mathematical validation.
- **Consolidated Portfolio View**: Interactive visual allocation (Plotly pie charts, metrics cards, FIFO cost-basis holdings table, and sector diversification charts).
- **Historical Performance**: Annualized ROI, total proceeds, and XIRR performance comparison against the S&P 500 benchmark (`^GSPC`).
- **AI Analyst Chat**: Dynamic multi-turn chat assistant that reads your direct portfolio balance, latest financial news, and company fundamentals to give intelligent insights.
- **Real-Time Ticker Banner**: Stunning top-marquee banner tracking major indices and portfolio stock movements.

## Technical Stack
- **Framework**: Streamlit
- **Package Manager**: `uv` (Astral)
- **Data Sources**: `yfinance` (real-time/historical prices & company profiles)
- **LLM Provider**: Groq API (`llama-3.1-8b-instant`)
- **Visuals**: Plotly, Streamlit custom CSS components

---

## Setup & Running Instructions

### 1. Requirements
Ensure you have Python 3.12 and `uv` installed. If you don't have `uv` installed, run:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory (based on `.env.example`) and supply your **Groq API Key**:
```bash
GROQ_API_KEY=gsk_your_key_here
```

### 3. Install Dependencies
Sync your virtual environment using `uv`:
```bash
uv sync
```

### 4. Run the Streamlit Application
Launch the dev server:
```bash
uv run streamlit run app.py
```
