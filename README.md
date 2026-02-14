# 💸 Smart Expense Tracker (Streamlit App)

Smart Expense Manager (Python, Streamlit, SQLite, Plotly)
Built a full-stack expense tracking web app with multi-user authentication, budgeting alerts, recurring expenses, interactive dashboards, monthly analytics, AI-driven insights, and PDF/Excel export. Deployed on Streamlit Cloud with GitHub CI workflow.

## 🔗 Live Demo
👉 https://smartexpensetracker-bckewjy44xapdtsqws4kbi.streamlit.app/

## 📸 App Screenshot
(Screenshot%202026-02-12%20134330.png)

## 🧠 How It Works
- User enters expense details in the Streamlit UI  
- Data is saved in a CSV file  
- Pandas processes totals and monthly summaries  
- Matplotlib renders bar and pie charts  
- Deployed on Streamlit Cloud via GitHub integration


## 🚀 Features
- Add expenses with title, amount, date & category  
- View total spending (All time & Monthly)  
- Budget tracking & remaining budget  
- Category-wise analysis (Bar + Pie charts)  
- Filter by category and month  
- Data stored in CSV (can be extended to DB)  

## 🛠 Tech Stack
- Python  
- Streamlit  
- Pandas  
- Matplotlib  

## ▶️ Run Locally
```bash
pip install -r requirements.txt
streamlit run app.py
