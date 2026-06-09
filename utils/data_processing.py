import pandas as pd
from typing import Union, Tuple
import io
import streamlit as st
from utils.auth_manager import is_authenticated
from database.db_models import SessionLocal, Transaction

def validate_and_clean_csv(file_source: Union[str, io.BytesIO, io.StringIO]) -> Tuple[pd.DataFrame, str]:
    """
    Validates and cleans the uploaded transaction history CSV file.
    
    Checks for:
    1. Correct headers: ticker, date, transaction_type, quantity, price.
    2. Missing values in critical columns.
    3. Proper data types and positive values for quantity and price.
    4. Valid transaction types (Buy or Sell).
    5. Chronological order sorting.
    6. Portfolio balance verification: ensuring cumulative shares of any ticker 
       never drop below zero (no selling shares you do not own).

    Returns:
        Tuple[pd.DataFrame, str]: A cleaned, validated, chronologically sorted DataFrame 
                                  and a success status message.
    Raises:
        ValueError: If validation fails.
    """
    try:
        # Load the CSV
        df = pd.read_csv(file_source)
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {str(e)}")
        
    # 1. Header Validation
    required_cols = {"ticker", "date", "transaction_type", "quantity", "price"}
    actual_cols = {col.lower().strip() for col in df.columns}
    
    missing_cols = required_cols - actual_cols
    if missing_cols:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing_cols)}. Required columns are: {', '.join(required_cols)}")
        
    # Standardize column names to lowercase and strip whitespace
    df.columns = [col.lower().strip() for col in df.columns]
    
    # Keep only the required columns (discard any extra ones)
    df = df[list(required_cols)]
    
    # 2. Data Validation and Cleaning
    # Remove rows that are entirely null
    df = df.dropna(how="all")
    
    # Ticker cleaning: Capitalize, strip spaces
    if df["ticker"].isnull().any():
        raise ValueError("CSV contains missing ticker values.")
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    
    # Date cleaning: Convert to datetime, check for invalid dates
    if df["date"].isnull().any():
        raise ValueError("CSV contains missing date values.")
    try:
        df["date"] = pd.to_datetime(df["date"])
    except Exception as e:
        raise ValueError(f"Failed to parse dates. Ensure dates are in YYYY-MM-DD or standard datetime format. Error: {str(e)}")
        
    # Transaction type validation: "Buy" or "Sell"
    if df["transaction_type"].isnull().any():
        raise ValueError("CSV contains missing transaction_type values.")
    df["transaction_type"] = df["transaction_type"].astype(str).str.strip().str.capitalize()
    
    invalid_types = set(df["transaction_type"].unique()) - {"Buy", "Sell"}
    if invalid_types:
        raise ValueError(f"Invalid transaction_type value(s) found: {', '.join(invalid_types)}. Must be strictly 'Buy' or 'Sell'.")
        
    # Quantity validation: Must be numeric, positive
    if df["quantity"].isnull().any():
        raise ValueError("CSV contains missing quantity values.")
    try:
        df["quantity"] = pd.to_numeric(df["quantity"])
    except Exception:
        raise ValueError("Quantity column contains non-numeric values.")
        
    if (df["quantity"] <= 0).any():
        raise ValueError("Quantity must be greater than zero for all transactions.")
        
    # Price validation: Must be numeric, positive
    if df["price"].isnull().any():
        raise ValueError("CSV contains missing price values.")
    try:
        df["price"] = pd.to_numeric(df["price"])
    except Exception:
        raise ValueError("Price column contains non-numeric values.")
        
    if (df["price"] <= 0).any():
        raise ValueError("Price must be greater than zero for all transactions.")
        
    # 3. Sort Chronologically
    df = df.sort_values(by="date").reset_index(drop=True)
    
    # 4. Strict Balance Validation (FIFO prerequisites)
    holdings = {} # ticker -> running quantity
    
    for idx, row in df.iterrows():
        ticker = row["ticker"]
        t_type = row["transaction_type"]
        qty = row["quantity"]
        date_str = row["date"].strftime('%Y-%m-%d')
        
        if ticker not in holdings:
            holdings[ticker] = 0.0
            
        if t_type == "Buy":
            holdings[ticker] += qty
        elif t_type == "Sell":
            holdings[ticker] -= qty
            # Check for negative balance
            if holdings[ticker] < -1e-9:  # tolerance for floating point rounding
                raise ValueError(
                    f"Invalid Transaction: Ticker '{ticker}' balance went negative ({holdings[ticker] + qty:.4f} -> {holdings[ticker]:.4f}) "
                    f"on {date_str} due to selling shares not owned."
                )
                
    success_msg = f"Data validation successful! Cleaned and sorted {len(df)} transactions chronologically."
    return df, success_msg

def load_portfolio_data() -> pd.DataFrame:
    """Loads portfolio data depending on authentication status."""
    if is_authenticated():
        user_id = st.session_state.get("user_id")
        db = SessionLocal()
        try:
            txs = db.query(Transaction).filter(Transaction.user_id == user_id).all()
            if not txs:
                return pd.DataFrame()
            
            data = [{
                "ticker": t.ticker,
                "date": pd.to_datetime(t.date),
                "transaction_type": t.transaction_type,
                "quantity": t.quantity,
                "price": t.price
            } for t in txs]
            df = pd.DataFrame(data)
            return df.sort_values(by="date").reset_index(drop=True)
        finally:
            db.close()
    else:
        # Guest Mode
        return st.session_state.get("portfolio_df", pd.DataFrame())

def save_portfolio_data(df: pd.DataFrame):
    """Saves portfolio data depending on authentication status."""
    if is_authenticated():
        user_id = st.session_state.get("user_id")
        db = SessionLocal()
        try:
            # Replace existing to avoid duplicates on re-upload
            db.query(Transaction).filter(Transaction.user_id == user_id).delete()
            
            for _, row in df.iterrows():
                tx = Transaction(
                    user_id=user_id,
                    ticker=row["ticker"],
                    date=row["date"].strftime('%Y-%m-%d'),
                    transaction_type=row["transaction_type"],
                    quantity=row["quantity"],
                    price=row["price"]
                )
                db.add(tx)
            db.commit()
            
            # also save to session state for fast cache
            st.session_state["portfolio_df"] = df
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    else:
        # Guest Mode
        st.session_state["portfolio_df"] = df
