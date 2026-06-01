import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, date
from collections import deque, defaultdict
from typing import Dict, List, Tuple, Any

def calculate_fifo_holdings(df: pd.DataFrame) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, float]]:
    """
    Computes active holdings and cost basis using the First-In-First-Out (FIFO) method,
    along with cumulative realized gains per ticker.

    Args:
        df (pd.DataFrame): Validated, chronologically sorted transaction DataFrame.

    Returns:
        Tuple[Dict, Dict]: 
            - active_holdings: Maps ticker -> {
                "shares": float, 
                "total_cost": float, 
                "avg_cost": float, 
                "lots": List[Dict]
              }
            - realized_gains: Maps ticker -> total realized gains (float)
    """
    lots = defaultdict(deque) # ticker -> deque of buy lots
    realized_gains = defaultdict(float) # ticker -> realized gains

    for _, row in df.iterrows():
        ticker = row["ticker"]
        t_type = row["transaction_type"]
        qty = float(row["quantity"])
        price = float(row["price"])
        tx_date = row["date"]

        if t_type == "Buy":
            # Add a new tax lot
            lots[ticker].append({
                "date": tx_date,
                "quantity": qty,
                "price": price
            })
        elif t_type == "Sell":
            sell_qty_remaining = qty
            while sell_qty_remaining > 0:
                if not lots[ticker]:
                    # Edge case fallback (though validated in data_processing)
                    break
                
                oldest_lot = lots[ticker][0]
                lot_qty = oldest_lot["quantity"]
                lot_price = oldest_lot["price"]

                if lot_qty > sell_qty_remaining:
                    # Partial consumption of oldest lot
                    gain = sell_qty_remaining * (price - lot_price)
                    realized_gains[ticker] += gain
                    oldest_lot["quantity"] -= sell_qty_remaining
                    sell_qty_remaining = 0
                else:
                    # Full consumption of oldest lot
                    gain = lot_qty * (price - lot_price)
                    realized_gains[ticker] += gain
                    sell_qty_remaining -= lot_qty
                    lots[ticker].popleft()

    # Aggregate remaining lots into active holdings
    active_holdings = {}
    for ticker, lot_queue in lots.items():
        total_shares = sum(lot["quantity"] for lot in lot_queue)
        if total_shares > 1e-9: # Filter out insignificant remainder
            total_cost = sum(lot["quantity"] * lot["price"] for lot in lot_queue)
            avg_cost = total_cost / total_shares
            
            active_holdings[ticker] = {
                "shares": total_shares,
                "total_cost": total_cost,
                "avg_cost": avg_cost,
                "lots": list(lot_queue)
            }

    return active_holdings, dict(realized_gains)

def fetch_current_prices(tickers: List[str]) -> Dict[str, float]:
    """
    Fetches the latest close market price for a list of tickers from yfinance.
    
    Includes multi-tiered fallback checks (fast_info, history close, info)
    to ensure robust behavior under any API conditions.
    """
    if not tickers:
        return {}

    prices = {}
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            # Tier 1: fast_info (super fast, no full metadata request)
            last_price = t.fast_info.get("last_price", None)
            if last_price is not None and not np.isnan(last_price) and last_price > 0:
                prices[ticker] = float(last_price)
                continue
                
            # Tier 2: history close
            hist = t.history(period="5d")
            if not hist.empty:
                prices[ticker] = float(hist["Close"].iloc[-1])
                continue
                
            # Tier 3: regularMarketPrice
            market_price = t.info.get("regularMarketPrice", None)
            if market_price is not None:
                prices[ticker] = float(market_price)
            else:
                prices[ticker] = 0.0
        except Exception:
            prices[ticker] = 0.0

    return prices

def xirr_cash_flow_valuation(r: float, cash_flows: List[Tuple[datetime, float]]) -> float:
    """
    Computes NPV of cash flows at annualized discount rate r.
    Formula: NPV = Sum ( CashFlow_i / (1 + r)^((Date_i - Date_0)/365) )
    """
    if not cash_flows:
        return 0.0
    t0 = cash_flows[0][0]
    npv = 0.0
    for d, val in cash_flows:
        years = (d - t0).days / 365.0
        # Prevent division by zero or negative base errors when discount rate is close to -100%
        if r <= -1.0:
            r = -0.999
        npv += val / ((1.0 + r) ** years)
    return npv

def calculate_portfolio_xirr(df: pd.DataFrame, current_prices: Dict[str, float], active_holdings: Dict[str, Dict[str, Any]]) -> float:
    """
    Calculates the Extended Internal Rate of Return (XIRR) for the consolidated portfolio.
    
    Cash flows include:
    - Negative cash flows for 'Buy' transactions (outflows to buy stock).
    - Positive cash flows for 'Sell' transactions (inflows from selling stock).
    - A final positive cash flow equal to the current valuation of active holdings 
      evaluated at the current date (today).
      
    Returns:
        float: Annualized XIRR return rate (e.g. 0.125 for 12.5%). Returns 0.0 if XIRR 
               cannot be solved or has no convergence.
    """
    cash_flows = []
    
    # 1. Map transaction cash flows
    for _, row in df.iterrows():
        t_type = row["transaction_type"]
        qty = float(row["quantity"])
        price = float(row["price"])
        tx_date = row["date"]
        
        # Convert date to datetime if it's timestamp
        if isinstance(tx_date, pd.Timestamp):
            dt = tx_date.to_pydatetime()
        elif isinstance(tx_date, (date, datetime)):
            dt = datetime(tx_date.year, tx_date.month, tx_date.day)
        else:
            dt = pd.to_datetime(tx_date).to_pydatetime()
            
        value = qty * price
        
        if t_type == "Buy":
            cash_flows.append((dt, -value))
        elif t_type == "Sell":
            cash_flows.append((dt, value))
            
    # 2. Add current valuation as final positive inflow today
    today = datetime.now()
    current_val = 0.0
    for ticker, holding in active_holdings.items():
        price = current_prices.get(ticker, 0.0)
        current_val += holding["shares"] * price
        
    if current_val > 0:
        cash_flows.append((today, current_val))
        
    # Sort chronologically
    cash_flows = sorted(cash_flows, key=lambda x: x[0])
    
    # Verify we have at least one negative and one positive cash flow
    amounts = [cf[1] for cf in cash_flows]
    if all(a >= 0 for a in amounts) or all(a <= 0 for a in amounts):
        return 0.0
        
    # 3. Solver implementation (Secant method falling back to Bisection)
    # Secant Method
    r0 = 0.1
    r1 = 0.15
    f0 = xirr_cash_flow_valuation(r0, cash_flows)
    
    for _ in range(100):
        f1 = xirr_cash_flow_valuation(r1, cash_flows)
        if abs(f1 - f0) < 1e-12:
            break
        r_next = r1 - f1 * (r1 - r0) / (f1 - f0)
        
        if abs(r_next - r1) < 1e-6:
            if -0.99 < r_next < 10.0:
                return float(r_next)
                
        r0, r1 = r1, r_next
        f0 = f1
        
    # Bisection Method Fallback
    low = -0.99
    high = 5.0
    f_low = xirr_cash_flow_valuation(low, cash_flows)
    f_high = xirr_cash_flow_valuation(high, cash_flows)
    
    if f_low * f_high < 0:
        for _ in range(100):
            mid = (low + high) / 2.0
            f_mid = xirr_cash_flow_valuation(mid, cash_flows)
            if abs(f_mid) < 1e-6:
                return float(mid)
            if f_low * f_mid < 0:
                high = mid
                f_high = f_mid
            else:
                low = mid
                f_low = f_mid
        return float((low + high) / 2.0)
        
    # Simple ROI fallback if XIRR fails to converge
    total_invested = sum(-cf[1] for cf in cash_flows if cf[1] < 0)
    total_returned = sum(cf[1] for cf in cash_flows if cf[1] > 0)
    if total_invested > 0:
        simple_roi = (total_returned - total_invested) / total_invested
        # Return simple annualized return based on total days elapsed
        days_elapsed = (cash_flows[-1][0] - cash_flows[0][0]).days
        if days_elapsed > 0:
            annualized_roi = (1 + simple_roi) ** (365.0 / days_elapsed) - 1.0
            return float(annualized_roi)
            
    return 0.0
