import streamlit as st
import pandas as pd
from datetime import date
import requests
import plotly.express as px
from firebase_config import get_db

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Money Manager", layout="wide")

db = get_db()
FIREBASE_API_KEY = st.secrets["auth"]["api_key"]

# ---------------- FIREBASE AUTH FUNCTIONS ----------------
def firebase_email_signup(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(url, json=payload).json()


def firebase_email_login(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(url, json=payload).json()


# ---------------- SESSION INIT ----------------
if "user" not in st.session_state:
    st.session_state.user = None


# ---------------- LOGIN UI ----------------
if not st.session_state.user:
    st.title("Money Manager 💸")
    st.markdown("Please sign in to continue")

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login"):
            resp = firebase_email_login(email, password)

            if "localId" in resp:
                st.session_state.user = {
                    "uid": resp["localId"],
                    "email": resp["email"],
                }
                st.rerun()
            else:
                st.error(resp.get("error", {}).get("message", "Login failed"))

    with tab2:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pass")

        if st.button("Create Account"):
            resp = firebase_email_signup(email, password)

            if "localId" in resp:
                st.success("Account created successfully. Please login.")
            else:
                st.error(resp.get("error", {}).get("message", "Signup failed"))

    st.stop()   # 🔥 IMPORTANT — stops app if not logged in


# ---------------- AUTHENTICATED APP ----------------

# Sidebar logout
st.sidebar.success(f"Logged in as {st.session_state.user.get('email')}")
if st.sidebar.button("Logout"):
    del st.session_state["user"]
    st.rerun()


st.title("Money Manager 💸")
st.markdown("Money saved is equal to money earned")

# ---------------- FIRESTORE REFERENCE ----------------
uid = st.session_state.user["uid"]
expenses_ref = db.collection("users").document(uid).collection("expenses")

CATEGORIES = ["Food", "Transport", "Bills", "Shopping", "Entertainment", "Health", "Education", "Other"]
PAYMENT_MODES = ["Cash", "Card", "UPI", "Bank Transfer", "Wallet", "Other"]


# ---------------- ADD EXPENSE ----------------
with st.sidebar:
    st.header("Add Expense")

    expense = st.text_input("Expense")
    amount = st.number_input("Amount", min_value=0.0, step=50.0)
    expense_date = st.date_input("Date", value=date.today())

    category = st.selectbox("Category", CATEGORIES)
    payment_mode = st.selectbox("Payment Mode", PAYMENT_MODES)

    if st.button("Add Expense"):
        if expense.strip():
            expenses_ref.add(
                {
                    "expense": expense.strip(),
                    "amount": float(amount),
                    "category": category,
                    "payment_mode": payment_mode,
                    "date": expense_date.isoformat(),
                }
            )
            st.success("Expense Added")
            st.rerun()
        else:
            st.warning("Enter expense name")


# ---------------- READ DATA ----------------
docs = expenses_ref.stream()
data = []

for doc in docs:
    row = doc.to_dict()
    row["id"] = doc.id
    data.append(row)

df = pd.DataFrame(data)

if df.empty:
    st.warning("No expenses added yet")
    st.stop()

df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
df["sort_date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.sort_values("sort_date", ascending=False)


# ---------------- KPIs ----------------
total = df["amount"].sum()
monthly_total = df[df["sort_date"].dt.month == date.today().month]["amount"].sum()

category_summary = df.groupby("category")["amount"].sum()
top_category = category_summary.idxmax()
top_category_amount = category_summary.max()

col1, col2, col3 = st.columns(3)

col1.metric("Total Expense", f"₹{total:,.2f}")
col2.metric("This Month", f"₹{monthly_total:,.2f}")
col3.metric("Top Category", f"{top_category} (₹{top_category_amount:,.2f})")


# ---------------- TABLE ----------------
st.subheader("All Expenses")
st.dataframe(
    df[["date", "expense", "amount", "category", "payment_mode"]],
    use_container_width=True,
)


# ---------------- DOWNLOAD ----------------
csv_data = df.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", csv_data, "expenses.csv", "text/csv")


# ---------------- CHARTS ----------------
st.subheader("Spending Trend")
trend = df.groupby(df["sort_date"].dt.date)["amount"].sum().reset_index()
fig_line = px.line(trend, x="sort_date", y="amount", markers=True)
st.plotly_chart(fig_line, use_container_width=True)

col4, col5 = st.columns(2)

with col4:
    st.subheader("Category Split")
    fig_pie = px.pie(df.groupby("category")["amount"].sum().reset_index(),
                     names="category",
                     values="amount",
                     hole=0.4)
    st.plotly_chart(fig_pie, use_container_width=True)

with col5:
    st.subheader("Monthly Spending")
    df["month"] = df["sort_date"].dt.to_period("M").astype(str)
    fig_bar = px.bar(df.groupby("month")["amount"].sum().reset_index(),
                     x="month",
                     y="amount")
    st.plotly_chart(fig_bar, use_container_width=True)

# ---------------- DELETE & UPDATE ----------------

st.sidebar.divider()
st.sidebar.header("Manage Expenses")

action_df = df.copy()

if not action_df.empty:

    # ---------- DELETE ----------
    delete_id = st.sidebar.selectbox(
        "Select expense to delete",
        options=action_df["id"],
        format_func=lambda x: (
            f"{action_df.loc[action_df['id']==x, 'date'].values[0]} | "
            f"{action_df.loc[action_df['id']==x, 'expense'].values[0]} | "
            f"₹{action_df.loc[action_df['id']==x, 'amount'].values[0]:.2f}"
        ),
        key="delete_select",
    )

    if st.sidebar.button("Delete Expense"):
        expenses_ref.document(delete_id).delete()
        st.sidebar.success("Expense Deleted")
        st.rerun()

    st.sidebar.divider()

    # ---------- UPDATE ----------
    st.sidebar.subheader("Update Expense")

    edit_id = st.sidebar.selectbox(
        "Select expense to edit",
        options=action_df["id"],
        format_func=lambda x: (
            f"{action_df.loc[action_df['id']==x, 'date'].values[0]} | "
            f"{action_df.loc[action_df['id']==x, 'expense'].values[0]}"
        ),
        key="edit_select",
    )

    selected_row = action_df[action_df["id"] == edit_id].iloc[0]

    new_expense = st.sidebar.text_input(
        "Expense Name",
        value=selected_row["expense"],
        key="edit_name",
    )

    new_amount = st.sidebar.number_input(
        "Amount",
        min_value=0.0,
        value=float(selected_row["amount"]),
        step=50.0,
        key="edit_amount",
    )

    try:
        selected_date = pd.to_datetime(selected_row["date"]).date()
    except Exception:
        selected_date = date.today()

    new_date = st.sidebar.date_input(
        "Date",
        value=selected_date,
        key="edit_date",
    )

    new_category = st.sidebar.selectbox(
        "Category",
        CATEGORIES,
        index=CATEGORIES.index(selected_row["category"])
        if selected_row["category"] in CATEGORIES else 0,
        key="edit_category",
    )

    new_payment = st.sidebar.selectbox(
        "Payment Mode",
        PAYMENT_MODES,
        index=PAYMENT_MODES.index(selected_row["payment_mode"])
        if selected_row["payment_mode"] in PAYMENT_MODES else 0,
        key="edit_payment",
    )

    if st.sidebar.button("Update Expense"):
        expenses_ref.document(edit_id).update(
            {
                "expense": new_expense.strip(),
                "amount": float(new_amount),
                "category": new_category,
                "payment_mode": new_payment,
                "date": new_date.isoformat(),
            }
        )
        st.sidebar.success("Expense Updated")
        st.rerun()

else:
    st.sidebar.warning("No expenses available")
