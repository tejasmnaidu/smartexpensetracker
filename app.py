import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
from datetime import datetime

# ---------------- Page Config ----------------
st.set_page_config(page_title="Smart Expense Manager", layout="wide")

st.title("💼 Smart Expense Manager")

# ---------------- Expenses: Start EMPTY (no fixed CSV) ----------------
if "expenses_df" not in st.session_state:
    st.session_state.expenses_df = pd.DataFrame(
        columns=["Title", "Amount", "Date", "Category"]
    )

df = st.session_state.expenses_df

# ---------------- Add Expense ----------------
st.subheader("➕ Add Expense")
c1, c2, c3, c4 = st.columns(4)

with c1:
    title = st.text_input("Title")
with c2:
    amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0)
with c3:
    date = st.date_input("Date", value=datetime.today())
with c4:
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
        df = st.session_state.expenses_df
        st.success("Expense added successfully!")

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

if not df.empty:
    df["month"] = df["Date"].dt.strftime("%Y-%m")
    this_month = pd.Timestamp.today().strftime("%Y-%m")
    month_spent = df[df["month"] == this_month]["Amount"].sum()
else:
    month_spent = 0.0

remaining = budget - total_spent if budget > 0 else 0

m1, m2, m3 = st.columns(3)
m1.metric("🪙 Total Spent (All Time)", f"₹ {total_spent:,.1f}")
m2.metric("📅 This Month Spent", f"₹ {month_spent:,.1f}")
m3.metric("💸 Remaining Budget", f"₹ {remaining:,.0f}")

if budget > 0:
    st.progress(min(total_spent / budget, 1.0))

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

    # ---------------- Graphs ----------------
    st.subheader("📊 Spending by Category (Bar Chart)")
    cat_sum = filtered_df.groupby("Category")["Amount"].sum()

    fig, ax = plt.subplots()
    cat_sum.plot(kind="bar", ax=ax)
    ax.set_xlabel("Category")
    ax.set_ylabel("Amount (₹)")
    st.pyplot(fig)

    # -------- Pie Chart --------
    st.subheader("🥧 Category-wise Spending (Pie Chart)")
    fig2, ax2 = plt.subplots()
    ax2.pie(cat_sum, labels=cat_sum.index, autopct="%1.1f%%", startangle=90)
    ax2.axis("equal")
    st.pyplot(fig2)

    # -------- Line Chart: Daily Trend --------
    st.subheader("📈 Daily Spending Trend")
    daily_sum = (
        filtered_df
        .groupby(filtered_df["Date"].dt.date)["Amount"]
        .sum()
        .reset_index()
    )

    fig3, ax3 = plt.subplots()
    ax3.plot(daily_sum["Date"], daily_sum["Amount"], marker="o")
    ax3.set_xlabel("Date")
    ax3.set_ylabel("Amount (₹)")
    plt.xticks(rotation=45)
    st.pyplot(fig3)

# ---------------- Export (Excel) ----------------
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

