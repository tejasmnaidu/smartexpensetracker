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

def reset_password_without_old(username, new_password):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=?", (username,))
    if c.fetchone() is None:
        conn.close()
        return False
    c.execute("UPDATE users SET password=? WHERE username=?", (hash_password(new_password), username))
    conn.commit()
    conn.close()
    return True

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
    category TEXT,
    recurring INTEGER DEFAULT 0
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

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# ---------------- AUTH UI ----------------
st.title("💼 Smart Expense Manager")
menu = ["Login", "Register", "Reset Password", "Forgot Password"]
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

    elif choice == "Forgot Password":
        st.subheader("🆘 Forgot Password")
        u = st.text_input("Username")
        new_pw = st.text_input("New Password", type="password")
        confirm_pw = st.text_input("Confirm New Password", type="password")
        security_key = st.text_input("Security Key (demo: admin123)", type="password")

        if st.button("Reset Without Old Password"):
            if security_key != "admin123":
                st.error("Invalid security key.")
            elif new_pw != confirm_pw:
                st.error("Passwords do not match.")
            else:
                ok = reset_password_without_old(u, new_pw)
                if ok:
                    st.success("Password reset successfully! Login now.")
                else:
                    st.error("User not found.")

    st.stop()

# ---------------- SIDEBAR ----------------
st.sidebar.success(f"Logged in as {st.session_state.username}")

# Budget
c.execute("SELECT budget FROM users WHERE username=?", (st.session_state.username,))
monthly_budget = float(c.fetchone()[0])

st.sidebar.header("🎯 Monthly Budget")
new_budget = st.sidebar.number_input("Set Monthly Budget (₹)", 0.0, value=monthly_budget, step=500.0)
if st.sidebar.button("Save Monthly Budget"):
    c.execute("UPDATE users SET budget=? WHERE username=?", (new_budget, st.session_state.username))
    conn.commit()
    st.sidebar.success("Saved!")

categories = ["Food","Travel","Shopping","Bills","Entertainment","Health","Other"]

st.sidebar.markdown("---")
st.sidebar.subheader("📁 Category Budgets")
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
c.execute("SELECT id, name, amount, date, category, recurring FROM expenses WHERE username=?", (st.session_state.username,))
rows = c.fetchall()
df = pd.DataFrame(rows, columns=["ID","Name","Amount","Date","Category","Recurring"])
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
monthly_df = df[df["Date"].astype(str).str.startswith(current_month)] if not df.empty else df

total_spent = df["Amount"].sum() if not df.empty else 0
monthly_spent = monthly_df["Amount"].sum() if not monthly_df.empty else 0
remaining_budget = max(monthly_budget - monthly_spent, 0)

k1,k2,k3 = st.columns(3)
k1.metric("💰 Total Spent", f"₹ {total_spent:.0f}")
k2.metric("📅 This Month", f"₹ {monthly_spent:.0f}")
k3.metric("🎯 Remaining Budget", f"₹ {remaining_budget:.0f}")

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

# ---------------- EDIT EXPENSE ----------------
st.subheader("✏️ Edit Expense")
if not df.empty:
    edit_id = st.selectbox("Select expense", df["ID"], format_func=lambda i: f"{df[df['ID']==i]['Name'].values[0]}")
    row = df[df["ID"] == edit_id].iloc[0]

    c1,c2,c3,c4 = st.columns(4)
    with c1: new_name = st.text_input("Edit Title", value=row["Name"])
    with c2: new_amount = st.number_input("Edit Amount (₹)", 0.0, value=float(row["Amount"]))
    with c3: new_date = st.date_input("Edit Date", value=row["Date"])
    with c4: new_category = st.selectbox("Edit Category", categories, index=categories.index(row["Category"]))

    if st.button("Save Changes", use_container_width=True):
        c.execute("""UPDATE expenses SET name=?, amount=?, date=?, category=? WHERE id=?""",
                  (new_name, new_amount, str(new_date), new_category, edit_id))
        conn.commit()
        st.success("Updated!")
        st.rerun()

# ---------------- COLORFUL CHARTS ----------------
if not filtered_df.empty:
    c5,c6 = st.columns(2)
    with c5:
        bar_df = filtered_df.groupby("Category")["Amount"].sum().reset_index()
        st.plotly_chart(px.bar(bar_df, x="Category", y="Amount", color="Category",
                               color_discrete_sequence=px.colors.qualitative.Bold), use_container_width=True)
    with c6:
        pie_df = filtered_df.groupby("Category")["Amount"].sum().reset_index()
        st.plotly_chart(px.pie(pie_df, names="Category", values="Amount", hole=0.4,
                               color_discrete_sequence=px.colors.qualitative.Prism), use_container_width=True)

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
    df_m = df.copy()
    df_m["Month"] = pd.to_datetime(df_m["Date"]).dt.to_period("M").astype(str)
    summary = df_m.groupby("Month")["Amount"].sum().reset_index()

    st.plotly_chart(px.bar(summary, x="Month", y="Amount", color="Month",
                           color_discrete_sequence=px.colors.qualitative.Set2), use_container_width=True)

    st.plotly_chart(px.line(summary, x="Month", y="Amount", markers=True), use_container_width=True)

    if len(summary) >= 2:
        m1, m2 = st.columns(2)
        with m1:
            month_1 = st.selectbox("Month 1", summary["Month"])
        with m2:
            month_2 = st.selectbox("Month 2", summary["Month"], index=len(summary)-1)

        s1 = summary[summary["Month"] == month_1]["Amount"].values[0]
        s2 = summary[summary["Month"] == month_2]["Amount"].values[0]
        st.metric("Difference", f"₹ {s2:.0f}", f"₹ {s2 - s1:.0f}")

# ---------------- AI ASSISTANT ----------------
st.subheader("🤖 AI Assistant – Smart Money Coach")

if not df.empty:
    df_ai = df.copy()
    df_ai["Month"] = pd.to_datetime(df_ai["Date"]).dt.to_period("M").astype(str)

    current_month = date.today().strftime("%Y-%m")
    prev_month = (pd.Period(current_month) - 1).strftime("%Y-%m")

    current_df = df_ai[df_ai["Month"] == current_month]
    prev_df = df_ai[df_ai["Month"] == prev_month]

    messages = []

    if not current_df.empty:
        top_cat = current_df.groupby("Category")["Amount"].sum().idxmax()
        top_amt = current_df.groupby("Category")["Amount"].sum().max()
        messages.append(f"🧠 You spent the most on **{top_cat} (₹{top_amt:.0f})** this month.")

    if not current_df.empty and not prev_df.empty:
        curr_total = current_df["Amount"].sum()
        prev_total = prev_df["Amount"].sum()
        diff = curr_total - prev_total
        pct = (diff / prev_total) * 100 if prev_total > 0 else 0

        if diff > 0:
            messages.append(f"📈 Your spending increased by **₹{diff:.0f} ({pct:.1f}%)** compared to last month.")
        elif diff < 0:
            messages.append(f"📉 Nice! You spent **₹{abs(diff):.0f} ({abs(pct):.1f}%) less** than last month.")
        else:
            messages.append("➖ Your spending is the same as last month.")

    if monthly_budget > 0:
        if monthly_spent > monthly_budget:
            messages.append("🚨 You crossed your budget. Try cutting discretionary spending.")
        else:
            remaining = monthly_budget - monthly_spent
            messages.append(f"🎯 You can still spend ₹{remaining:.0f} this month within budget.")

    if len(df_ai["Month"].unique()) >= 3:
        ms = df_ai.groupby("Month")["Amount"].sum().reset_index()
        last3 = ms.tail(3)["Amount"].values
        if last3[2] > last3[1] > last3[0]:
            messages.append("📊 Spending is increasing for 3 months.")
        elif last3[2] < last3[1] < last3[0]:
            messages.append("📉 Spending is decreasing for 3 months.")
        else:
            messages.append("📊 Spending is fluctuating.")

    for m in messages:
        st.info(m)
else:
    st.info("Add expenses to see AI insights.")

# ---------------- SMART INSIGHTS (FULL) ----------------
st.subheader("🧠 Smart Spending Insights")

if not df.empty:
    df_ins = df.copy()
    df_ins["Month"] = pd.to_datetime(df_ins["Date"]).dt.to_period("M").astype(str)
    current_month = date.today().strftime("%Y-%m")
    prev_month = (pd.Period(current_month) - 1).strftime("%Y-%m")

    cur = df_ins[df_ins["Month"] == current_month]
    prev = df_ins[df_ins["Month"] == prev_month]

    insights = []

    if not cur.empty:
        top_cat = cur.groupby("Category")["Amount"].sum().idxmax()
        insights.append(f"📌 Highest spend this month: **{top_cat}**")

    if not cur.empty and not prev.empty:
        diff = cur["Amount"].sum() - prev["Amount"].sum()
        insights.append(f"📊 Month difference: ₹{diff:.0f}")

    for ins in insights:
        st.info(ins)
else:
    st.info("Add expenses to see insights.")

# ---------------- EXPORT ----------------
st.subheader("⬇️ Export Report")

if not df.empty:
    col1,col2 = st.columns(2)

    with col1:
        buf = BytesIO()
        out_df = df.copy()
        out_df["Date"] = pd.to_datetime(out_df["Date"]).dt.strftime("%Y-%m-%d")
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            out_df.to_excel(w, index=False)
        buf.seek(0)
        st.download_button("⬇️ Download Excel", buf, "expenses.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with col2:
        if st.button("📄 Generate PDF"):
            pdf_buffer = BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            elements = [Paragraph("Expense Report", styles["Title"]), Spacer(1, 12)]

            table_data = [out_df.columns.tolist()] + out_df.values.tolist()
            table = Table(table_data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
            ]))
            elements.append(table)
            doc.build(elements)
            pdf_buffer.seek(0)
            st.download_button("⬇️ Download PDF", pdf_buffer, "expenses.pdf", "application/pdf")

st.markdown("---")
st.caption("Built using Python & Streamlit")
