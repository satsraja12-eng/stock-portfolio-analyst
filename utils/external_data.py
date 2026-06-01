import yfinance as yf
import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Any, Tuple

def fetch_sectors_for_tickers(tickers: List[str]) -> Dict[str, str]:
    """
    Fetches the market sector for each active ticker using yfinance.
    
    Includes default local fallback mappings to minimize API delays.
    """
    if not tickers:
        return {}
        
    # Standard fallback dictionary for popular tickers to ensure speedy response
    fallback_sectors = {
        "MSFT": "Technology",
        "AAPL": "Technology",
        "NVDA": "Technology",
        "GOOGL": "Communication Services",
        "GOOG": "Communication Services",
        "AMZN": "Consumer Cyclical",
        "TSLA": "Consumer Cyclical",
        "CRM": "Technology",
        "ASTS": "Telecommunications",
        "META": "Communication Services",
        "NFLX": "Communication Services",
        "AMD": "Technology",
        "JPM": "Financial Services",
        "V": "Financial Services",
        "WMT": "Consumer Defensive",
        "DIS": "Consumer Cyclical"
    }
    
    sectors = {}
    for ticker in tickers:
        # Check fallback first
        if ticker in fallback_sectors:
            sectors[ticker] = fallback_sectors[ticker]
            continue
            
        try:
            t = yf.Ticker(ticker)
            sector = t.info.get("sector", "Other")
            if sector and sector != "Other":
                sectors[ticker] = sector
            else:
                sectors[ticker] = "Other"
        except Exception:
            sectors[ticker] = "Other"
            
    return sectors

def fetch_fundamentals_and_dividends(tickers: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Fetches upcoming dividend info and key fundamental yields for active holdings.
    """
    if not tickers:
        return {}
        
    fundamentals = {}
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.info
            
            # Extract ex-dividend date (returns epoch timestamp usually, or None)
            ex_div_epoch = info.get("exDividendDate", None)
            ex_div_str = "N/A"
            if ex_div_epoch:
                try:
                    ex_div_str = datetime.fromtimestamp(ex_div_epoch).strftime('%Y-%m-%d')
                except Exception:
                    ex_div_str = str(ex_div_epoch)
            
            div_yield = info.get("dividendYield", 0.0)
            div_yield_pct = f"{div_yield * 100:.2f}%" if div_yield else "0.00%"
            
            pe_ratio = info.get("trailingPE", "N/A")
            pe_ratio_str = f"{pe_ratio:.2f}" if isinstance(pe_ratio, (int, float)) else "N/A"
            
            fundamentals[ticker] = {
                "name": info.get("longName", ticker),
                "dividend_date": ex_div_str,
                "dividend_yield": div_yield_pct,
                "pe_ratio": pe_ratio_str,
                "market_cap": info.get("marketCap", 0)
            }
        except Exception:
            fundamentals[ticker] = {
                "name": ticker,
                "dividend_date": "N/A",
                "dividend_yield": "0.00%",
                "pe_ratio": "N/A",
                "market_cap": 0
            }
            
    return fundamentals

def fetch_news_for_tickers(tickers: List[str], max_articles: int = 5) -> List[Dict[str, Any]]:
    """
    Fetches the latest business headlines and links for active portfolio holdings
    using yfinance Ticker.news integration.
    """
    if not tickers:
        return []
        
    articles = []
    seen_links = set()
    
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            news = t.news
            if not news:
                continue
                
            for item in news[:3]: # Take top 3 articles per ticker
                title = item.get("title", "")
                link = item.get("link", "")
                publisher = item.get("publisher", "")
                pub_time = item.get("providerPublishTime", 0)
                
                if link not in seen_links:
                    seen_links.add(link)
                    
                    # Convert pub_time epoch to datetime string
                    pub_date = "Recent"
                    if pub_time:
                        try:
                            pub_date = datetime.fromtimestamp(pub_time).strftime('%Y-%m-%d %H:%M')
                        except Exception:
                            pass
                            
                    articles.append({
                        "ticker": ticker,
                        "title": title,
                        "link": link,
                        "publisher": publisher,
                        "date": pub_date,
                        "timestamp": pub_time
                    })
        except Exception:
            pass
            
    # Sort articles by publish timestamp in descending order
    articles = sorted(articles, key=lambda x: x.get("timestamp", 0), reverse=True)
    return articles[:max_articles]

def fetch_benchmark_performance(start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Fetches S&P 500 index (^GSPC) price history from start_date to end_date.
    
    Computes cumulative performance relative to start_date to compare 
    directly against the user's capital allocations.
    """
    try:
        # Standardize dates
        start_str = start_date.strftime('%Y-%m-%d')
        # Include buffer up to today's date for latest index data
        end_str = datetime.now().strftime('%Y-%m-%d')
        
        benchmark = yf.download("^GSPC", start=start_str, end=end_str, progress=False)
        if benchmark.empty:
            return pd.DataFrame()
            
        benchmark = benchmark.reset_index()
        # Clean columns from multi-index if returned
        if isinstance(benchmark.columns, pd.MultiIndex):
            benchmark.columns = [col[0] for col in benchmark.columns]
            
        benchmark.columns = [col.lower().strip() for col in benchmark.columns]
        
        # Calculate daily cumulative returns: Close_t / Close_0
        first_close = float(benchmark.loc[0, "close"])
        benchmark["cumulative_return"] = benchmark["close"] / first_close
        
        return benchmark[["date", "close", "cumulative_return"]]
    except Exception:
        return pd.DataFrame()
