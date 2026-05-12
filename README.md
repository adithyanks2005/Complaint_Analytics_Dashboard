# 📊 Complaint Analytics Dashboard

A real-time public service complaint intelligence dashboard built with **Streamlit**, **Plotly**, and **SQLite**. Visualize complaint trends, track resolution rates, and manage records — all without a backend server.

---

## ✨ Features

- **KPI Cards** — Total complaints, closed count, open/pending, average closure time, and closure rate
- **Interactive Charts** — Monthly trend, category distribution (donut), complaints by area (colored bars), avg closure days
- **Smart Filters** — Filter by date range, area, category, and status with an Apply button
- **Complaint Submission** — Register new complaints directly from the dashboard
- **Admin Panel** — Secure 2-step login (username + password) to update or delete complaints
- **Auto Refresh** — Dashboard updates automatically after every admin or user action
- **CSV Export** — Download filtered complaint records as a CSV file
- **Direct SQLite** — No backend API required; reads and writes directly to the database

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | [Streamlit](https://streamlit.io/) |
| Charts | [Plotly](https://plotly.com/python/) |
| Database | SQLite (via Python `sqlite3`) |
| Data | [Pandas](https://pandas.pydata.org/) |
| Styling | Custom CSS + Inter font |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/adithyanks2005/Complaint_Analytics_Dashboard.git
cd Complaint_Analytics_Dashboard

# 2. Run the setup script (creates venv and installs dependencies)
setup.bat

# 3. Launch the dashboard
run_dashboard.bat
```

The dashboard will open at `http://localhost:8501`

---

## 📁 Project Structure

```
Complaint_Analytics_Dashboard/
├── frontend/
│   └── streamlit_app.py      # Main Streamlit application
├── backend/
│   ├── main.py               # FastAPI backend (optional)
│   ├── analytics.py          # Analytics logic
│   └── database.py           # Database helpers
├── data/
│   └── sample_complaints.csv # Seed data
├── tests/
│   └── test_api.py           # API tests
├── run_dashboard.bat         # Launch dashboard
├── run_backend.bat           # Launch backend (optional)
├── setup.bat                 # Environment setup
└── requirements.txt          # Python dependencies
```

---

## 🔐 Admin Access

The admin panel allows updating and deleting complaint records.

| Field | Value |
|-------|-------|
| Username | `admin` |
| Password | `admin123` |

> To change credentials, update `ADMIN_USERNAME` and `ADMIN_PASSWORD` in `frontend/streamlit_app.py`.

---

## 📸 Dashboard Preview

| Section | Description |
|---------|-------------|
| KPI Cards | 5 metric cards at the top |
| Overview Tab | 4 interactive Plotly charts |
| Records Tab | Filterable data table with CSV export |
| Submit Tab | Form to register new complaints |
| Admin Panel | Update/delete complaints (admin only) |

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

---

## 👤 Author

**Adithyan KS**

- GitHub: [@adithyanks2005](https://github.com/adithyanks2005)

---

<div align="center">
  Built with ❤️ by Adithyan KS
</div>
