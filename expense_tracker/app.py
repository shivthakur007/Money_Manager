import streamlit as st
import pandas as pd
from datetime import date
import requests
import plotly.express as px
import urllib.parse
import secrets
from firebase_config import get_db

db = get_db()

st.set_page_config(page_title="Money Manager", layout="wide")

# ---------------- AUTH CONFIG ----------------
FIREBASE_API_KEY = st.secrets["auth"]["api_key"]
GOOGLE_CLIENT_ID = st.secrets["auth"]["google_client_id"]
REDIRECT_URI = st.secrets["auth"]["redirect_uri"]

# ---------------- FIREBASE AUTH ----------------

def firebase_email_signup(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(url, json=payload).json()


def firebase_email_login(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(url, json=payload).json()


def firebase_google_login(id_token):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key={FIREBASE_API_KEY}"
    payload = {
        "postBody": f"id_token={id_token}&providerId=google.com",
        "requestUri": REDIRECT_URI,
        "returnSecureToken": True,
        "returnIdpCredential": True,
    }
    return requests.post(url, json=payload).json()


# ---------------- GOOGLE LOGIN (FIREBASE NATIVE) ----------------

def get_google_auth_url():
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"

    nonce = secrets.token_urlsafe(16)
    st.session_state["oauth_nonce"] = nonce

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "id_token",
        "scope": "openid email profile",
        "nonce": nonce,
        "prompt": "select_account",
    }

    return f"{base_url}?{urllib.parse.urlencode(params)}"


# ---------------- SESSION ----------------

if "user" not in st.session_state:
    st.session_state.user = None


# ---------------- LOGIN SCREEN ----------------

if st.session_state.user is None:
    st.title("Money Manager 💸")
    st.markdown("Please sign in to continue")

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login"):
            resp = firebase_email_login(email, password)
            if resp.get("idToken"):
                st.session_state.user = {
                    "uid": resp["localId"],
                    "email": resp["email"],
                }
                st.rerun()
            else:
                st.error(resp.get("error", {}).get("message", "Login failed"))

        st.divider()
        st.markdown("Or sign in with Google")

        google_url = get_google_auth_url()
        st.link_button("Continue with Google", google_url)

    with tab2:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pass")

        if st.button("Create Account"):
            resp = firebase_email_signup(email, password)
            if resp.get("idToken"):
                st.success("Account created. Please log in.")
            else:
                st.error(resp.get("error", {}).get("message", "Signup failed"))

    # ---- Handle Google Redirect ----
    query = st.query_params

    if "id_token" in query and st.session_state.user is None:
        id_token = query["id_token"]
        if isinstance(id_token, (list, tuple)):
            id_token = id_token[0]

        resp = firebase_google_login(id_token)

        if resp.get("idToken"):
            st.session_state.user = {
                "uid": resp["localId"],
                "email": resp["email"],
            }

            st.query_params.clear()
            st.rerun()
        else:
            st.error("Google login failed.")
            st.query_params.clear()

    st.stop()


# ---------------- LOGOUT ----------------

st.sidebar.success(f"Logged in as {st.session_state.user['email']}")

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()


# ---------------- MAIN APP ----------------

st.title("Money Manager 💸")
st.markdown("Money saved is equal to money earned")

CATEGORIES = ["Food", "Transport", "Bills", "Shopping", "Entertainment", "Health", "Education", "Other"]
PAYMENT_MODES = ["Cash", "Card", "UPI", "Bank Transfer", "Wallet", "Other"]

uid = st.session_state.user["uid"]
expenses_ref = db.collection("users").document(uid).collection("expenses")


# ---------- ADD EXPENSE ----------
with st.sidebar:
    st.header("Add Expense")
    expense = st.text_input("Enter expense")
    amount = st.number_input("Enter amount", min_value=0.0, step=50.0)
    expense_date = st.date_input("Expense date", value=date.today())

    category = st.selectbox("Category", CATEGORIES)
    payment_mode = st.selectbox("Payment mode", PAYMENT_MODES)

    if st.button("Add Expense"):
        if expense:
            expenses_ref.add(
                {
                    "expense": expense.strip(),
                    "amount": float(amount),
                    "category": category,
                    "payment_mode": payment_mode,
                    "date": expense_date.isoformat(),
                }
            )
            st.success("Expense added")
            st.rerun()
        else:
            st.warning("Please enter an expense")


# ---------- READ EXPENSES ----------
docs = expenses_ref.stream()
data = []

for doc in docs:
    row = doc.to_dict()
    row["id"] = doc.id
    data.append(row)

df = pd.DataFrame(data)

if not df.empty:

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["sort_date"] = pd.to_datetime(df["date"], errors="coerce")

    df = df.sort_values(by="sort_date", ascending=False)

    # ---------- KPIs ----------
    total = df["amount"].sum()

    today = date.today()
    month_total = df[
        (df["sort_date"].dt.month == today.month)
        & (df["sort_date"].dt.year == today.year)
    ]["amount"].sum()

    category_summary = df.groupby("category")["amount"].sum()
    top_category = category_summary.idxmax()
    top_category_amount = category_summary.max()

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Expense", f"₹{total:,.2f}")
    col2.metric("This Month", f"₹{month_total:,.2f}")
    col3.metric("Top Category", f"{top_category} (₹{top_category_amount:,.2f})")

    # ---------- TABLE ----------
    st.subheader("Expenses")
    st.dataframe(
        df[["date", "expense", "amount", "category", "payment_mode"]],
        use_container_width=True,
        hide_index=True,
    )

    # ---------- CHARTS ----------
    st.subheader("Spending Trend")

    trend = df.groupby(df["sort_date"].dt.date)["amount"].sum().reset_index()

    if not trend.empty:
        fig = px.line(trend, x="sort_date", y="amount", markers=True)
        st.plotly_chart(fig, use_container_width=True)

    # ---------- DELETE + UPDATE ----------
    action_df = df.copy()

    with st.sidebar:
        st.header("Delete Expense")

        if action_df.empty:
            st.warning("No expenses available")
        else:
            del_id = st.selectbox(
                "Select expense to delete",
                options=action_df["id"],
                format_func=lambda x: (
                    f"{action_df.loc[action_df['id'] == x, 'date'].values[0]} - "
                    f"{action_df.loc[action_df['id'] == x, 'expense'].values[0]} - "
                    f"₹{action_df.loc[action_df['id'] == x, 'amount'].values[0]:.2f}"
                ),
                key="delete_id",
            )

            if st.button("Delete Expense"):
                expenses_ref.document(del_id).delete()
                st.success("Expense deleted")
                st.rerun()

            st.header("Update Expense")

            edit_id = st.selectbox(
                "Select expense to edit",
                options=action_df["id"],
                format_func=lambda x: (
                    f"{action_df.loc[action_df['id'] == x, 'date'].values[0]} - "
                    f"{action_df.loc[action_df['id'] == x, 'expense'].values[0]} - "
                    f"₹{action_df.loc[action_df['id'] == x, 'amount'].values[0]:.2f}"
                ),
                key="edit_id",
            )

            selected_row = action_df[action_df["id"] == edit_id].iloc[0]

            new_expense = st.text_input(
                "Update expense name",
                value=selected_row["expense"],
            )

            new_amount = st.number_input(
                "Update amount",
                min_value=0.0,
                value=float(selected_row["amount"]),
                step=50.0,
            )

            try:
                selected_date = pd.to_datetime(selected_row["date"]).date()
            except:
                selected_date = date.today()

            new_date = st.date_input("Update date", value=selected_date)

            new_category = st.selectbox(
                "Update category",
                CATEGORIES,
                index=CATEGORIES.index(selected_row["category"])
                if selected_row["category"] in CATEGORIES
                else 0,
            )

            new_payment_mode = st.selectbox(
                "Update payment mode",
                PAYMENT_MODES,
                index=PAYMENT_MODES.index(selected_row["payment_mode"])
                if selected_row["payment_mode"] in PAYMENT_MODES
                else 0,
            )

            if st.button("Update Expense"):
                expenses_ref.document(edit_id).update(
                    {
                        "expense": new_expense.strip(),
                        "amount": float(new_amount),
                        "category": new_category,
                        "payment_mode": new_payment_mode,
                        "date": new_date.isoformat(),
                    }
                )
                st.success("Expense updated")
                st.rerun()
else:
    st.warning("No expenses added yet.")
