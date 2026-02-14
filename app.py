import matplotlib
matplotlib.use("Agg")

import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
from datetime import date
from io import BytesIO
import sqlite3
import hashlib

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Smart Expense Manager", page_icon="💸", layout="wide")
DB_FILE = "app.db"

# ---------------- DB HELPERS ----------------
def get_db():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def verify_user(username, password):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    return row and row[0] == hash_password(password)

def update_password(username, new_password):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET password=? WHERE username=?", (hash_password(new_password), username))
    conn.commit()
    conn.close()

# ---------------- INIT DB ----------------
conn = get_db()
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    budget REAL DEFAULT 0
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    name TEXT,
    amount REAL,
    date TEXT,
    category TEXT
)
""")
conn.commit()

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# ---------------- AUTH UI ----------------
st.title("💼 Smart Expense Manager")
menu = ["Login", "Register", "Reset Password"]
choice = st.sidebar.selectbox("Account", menu)

if not st.session_state.logged_in:

    if choice == "Login":
        st.subheader("🔐 Login")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            if verify_user(u, p):
                st.session_state.logged_in = True
                st.session_state.username = u
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid credentials")

    elif choice == "Register":
        st.subheader("📝 Register")
        u = st.text_input("New Username")
        p = st.text_input("New Password", type="password")
        if st.button("Register"):
            try:
                c.execute("INSERT INTO users (username, password, budget) VALUES (?, ?, 0)",
                          (u, hash_password(p)))
                conn.commit()
                st.success("Account created! Login now.")
            except:
                st.error("Username already exists")

    elif choice == "Reset Password":
        st.subheader("🔁 Reset Password")
        u = st.text_input("Username")
        old_pw = st.text_input("Old Password", type="password")
        new_pw = st.text_input("New Password", type="password")

        if st.button("Reset Password"):
            if verify_user(u, old_pw):
                update_password(u, new_pw)
                st.success("Password updated successfully!")
            else:
                st.error("Invalid username or old password")

    st.stop()

# ---------------- LOGOUT ----------------
st.sidebar.success(f"Logged in as {st.session_state.username}")
if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

# ---------------- BUDGET ----------------
c.execute("SELECT budget FROM users WHERE username=?", (st.session_state.username,))
monthly_budget = c.fetchone()[0]

st.sidebar.header("🎯 Budget Settings")
new_budget = st.sidebar.number_input("Set Monthly Budget (₹)", 0.0, value=float(monthly_budget), step=500.0)
if st.sidebar.button("Save Budget"):
    c.execute("UPDATE users SET budget=? WHERE username=?", (new_budget, st.session_state.username))
    conn.commit()
    st.sidebar.success("Budget saved!")

# ---------------- LOAD EXPENSES ----------------
c.execute("SELECT name, amount, date, category FROM expenses WHERE username=?", (st.session_state.username,))
rows = c.fetchall()
df = pd.DataFrame(rows, columns=["Name", "Amount", "Date", "Category"])
if not df.empty:
    df["Date"] = pd.to_datetime(df["Date"]).dt.date

# ---------------- ADD EXPENSE ----------------
st.subheader("➕ Add Expense")
c1, c2, c3, c4 = st.columns(4)
with c1: name = st.text_input("Title")
with c2: amount = st.number_input("Amount (₹)", 0.0, step=1.0)
with c3: exp_date = st.date_input("Date", value=date.today())
with c4: category = st.selectbox("Category", ["Food","Travel","Shopping","Bills","Entertainment","Health","Other"])

if st.button("Add Expense", use_container_width=True):
    if name and amount > 0:
        c.execute("INSERT INTO expenses VALUES (NULL,?,?,?,?,?)",
                  (st.session_state.username, name, amount, str(exp_date), category))
        conn.commit()
        st.success("Expense added!")
        st.rerun()
    else:
        st.error("Invalid input")

st.divider()

# ---------------- DASHBOARD ----------------
today = date.today()
current_month = today.strftime("%Y-%m")
monthly_df = df[df["Date"].apply(lambda x: x.strftime("%Y-%m")) == current_month] if not df.empty else df

total_spent = df["Amount"].sum() if not df.empty else 0
monthly_spent = monthly_df["Amount"].sum() if not monthly_df.empty else 0
remaining_budget = max(monthly_budget - monthly_spent, 0)

k1, k2, k3 = st.columns(3)
k1.metric("💰 Total Spent", f"₹ {total_spent}")
k2.metric("📅 This Month", f"₹ {monthly_spent}")
k3.metric("🎯 Remaining Budget", f"₹ {remaining_budget}")

if monthly_budget > 0 and monthly_spent > monthly_budget:
    st.error("🚨 You have exceeded your monthly budget!")

# ---------------- FILTER ----------------
st.subheader("🔍 Filter & Analyze")
filter_category = st.selectbox("Category", ["All"] + sorted(df["Category"].unique().tolist()) if not df.empty else ["All"])
filter_month = st.selectbox("Month", ["All"] + sorted(df["Date"].astype(str).str[:7].unique().tolist()) if not df.empty else ["All"])

filtered_df = df.copy()
if filter_category != "All":
    filtered_df = filtered_df[filtered_df["Category"] == filter_category]
if filter_month != "All":
    filtered_df = filtered_df[filtered_df["Date"].astype(str).str.startswith(filter_month)]

st.dataframe(filtered_df, use_container_width=True)

# ---------------- CHARTS ----------------
if not filtered_df.empty:
    c5, c6 = st.columns(2)
    with c5:
        st.subheader("📊 Category-wise Spending")
        st.bar_chart(filtered_df.groupby("Category")["Amount"].sum())
    with c6:
        pie_data = filtered_df.groupby("Category")["Amount"].sum()
        fig, ax = plt.subplots()
        ax.pie(pie_data, labels=pie_data.index, autopct="%1.1f%%")
        ax.axis("equal")
        st.pyplot(fig)

# ---------------- TREND ----------------
st.subheader("📈 Spending Trend")
if not df.empty:
    df_trend = df.copy()
    df_trend["Date"] = pd.to_datetime(df_trend["Date"])
    trend_df = df_trend.groupby(df_trend["Date"].dt.to_period("D"))["Amount"].sum().reset_index()
    trend_df["Date"] = trend_df["Date"].astype(str)
    st.line_chart(trend_df.set_index("Date"))

# ---------------- EXPORT ----------------
st.subheader("⬇️ Export Report")
if not df.empty:
    buffer = BytesIO()
    export_df = df.copy()
    export_df["Date"] = pd.to_datetime(export_df["Date"]).dt.strftime("%Y-%m-%d")

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name="Expenses")
        ws = writer.sheets["Expenses"]
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = 18

    buffer.seek(0)
    st.download_button("⬇️ Download Excel", buffer, "expenses.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.markdown("---")
st.caption("Built with  using Python & Streamlit")
