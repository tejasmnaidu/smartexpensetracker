import plotly.express as px
import matplotlib
matplotlib.use("Agg")

import streamlit as st
import pandas as pd
from datetime import date
from io import BytesIO
import sqlite3
import hashlib
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer


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

c.execute("""
CREATE TABLE IF NOT EXISTS category_budgets (
    username TEXT,
    category TEXT,
    budget REAL,
    PRIMARY KEY (username, category)
)
""")
conn.commit()

# --------- MIGRATION: add recurring column if missing ---------
try:
    c.execute("ALTER TABLE expenses ADD COLUMN recurring INTEGER DEFAULT 0")
    conn.commit()
except:
    pass

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

# ---------------- SIDEBAR ----------------
st.sidebar.success(f"Logged in as {st.session_state.username}")

# Recurring
st.sidebar.markdown("---")
st.sidebar.subheader("🔁 Recurring Expenses")
if st.sidebar.button("Carry recurring expenses to this month"):
    c.execute("SELECT name, amount, category FROM expenses WHERE username=? AND recurring=1", (st.session_state.username,))
    rows = c.fetchall()
    for name, amount, category in rows:
        c.execute("INSERT INTO expenses (username, name, amount, date, category, recurring) VALUES (?, ?, ?, ?, ?, 1)",
                  (st.session_state.username, name, amount, date.today().strftime("%Y-%m-%d"), category))
    conn.commit()
    st.sidebar.success("Recurring expenses added!")
    st.rerun()

# Budget
c.execute("SELECT budget FROM users WHERE username=?", (st.session_state.username,))
monthly_budget = float(c.fetchone()[0])
st.sidebar.header("🎯 Monthly Budget")
new_budget = st.sidebar.number_input("Set Monthly Budget (₹)", 0.0, value=monthly_budget, step=500.0)
if st.sidebar.button("Save Monthly Budget"):
    c.execute("UPDATE users SET budget=? WHERE username=?", (new_budget, st.session_state.username))
    conn.commit()
    st.sidebar.success("Saved!")

# Category Budgets
st.sidebar.markdown("---")
st.sidebar.subheader("📁 Category Budgets")
categories = ["Food","Travel","Shopping","Bills","Entertainment","Health","Other"]
cat_budgets = {}
for cat in categories:
    c.execute("SELECT budget FROM category_budgets WHERE username=? AND category=?", (st.session_state.username, cat))
    row = c.fetchone()
    cat_budgets[cat] = float(row[0]) if row else 0.0

for cat in categories:
    cat_budgets[cat] = st.sidebar.number_input(f"{cat} Budget (₹)", 0.0, value=cat_budgets[cat], step=500.0)

if st.sidebar.button("Save Category Budgets"):
    for cat, bud in cat_budgets.items():
        c.execute("""
            INSERT INTO category_budgets (username, category, budget)
            VALUES (?, ?, ?)
            ON CONFLICT(username, category) DO UPDATE SET budget=excluded.budget
        """, (st.session_state.username, cat, bud))
    conn.commit()
    st.sidebar.success("Category budgets saved!")

if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

# ---------------- LOAD DATA ----------------
c.execute("SELECT name, amount, date, category, recurring FROM expenses WHERE username=?", (st.session_state.username,))
rows = c.fetchall()
df = pd.DataFrame(rows, columns=["Name","Amount","Date","Category","Recurring"])
if not df.empty:
    df["Date"] = pd.to_datetime(df["Date"]).dt.date

# ---------------- ADD EXPENSE ----------------
st.subheader("➕ Add Expense")
c1,c2,c3,c4 = st.columns(4)
with c1: name = st.text_input("Title")
with c2: amount = st.number_input("Amount (₹)", 0.0, step=1.0)
with c3: exp_date = st.date_input("Date", value=date.today())
with c4: category = st.selectbox("Category", categories)
is_recurring = st.checkbox("🔁 Recurring monthly expense?")
if st.button("Add Expense", use_container_width=True):
    if name and amount > 0:
        c.execute("INSERT INTO expenses VALUES (NULL,?,?,?,?,?,?)",
                  (st.session_state.username, name, amount, str(exp_date), category, int(is_recurring)))
        conn.commit()
        st.success("Added!")
        st.rerun()

st.divider()

# ---------------- DASHBOARD ----------------
today = date.today()
current_month = today.strftime("%Y-%m")
monthly_df = df[df["Date"].apply(lambda x: x.strftime("%Y-%m")) == current_month] if not df.empty else df

total_spent = df["Amount"].sum() if not df.empty else 0
monthly_spent = monthly_df["Amount"].sum() if not monthly_df.empty else 0
remaining_budget = max(monthly_budget - monthly_spent, 0)

k1,k2,k3 = st.columns(3)
k1.metric("💰 Total Spent", f"₹ {total_spent:.0f}")
k2.metric("📅 This Month", f"₹ {monthly_spent:.0f}")
k3.metric("🎯 Remaining Budget", f"₹ {remaining_budget:.0f}")

# ---------------- BUDGET ALERTS ----------------
if monthly_budget > 0:
    pct = (monthly_spent / monthly_budget) * 100
    if pct >= 100:
        st.error("🚨 You exceeded your monthly budget!")
    elif pct >= 80:
        st.warning(f"🔔 {pct:.1f}% of budget used.")
    else:
        st.info(f"ℹ️ {pct:.1f}% of budget used.")

# ---------------- FILTER ----------------
st.subheader("🔍 Filter & Analyze")
search_query = st.text_input("Search by name")
filter_category = st.selectbox("Category", ["All"] + categories)
filter_month = st.selectbox("Month", ["All"] + sorted(df["Date"].astype(str).str[:7].unique().tolist()) if not df.empty else ["All"])

filtered_df = df.copy()
if filter_category != "All":
    filtered_df = filtered_df[filtered_df["Category"] == filter_category]
if filter_month != "All":
    filtered_df = filtered_df[filtered_df["Date"].astype(str).str.startswith(filter_month)]
if search_query:
    filtered_df = filtered_df[filtered_df["Name"].str.contains(search_query, case=False, na=False)]

st.dataframe(filtered_df, use_container_width=True)

# ---------------- COLORFUL CHARTS ----------------
if not filtered_df.empty:
    c5,c6 = st.columns(2)
    with c5:
        bar_df = filtered_df.groupby("Category")["Amount"].sum().reset_index()
        st.plotly_chart(px.bar(bar_df, x="Category", y="Amount", color="Category",
                               color_discrete_sequence=px.colors.qualitative.Bold,
                               title="Category Spending"), use_container_width=True)
    with c6:
        pie_df = filtered_df.groupby("Category")["Amount"].sum().reset_index()
        st.plotly_chart(px.pie(pie_df, names="Category", values="Amount", hole=0.4,
                               color_discrete_sequence=px.colors.qualitative.Prism,
                               title="Spending Distribution"), use_container_width=True)

# ---------------- TREND ----------------
st.subheader("📈 Spending Trend")
if not df.empty:
    df_trend = df.copy()
    df_trend["Date"] = pd.to_datetime(df_trend["Date"])
    trend_df = df_trend.groupby(df_trend["Date"].dt.to_period("D"))["Amount"].sum().reset_index()
    trend_df["Date"] = trend_df["Date"].astype(str)
    st.plotly_chart(px.line(trend_df, x="Date", y="Amount", markers=True), use_container_width=True)

# ---------------- MONTHLY COMPARISON + DIFFERENCE ----------------
st.subheader("📊 Monthly Comparison Dashboard")
if not df.empty:
    df_monthly = df.copy()
    df_monthly["Month"] = pd.to_datetime(df_monthly["Date"]).dt.to_period("M").astype(str)
    monthly_summary = df_monthly.groupby("Month")["Amount"].sum().reset_index()

    st.plotly_chart(px.bar(monthly_summary, x="Month", y="Amount", color="Month",
                           color_discrete_sequence=px.colors.qualitative.Set2,
                           title="Monthly Spending"), use_container_width=True)

    st.plotly_chart(px.line(monthly_summary, x="Month", y="Amount", markers=True,
                            title="Monthly Trend"), use_container_width=True)

    st.markdown("### 🔍 Compare Two Months")
    if len(monthly_summary) >= 2:
        m1, m2 = st.columns(2)
        with m1:
            month_1 = st.selectbox("Month 1", monthly_summary["Month"])
        with m2:
            month_2 = st.selectbox("Month 2", monthly_summary["Month"], index=len(monthly_summary)-1)

        spend_1 = monthly_summary[monthly_summary["Month"] == month_1]["Amount"].values[0]
        spend_2 = monthly_summary[monthly_summary["Month"] == month_2]["Amount"].values[0]

        st.metric(f"Difference ({month_2} vs {month_1})", f"₹ {spend_2:.0f}", f"₹ {spend_2 - spend_1:.0f}")

# ---------------- SMART INSIGHTS (FULL) ----------------
st.subheader("🧠 Smart Spending Insights")

if not df.empty:
    df_insight = df.copy()
    df_insight["Month"] = pd.to_datetime(df_insight["Date"]).dt.to_period("M").astype(str)

    current_month = date.today().strftime("%Y-%m")
    prev_month = (pd.Period(current_month) - 1).strftime("%Y-%m")

    current_df = df_insight[df_insight["Month"] == current_month]
    prev_df = df_insight[df_insight["Month"] == prev_month]

    insights = []

    # 1️⃣ Highest spending category this month
    if not current_df.empty:
        top_cat = current_df.groupby("Category")["Amount"].sum().idxmax()
        top_amt = current_df.groupby("Category")["Amount"].sum().max()
        insights.append(f"📌 Your highest spending category this month is **{top_cat} (₹{top_amt:.0f})**.")

    # 2️⃣ Compare with last month (with %)
    if not current_df.empty and not prev_df.empty:
        curr_total = current_df["Amount"].sum()
        prev_total = prev_df["Amount"].sum()
        diff = curr_total - prev_total
        pct = (diff / prev_total) * 100 if prev_total > 0 else 0

        if diff > 0:
            insights.append(f"📈 You spent **₹{diff:.0f} more** this month compared to last month (+{pct:.1f}%).")
        elif diff < 0:
            insights.append(f"📉 You spent **₹{abs(diff):.0f} less** this month compared to last month ({pct:.1f}%).")
        else:
            insights.append("➖ Your spending is the **same as last month**.")

    # 3️⃣ Budget insight (mirrors budget alerts but in AI text form)
    if monthly_budget > 0:
        if monthly_spent > monthly_budget:
            insights.append("🚨 You have **exceeded your monthly budget**. Consider cutting down expenses.")
        else:
            remaining = monthly_budget - monthly_spent
            insights.append(f"✅ You are within budget. You can still spend **₹{remaining:.0f}** this month.")

    # 4️⃣ Trend insight (last 3 months)
    if len(df_insight["Month"].unique()) >= 3:
        monthly_summary = df_insight.groupby("Month")["Amount"].sum().reset_index()
        last_3 = monthly_summary.tail(3)["Amount"].values

        if last_3[2] > last_3[1] > last_3[0]:
            insights.append("📊 Your spending is **increasing over the last 3 months**.")
        elif last_3[2] < last_3[1] < last_3[0]:
            insights.append("📉 Your spending is **decreasing over the last 3 months**.")
        else:
            insights.append("📊 Your spending is **fluctuating over recent months**.")

    for ins in insights:
        st.info(ins)
else:
    st.info("Add expenses to see smart insights.")


# ---------------- EXPORT ----------------
st.subheader("⬇️ Export Report")

if not df.empty:
    col1, col2 = st.columns(2)

    # ---- Excel Export (kept) ----
    with col1:
        buffer = BytesIO()
        export_df = df.copy()
        export_df["Date"] = pd.to_datetime(export_df["Date"]).dt.strftime("%Y-%m-%d")
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            export_df.to_excel(writer, index=False)
        buffer.seek(0)
        st.download_button("⬇️ Download Excel", buffer, "expenses.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ---- PDF Export (new) ----
    with col2:
        month_options = ["All"] + sorted(df["Date"].astype(str).str[:7].unique().tolist())
        pdf_month = st.selectbox("Select Month for PDF", month_options)

        if st.button("📄 Generate PDF"):
            if pdf_month == "All":
                pdf_df = df.copy()
                title = "Expense Report (All Time)"
                filename = "expenses_report.pdf"
            else:
                pdf_df = df[df["Date"].astype(str).str.startswith(pdf_month)]
                title = f"Expense Report - {pdf_month}"
                filename = f"expenses_{pdf_month}.pdf"

            pdf_df = pdf_df.copy()
            pdf_df["Date"] = pd.to_datetime(pdf_df["Date"]).dt.strftime("%Y-%m-%d")

            pdf_buffer = BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            elements = []

            elements.append(Paragraph(title, styles["Title"]))
            elements.append(Spacer(1, 12))

            total_amt = pdf_df["Amount"].sum() if not pdf_df.empty else 0
            elements.append(Paragraph(f"<b>Total Spent:</b> ₹ {total_amt:.0f}", styles["Normal"]))
            elements.append(Spacer(1, 12))

            table_data = [pdf_df.columns.tolist()] + pdf_df.values.tolist()
            table = Table(table_data, repeatRows=1)

            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ]))

            elements.append(table)
            doc.build(elements)
            pdf_buffer.seek(0)

            st.download_button("⬇️ Download PDF", pdf_buffer, filename, "application/pdf")
            
st.markdown("---")
st.caption("Built using Python & Streamlit")
