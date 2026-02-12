import streamlit as st

# MUST be the first Streamlit command
st.set_page_config(
    page_title="Smart Expense Manager",
    page_icon="💸",
    layout="wide"
)

# Quick test to confirm UI loads
st.write("🔥 Streamlit UI is working")

# Your normal imports
import pandas as pd
from datetime import date
import os

st.title("💼 Smart Expense Manager")


FILE_NAME = "expenses.csv"
BUDGET_FILE = "budget.txt"

# ---------- Load Data ----------
if os.path.exists(FILE_NAME):
    df = pd.read_csv(FILE_NAME)
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
else:
    df = pd.DataFrame(columns=["Name", "Amount", "Date", "Category"])

if os.path.exists(BUDGET_FILE):
    with open(BUDGET_FILE, "r") as f:
        monthly_budget = float(f.read())
else:
    monthly_budget = 0.0

# ---------- Sidebar ----------
st.sidebar.header("⚙️ Settings")
new_budget = st.sidebar.number_input("Set Monthly Budget (₹)", min_value=0.0, value=monthly_budget, step=500.0)

if st.sidebar.button("Save Budget"):
    with open(BUDGET_FILE, "w") as f:
        f.write(str(new_budget))
    st.sidebar.success("Budget saved!")

st.sidebar.markdown("---")
st.sidebar.info("📌 Demo project for interviews")

# ---------- Add Expense ----------
st.subheader("➕ Add Expense")

c1, c2, c3, c4 = st.columns(4)

with c1:
    name = st.text_input("Title")
with c2:
    amount = st.number_input("Amount (₹)", min_value=0.0, step=1.0)
with c3:
    exp_date = st.date_input("Date", value=date.today())
with c4:
    category = st.selectbox("Category", ["Food", "Travel", "Shopping", "Bills", "Entertainment", "Health", "Other"])

if st.button("Add Expense", use_container_width=True):
    if name and amount > 0:
        new_row = pd.DataFrame([{
            "Name": name,
            "Amount": amount,
            "Date": exp_date,
            "Category": category
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(FILE_NAME, index=False)
        st.success("Expense added!")
        st.rerun()
    else:
        st.error("Please enter valid details")

st.divider()

# ---------- Dashboard ----------
today = date.today()
current_month = today.strftime("%Y-%m")

monthly_df = df[df["Date"].apply(lambda x: x.strftime("%Y-%m")) == current_month]

total_spent = df["Amount"].sum() if not df.empty else 0
monthly_spent = monthly_df["Amount"].sum() if not monthly_df.empty else 0
remaining_budget = max(monthly_budget - monthly_spent, 0)

k1, k2, k3 = st.columns(3)
k1.metric("💰 Total Spent (All Time)", f"₹ {total_spent}")
k2.metric("📅 This Month Spent", f"₹ {monthly_spent}")
k3.metric("🎯 Remaining Budget", f"₹ {remaining_budget}")

if monthly_budget > 0 and monthly_spent > monthly_budget:
    st.error("🚨 You have exceeded your monthly budget!")

st.divider()

# ---------- Filters ----------
st.subheader("🔍 Filter & Analyze")

f1, f2 = st.columns(2)

with f1:
    filter_category = st.selectbox(
        "Category",
        ["All"] + sorted(df["Category"].unique().tolist()) if not df.empty else ["All"]
    )

with f2:
    filter_month = st.selectbox(
        "Month",
        ["All"] + sorted(list(set([d.strftime("%Y-%m") for d in df["Date"]]))) if not df.empty else ["All"]
    )

filtered_df = df.copy()

if filter_category != "All":
    filtered_df = filtered_df[filtered_df["Category"] == filter_category]

if filter_month != "All":
    filtered_df = filtered_df[filtered_df["Date"].apply(lambda x: x.strftime("%Y-%m")) == filter_month]

st.dataframe(filtered_df, use_container_width=True)

# ---------- Charts ----------
if not filtered_df.empty:
    c5, c6 = st.columns(2)

    with c5:
        st.subheader("📊 Category-wise Spending (Bar)")
        st.bar_chart(filtered_df.groupby("Category")["Amount"].sum())

    with c6:
        st.subheader("🥧 Category-wise Spending (Pie)")
        pie_data = filtered_df.groupby("Category")["Amount"].sum()
        st.pyplot(pie_data.plot.pie(autopct="%1.1f%%").figure)

st.divider()

# ---------- Delete ----------
st.subheader("🗑️ Manage Expenses")

if not df.empty:
    idx = st.selectbox(
        "Select expense to delete",
        df.index,
        format_func=lambda i: f"{df.loc[i,'Name']} - ₹{df.loc[i,'Amount']} ({df.loc[i,'Date']})"
    )

    if st.button("Delete Selected", use_container_width=True):
        df = df.drop(idx).reset_index(drop=True)
        df.to_csv(FILE_NAME, index=False)
        st.success("Deleted successfully!")
        st.rerun()

# ---------- Export ----------
st.subheader("⬇️ Export Report")
if not df.empty:
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, "expenses_report.csv", "text/csv")

# ---------- Footer ----------
st.markdown("---")
st.caption("Built with ❤️ using Python & Streamlit")
