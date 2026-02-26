import streamlit as st
import pandas as pd
from datetime import date
import requests
import plotly.express as px
from firebase_config import get_db

db = get_db()

st.set_page_config(page_title="Money Manager", layout="wide")

# ---------------- AUTH CONFIG ----------------
FIREBASE_API_KEY = st.secrets["auth"]["api_key"]

def firebase_email_signup(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(url, json=payload).json()

def firebase_email_login(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(url, json=payload).json()

# ---------------- LOGIN UI ----------------
if not st.experimental_user.is_logged_in:
    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is None:
        st.title("Money Manager 💸")
        st.markdown("Please sign in to continue")

        tab1, tab2 = st.tabs(["Login", "Sign Up"])

        with tab1:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login"):
                resp = firebase_email_login(email, password)
                if "localId" in resp:
                    st.session_state.user = {"uid": resp["localId"], "email": resp["email"]}
                    st.rerun()
                else:
                    st.error(resp.get("error", {}).get("message", "Login failed"))

            st.divider()
            st.markdown("Or sign in with Google")
            if st.button("Continue with Google"):
                st.login("google")

        with tab2:
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_pass")
            if st.button("Create Account"):
                resp = firebase_email_signup(email, password)
                if "localId" in resp:
                    st.success("Account created. Please log in.")
                else:
                    st.error(resp.get("error", {}).get("message", "Signup failed"))

        st.stop()

# ---------------- GET USER INFO ----------------
if st.experimental_user.is_logged_in:
    uid = st.experimental_user.sub
    user_email = st.experimental_user.email
elif "user" in st.session_state and st.session_state.user:
    uid = st.session_state.user["uid"]
    user_email = st.session_state.user["email"]
else:
    st.stop()

# ---------------- LOGOUT ----------------
st.sidebar.success(f"Logged in as {user_email}")
if st.sidebar.button("Logout"):
    if st.experimental_user.is_logged_in:
        st.logout()
    else:
        st.session_state.user = None
        st.rerun()

# ---------------- UI THEME ----------------
dark_mode = st.sidebar.toggle("Dark mode", value=False)

if dark_mode:
    theme_css = """
    <style>
    .main {
        background: linear-gradient(135deg, #0f172a, #1e293b);
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    h1, h2, h3 {
        color: #f8fafc;
        font-weight: 600;
        letter-spacing: -0.3px;
    }

    .kpi-card {
        background: #1e293b;
        padding: 1.2rem 1.4rem;
        border-radius: 16px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.25);
        transition: all 0.2s ease;
        border: 1px solid rgba(255,255,255,0.05);
    }

    .kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.35);
    }

    .kpi-title {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }

    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        margin-top: 0.3rem;
        color: #ffffff;
    }

    .stButton>button {
        background: linear-gradient(135deg, #6366f1, #4f46e5);
        color: white;
        border-radius: 12px;
        border: none;
        padding: 0.6rem 1.4rem;
        font-weight: 500;
        transition: all 0.2s ease;
    }

    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
    }
    </style>
    """
else:
    theme_css = """
    <style>
    .main {
        background: linear-gradient(135deg, #f8fafc, #eef2ff);
        font-family: 'Inter', sans-serif;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    h1 {
        font-size: 2.4rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        color: #0f172a;
    }

    h2, h3 {
        color: #1e293b;
    }

    .kpi-card {
        background: white;
        padding: 1.2rem 1.4rem;
        border-radius: 16px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .kpi-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 30px rgba(15, 23, 42, 0.15);
    }

    .kpi-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #64748b;
    }

    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        margin-top: 0.3rem;
        color: #0f172a;
    }

    .stButton>button {
        background: linear-gradient(135deg, #0f172a, #1e293b);
        color: white;
        border-radius: 12px;
        border: none;
        padding: 0.6rem 1.4rem;
        font-weight: 500;
        transition: all 0.2s ease;
    }

    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.2);
    }
    </style>
    """
st.markdown(theme_css, unsafe_allow_html=True)

st.title("Money Manager 💸")
st.markdown("Money saved is equal to money earned")

CATEGORIES = ["Food", "Transport", "Bills", "Shopping", "Entertainment", "Health", "Education", "Other"]
PAYMENT_MODES = ["Cash", "Card", "UPI", "Bank Transfer", "Wallet", "Other"]

expenses_ref = db.collection("users").document(uid).collection("expenses")

# ---------- SIDEBAR: ADD EXPENSE ----------
with st.sidebar:
    st.header("Add Expense")
    expense = st.text_input("Enter expense")
    amount = st.number_input("Enter amount", min_value=0.0, step=50.0, format="%.2f")
    expense_date = st.date_input("Expense date", value=date.today())

    category = st.selectbox("Category", CATEGORIES + ["Other"])
    if category == "Other":
        category_other = st.text_input("Custom category")
        if category_other:
            category = category_other.strip()

    payment_mode = st.selectbox("Payment mode", PAYMENT_MODES + ["Other"])
    if payment_mode == "Other":
        payment_other = st.text_input("Custom payment mode")
        if payment_other:
            payment_mode = payment_other.strip()

    if st.button("Add Expense"):
        if expense:
            expenses_ref.add({
                "expense": expense.strip(),
                "amount": float(amount),
                "category": category,
                "payment_mode": payment_mode,
                "date": expense_date.isoformat()
            })
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
    for col in ["expense", "amount", "category", "payment_mode", "date"]:
        if col not in df.columns:
            df[col] = ""

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["category"] = df["category"].fillna("").replace("", "Uncategorized")
    df["payment_mode"] = df["payment_mode"].fillna("").replace("", "Unknown")
    df["date"] = df["date"].fillna("").replace("", "Unknown")

    df["sort_date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values(by="sort_date", ascending=False, na_position="last")

    # ---------- FILTERS ----------
    st.subheader("Filters")
    show_all = st.checkbox("Show all expenses", value=True)

    if show_all:
        filtered_df = df.copy()
    else:
        min_date = df["sort_date"].min()
        max_date = df["sort_date"].max()

        if pd.notna(min_date) and pd.notna(max_date):
            date_range = st.date_input(
                "Select date range",
                value=(min_date.date(), max_date.date())
            )
        else:
            date_range = (date.today(), date.today())

        category_options = sorted(df["category"].unique())
        payment_options = sorted(df["payment_mode"].unique())

        category_filter = st.multiselect("Filter by category", category_options, default=category_options)
        payment_filter = st.multiselect("Filter by payment mode", payment_options, default=payment_options)

        filtered_df = df[
            df["category"].isin(category_filter) &
            df["payment_mode"].isin(payment_filter)
        ]

        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            filtered_df = filtered_df[
                (filtered_df["sort_date"] >= pd.to_datetime(start_date)) &
                (filtered_df["sort_date"] <= pd.to_datetime(end_date))
            ]

    # ---------- KPI CARDS ----------
    total = filtered_df["amount"].sum()
    month_total = filtered_df[
        filtered_df["sort_date"].dt.month == date.today().month
    ]["amount"].sum()
    avg_entry = total / max(len(filtered_df), 1)
    if not filtered_df.empty:
        category_summary = filtered_df.groupby("category")["amount"].sum()
        top_category = category_summary.idxmax()
        top_category_amount = category_summary.max()
    else:
        top_category = "N/A"
        top_category_amount = 0

    col1, col2, col3 = st.columns(3)
    col1.markdown(f"<div class='kpi-card'><div class='kpi-title'>Total Expense</div><div class='kpi-value'>₹{total:,.2f}</div></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='kpi-card'><div class='kpi-title'>This Month</div><div class='kpi-value'>₹{month_total:,.2f}</div></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='kpi-card'><div class='kpi-title'>Top Category</div><div class='kpi-value'>{top_category}<br>₹{top_category_amount:,.2f}</div></div>", unsafe_allow_html=True)

    # ---------- TABLE + DOWNLOAD ----------
    st.subheader("Expenses")
    st.dataframe(
        filtered_df[["date", "expense", "amount", "category", "payment_mode"]],
        use_container_width=True,
        hide_index=True
    )

    csv_data = filtered_df[["date", "expense", "amount", "category", "payment_mode"]].to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv_data, file_name="expenses.csv", mime="text/csv")

    # ---------- CHARTS (PLOTLY) ----------
    st.subheader("Spending Trend")
    trend = filtered_df.dropna(subset=["sort_date"]).copy()
    trend = trend.groupby(trend["sort_date"].dt.date)["amount"].sum().reset_index()
    fig_trend = px.line(trend, x="sort_date", y="amount", markers=True)
    fig_trend.update_layout(xaxis_title="Date", yaxis_title="Amount")
    st.plotly_chart(fig_trend, use_container_width=True)

    col4, col5 = st.columns(2)

    with col4:
        st.subheader("Category Split")
        cat_chart = filtered_df.groupby("category")["amount"].sum().reset_index()
        fig_pie = px.pie(cat_chart, names="category", values="amount", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col5:
        st.subheader("Monthly Spending")
        monthly = filtered_df.dropna(subset=["sort_date"]).copy()
        monthly["month"] = monthly["sort_date"].dt.to_period("M").astype(str)
        monthly_sum = monthly.groupby("month")["amount"].sum().reset_index()
        fig_bar = px.bar(monthly_sum, x="month", y="amount")
        fig_bar.update_layout(xaxis_title="Month", yaxis_title="Amount")
        st.plotly_chart(fig_bar, use_container_width=True)

    # ---------- SIDEBAR: DELETE + UPDATE ----------
    action_df = filtered_df.copy()

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
                    f"Rs {action_df.loc[action_df['id'] == x, 'amount'].values[0]:.2f} "
                    f"[{action_df.loc[action_df['id'] == x, 'category'].values[0]}, "
                    f"{action_df.loc[action_df['id'] == x, 'payment_mode'].values[0]}]"
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
                    f"Rs {action_df.loc[action_df['id'] == x, 'amount'].values[0]:.2f}"
                ),
                key="edit_id",
            )

            selected_row = action_df[action_df["id"] == edit_id].iloc[0]

            new_expense = st.text_input("Update expense name", value=selected_row["expense"])
            new_amount = st.number_input(
                "Update amount",
                min_value=0.0,
                value=float(selected_row["amount"]),
                step=50.0,
                format="%.2f",
            )

            try:
                selected_date = pd.to_datetime(selected_row["date"]).date()
            except Exception:
                selected_date = date.today()

            new_date = st.date_input("Update date", value=selected_date)

            category_options = sorted(set(CATEGORIES + action_df["category"].tolist() + ["Other"]))
            current_cat = selected_row["category"] if selected_row["category"] in category_options else "Other"
            new_category = st.selectbox(
                "Update category",
                category_options,
                index=category_options.index(current_cat),
            )

            payment_options = sorted(set(PAYMENT_MODES + action_df["payment_mode"].tolist() + ["Other"]))
            current_pay = selected_row["payment_mode"] if selected_row["payment_mode"] in payment_options else "Other"
            new_payment_mode = st.selectbox(
                "Update payment mode",
                payment_options,
                index=payment_options.index(current_pay),
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
    st.warning("No expenses added yet")
