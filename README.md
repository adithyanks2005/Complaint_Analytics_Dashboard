# 📊 Complaint Analytics Dashboard

A real-time public service complaint intelligence dashboard built with **Streamlit**, **Plotly**, and **Supabase/SQLite**. Visualize complaint trends, track resolution rates, and manage complaint records with an intuitive admin interface.

### 🌐 Live Demo
- **Production Dashboard**: [https://complaintanalyticsdashboard.streamlit.app/](https://complaintanalyticsdashboard.streamlit.app/)

---

## ✨ Features

- **KPI Cards** — Total complaints, closed count, open/pending, average closure time, and closure rate
- **Interactive Charts** — Monthly trend, category distribution (donut), complaints by area (colored bars), avg closure days
- **Smart Filters** — Filter by date range, area, category, and status with an Apply button
- **Complaint Submission** — Register new complaints directly from the dashboard
- **Admin Panel** — Secure 2-step login (username + password) to update or delete complaints
- **Auto Refresh** — Dashboard updates automatically after every admin or user action
- **CSV Export** — Download filtered complaint records as a CSV file
- **Shared Complaint Store** — Uses Supabase when configured so complaints are visible to every user, with SQLite as a local fallback
- **Professional UI** — Dark theme with gradient styling and smooth animations

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | [Streamlit](https://streamlit.io/) |
| Charts | [Plotly](https://plotly.com/python/) |
| Database | Supabase Postgres, SQLite fallback |
| Data Processing | [Pandas](https://pandas.pydata.org/) |
| Styling | Custom CSS + Outfit font |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/adithyanks2005/Complaint_Analytics_Dashboard.git
cd Complaint_Analytics_Dashboard

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the dashboard
streamlit run frontend/streamlit_app.py
```

The dashboard will open at `http://localhost:8501`

### Supabase Setup

1. Create a Supabase project.
2. Run [`schema/supabase.sql`](schema/supabase.sql) in the Supabase SQL editor.
3. Copy [`.env.example`](.env.example) to `.env`.
4. Fill in `SUPABASE_URL` and `SUPABASE_ANON_KEY`.
5. Restart Streamlit.

When those variables are present, all complaint reads, submissions, admin updates, and deletes use the shared Supabase `complaints` table. Without them, the app keeps using local SQLite.

---

## 📁 Project Structure

```
Complaint_Analytics_Dashboard/
├── frontend/
│   └── streamlit_app.py      # Main Streamlit application
├── data/
│   ├── complaints.db         # SQLite database
│   └── sample_complaints.csv # Seed data
├── schema/
│   └── supabase.sql          # Shared Supabase table and RLS policies
├── tests/
│   └── test_api.py           # API tests
├── setup.bat                 # Environment setup
├── requirements.txt          # Python dependencies
└── README.md                 # This file
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

## 👤 Author

**Adithyan KS**

- GitHub: [@adithyanks2005](https://github.com/adithyanks2005)

---

<div align="center">
  Built with ❤️ by Adithyan KS
</div>
