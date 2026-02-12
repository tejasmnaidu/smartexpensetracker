
import streamlit as st
import pandas as pd
import io
from datetime import datetime

# ---------------- Page Config ----------------
st.set_page_config(page_title="Smart Expense Manager", layout="wide")

st.markdown("🔥 Streamlit UI is working")
st.title("💼 Smart Expense Manager")

# ---------------- Expenses: Start EMPTY for demo ----------------
if "expenses_df" not in st.session_state:
    st.session_state.expenses_df = pd.DataFrame(
        columns=["Title", "Amount", "Date", "Category"]
    )

df = st.session_state.expenses_df

# ---------------- Add Expense ----------------
st.subheader("➕ Add Expense")

col1, col2, col3, col4 = st.columns(4)

with col1:
    title = st.text_input("Title")
with col2:
    amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0)
with col3:
    date = st.date_input("Date", value=datetime.today())
with col4:
    category = st.selectbox("Category", ["Food", "Shopping", "Bills", "Travel", "Other"])

if st.button("Add Expense"):
    if title.strip() == "" or amount <= 0:
        st.warning("Please enter valid title and amount.")
    else:
        new_row = {
            "Title": title,
            "Amount": float(amount),
            "Date": pd.to_datetime(date),
            "Category": category
        }
        st.session_state.expenses_df = pd.concat(
            [st.session_state.expenses_df, pd.DataFrame([new_row])],
            ignore_index=True
        )
        st.success("Expense added successfully!")

df = st.session_state.expenses_df

# ---------------- Budget (Dynamic) ----------------
st.sidebar.subheader("💰 Monthly Budget")

if "budget" not in st.session_state:
    st.session_state.budget = 0.0

new_budget = st.sidebar.number_input("Set Budget (₹)", min_value=0.0, step=500.0)
if st.sidebar.button("Save Budget"):
    st.session_state.budget = new_budget

budget = st.session_state.budget

# ---------------- Metrics ----------------
st.markdown("---")

total_spent = df["Amount"].sum() if not df.empty else 0.0

this_month = pd.Timestamp.today().strftime("%Y-%m")
if not df.empty:
    df["month"] = df["Date"].dt.strftime("%Y-%m")
    month_spent = df[df["month"] == this_month]["Amount"].sum()
else:
    month_spent = 0.0

remaining = budget - total_spent if budget > 0 else 0

c1, c2, c3 = st.columns(3)
c1.metric("🪙 Total Spent (All Time)", f"₹ {total_spent:,.1f}")
c2.metric("📅 This Month Spent", f"₹ {month_spent:,.1f}")
c3.metric("💸 Remaining Budget", f"₹ {remaining:,.0f}")

# ---------------- Filter & Analyze ----------------
st.markdown("---")
st.subheader("🔎 Filter & Analyze")

if df.empty:
    st.info("No expenses yet. Add your first expense above 👆")
else:
    f1, f2 = st.columns(2)

    with f1:
        category_filter = st.selectbox(
            "Category",
            ["All"] + sorted(df["Category"].unique().tolist())
        )

    with f2:
        month_filter = st.selectbox(
            "Month",
            ["All"] + sorted(df["month"].unique().tolist())
        )

    filtered_df = df.copy()

    if category_filter != "All":
        filtered_df = filtered_df[filtered_df["Category"] == category_filter]

    if month_filter != "All":
        filtered_df = filtered_df[filtered_df["month"] == month_filter]

    st.dataframe(filtered_df, use_container_width=True)

# ---------------- Export ----------------
st.markdown("---")
st.subheader("📤 Export Report")

if df.empty:
    st.info("No expenses to export yet.")
else:
    export_months = ["All"] + sorted(df["month"].unique().tolist())
    export_month = st.selectbox("Select Month for Excel", export_months)

    buffer = io.BytesIO()

    if export_month == "All":
        export_df = df.copy()
        filename = "expenses_all.xlsx"
    else:
        export_df = df[df["month"] == export_month]
        filename = f"expenses_{export_month}.xlsx"

    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        export_df.to_excel(writer, index=False, sheet_name="Expenses")

    st.download_button(
        label="⬇ Download Excel",
        data=buffer.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ---------------- Footer ----------------
st.markdown("---")
st.caption("Built using Python & Streamlit")
