import streamlit as st
import bcrypt
from database.db_models import SessionLocal, User

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def init_auth_state():
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None # None means Guest
    if "username" not in st.session_state:
        st.session_state["username"] = "Guest"

def is_authenticated() -> bool:
    return st.session_state.get("user_id") is not None

def register_user(username, password):
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            return False, "Username already exists."
        
        new_user = User(
            username=username,
            password_hash=hash_password(password)
        )
        db.add(new_user)
        db.commit()
        return True, "Registration successful. Please log in."
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()

def login_user(username, password):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user and verify_password(password, user.password_hash):
            st.session_state["user_id"] = user.id
            st.session_state["username"] = user.username
            return True, "Login successful."
        return False, "Invalid username or password."
    finally:
        db.close()

def logout_user():
    st.session_state["user_id"] = None
    st.session_state["username"] = "Guest"
    # Clear portfolio data from session if any
    if "portfolio_df" in st.session_state:
        del st.session_state["portfolio_df"]
