"""
Complaint Analytics Dashboard - Streamlit Frontend
Talks directly to the SQLite database (no backend required)
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DB_PATH  = BASE_DIR / "data" / "complaints.db"
CSV_PATH = BASE_DIR / "data" / "sample_complaints.csv"

# REPLACE THIS WITH YOUR ACTUAL VERCEL DOMAIN (e.g., https://complaint-analytics-dashboard.vercel.app)
API_URL = "https://complaint-analytics-dashboard-k20j.vercel.app"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

st.set_page_config(
    page_title="Complaint Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global Styles ──────────────────────────────────────────────────────────────
st.markdown(r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }
.stApp { 
  background: radial-gradient(circle at 15% 50%, rgba(99, 102, 241, 0.08), transparent 25%), 
              radial-gradient(circle at 85% 30%, rgba(139, 92, 246, 0.08), transparent 25%), 
              #050505; 
  color: #f8fafc; 
}
.main .block-container { padding: 2rem 3rem !important; max-width: 100% !important; }

/* Sidebar styling */
section[data-testid="stSidebar"] { 
  background: rgba(10, 10, 15, 0.65) !important; 
  backdrop-filter: blur(20px) !important;
  -webkit-backdrop-filter: blur(20px) !important;
  border-right: 1px solid rgba(255, 255, 255, 0.05) !important; 
}
section[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
section[data-testid="stSidebar"] hr { border-color: rgba(255, 255, 255, 0.05); }

/* Custom Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: rgba(99,102,241,0.5); }

/* Fade-in Animation */
.main .block-container { animation: appFadeIn 1s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes appFadeIn { from { opacity: 0; transform: translateY(20px) scale(0.98); } to { opacity: 1; transform: translateY(0) scale(1); } }

/* Advanced Page Header */
.page-header { 
  background: linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%); 
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255,255,255,0.1); 
  border-radius: 20px; 
  padding: 24px 28px; 
  margin-bottom: 28px; 
  box-shadow: 0 20px 40px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.1);
  position: relative;
  overflow: hidden;
}
.page-header-title { font-size: 1.8rem; font-weight: 800; color: #f1f5f9; margin-bottom: 4px; display:flex; align-items:center; gap:10px; }
.page-header-sub { font-size: 0.85rem; color: #94a3b8; margin-bottom: 12px; }
.header-badges { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
.header-badge { 
  background: rgba(99,102,241,0.2); 
  border: 1px solid rgba(99,102,241,0.4); 
  border-radius: 50px; 
  padding: 6px 16px; 
  font-size: 0.75rem; 
  color: #a5b4fc; 
  font-weight: 600; 
  display:inline-flex; 
  align-items:center; 
  gap:6px; 
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  cursor: default;
}
.header-badge:hover {
  transform: scale(1.1) translateY(-3px);
  background: rgba(99,102,241,0.3);
  box-shadow: 0 8px 16px rgba(0,0,0,0.3);
  z-index: 10;
}

/* macOS Dock Inspired KPI Cards */
.kpi-grid { 
  display: flex; 
  gap: 12px; 
  margin-bottom: 28px; 
  align-items: stretch; 
  justify-content: center; 
  perspective: 1000px; 
}
.kpi-card {
  background: linear-gradient(135deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.03) 100%);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 16px;
  padding: 20px 18px;
  position: relative;
  overflow: hidden;
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease;
  transform-origin: center center;
  cursor: pointer;
  z-index: 1;
}
.kpi-card:hover {
  transform: scale(1.08) translateY(-8px) rotate(0.5deg);
  background: linear-gradient(135deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.06) 100%);
  border-color: rgba(99,102,241,0.5);
  box-shadow: 0 20px 40px rgba(0,0,0,0.4);
  z-index: 50;
}
.kpi-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--accent, linear-gradient(90deg, #6366f1, #8b5cf6)); border-radius: 16px 16px 0 0; }
.kpi-grid:hover .kpi-card { transform: scale(0.95); filter: brightness(0.75); }
.kpi-grid:hover .kpi-card:hover {
  transform: scale(1.18) translateY(-10px);
  filter: brightness(1);
  z-index: 10;
  box-shadow: 0 20px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.12), 0 8px 32px var(--glow, rgba(99,102,241,0.3));
}
.kpi-grid:hover .kpi-card:hover + .kpi-card,
.kpi-grid:hover .kpi-card:has(+ .kpi-card:hover) {
  transform: scale(1.07) translateY(-5px);
  filter: brightness(0.9);
  z-index: 5;
}

.kpi-icon { width:38px; height:38px; border-radius:10px; display:flex; align-items:center; justify-content:center; margin-bottom:10px; background: var(--icon-bg, rgba(99,102,241,0.15)); flex-shrink: 0; }
.kpi-icon svg { display:block; width:20px; height:20px; }
.kpi-label { font-size: 0.68rem; color: #64748b; letter-spacing: .08em; text-transform: uppercase; font-weight: 600; display: block; }
.kpi-value { font-size: 1.75rem; font-weight: 800; line-height: 1.15; margin-top: 6px; display: block; }
.kpi-sub { font-size: 0.68rem; color: #475569; margin-top: 6px; display: block; }

.progress-bar-wrap { background: rgba(255,255,255,0.06); border-radius: 99px; height: 6px; overflow: hidden; margin-top: 10px; }
.progress-bar-fill { height: 100%; border-radius: 99px; }

/* Glassmorphic Tabs */
.stTabs [data-baseweb="tab-list"] { background: rgba(255,255,255,0.04); border-radius: 12px; padding: 4px; gap: 4px; border: 1px solid rgba(255,255,255,0.06); }
.stTabs [data-baseweb="tab"] { border-radius: 8px; color: #94a3b8; font-weight: 600; font-size: 0.85rem; padding: 8px 18px; }
.stTabs [aria-selected="true"] { background: linear-gradient(135deg, #6366f1, #8b5cf6) !important; color: white !important; }

.stButton > button { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; border: none; border-radius: 10px; font-weight: 600; padding: 10px 22px; }

/* Global Focus & Input Overrides */
* { outline: none !important; }
*:focus, *:active, *:focus-visible { outline: none !important; box-shadow: none !important; }

div[data-testid="stTextInput"] > div, 
div[data-testid="stTextArea"] > div, 
div[data-testid="stSelectbox"] > div,
div[data-testid="stDateInput"] > div,
div[data-baseweb="input"], 
div[data-baseweb="base-input"],
div[data-baseweb="select"] {
  border-radius: 14px !important;
  border: none !important;
  background: transparent !important;
  outline: none !important;
  box-shadow: none !important;
}

div[data-testid="stTextInput"] [data-baseweb="base-input"],
div[data-testid="stTextArea"] [data-baseweb="base-input"],
div[data-testid="stSelectbox"] [data-baseweb="select"],
div[data-testid="stDateInput"] [data-baseweb="base-input"] {
  background: rgba(255,255,255,0.04) !important; 
  border: 1px solid rgba(255,255,255,0.1) !important; 
  border-radius: 14px !important; 
  backdrop-filter: blur(10px) !important;
  padding: 0 16px !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

div[data-testid="stTextInput"] [data-baseweb="base-input"]:focus-within,
div[data-testid="stTextArea"] [data-baseweb="base-input"]:focus-within,
div[data-testid="stSelectbox"] [data-baseweb="select"]:focus-within,
div[data-testid="stDateInput"] [data-baseweb="base-input"]:focus-within {
  border-color: rgba(99,102,241,0.8) !important; 
  background: rgba(255,255,255,0.08) !important;
  box-shadow: 0 0 0 2px rgba(99,102,241,0.2) !important;
}

div[data-testid="stTextInput"] input, 
div[data-testid="stTextArea"] textarea {
  background: transparent !important;
  border: none !important;
  color: #f1f5f9 !important;
}

input:-webkit-autofill {
  -webkit-text-fill-color: #f1f5f9 !important;
  -webkit-box-shadow: 0 0 0px 1000px #1e293b inset !important;
}
::selection { background: rgba(99,102,241,0.3); color: white; }
div[data-testid="InputInstructions"] { display: none !important; }

/* No Results Styling */
.no-results-card {
    background: rgba(255,255,255,0.02);
    border: 1px dashed rgba(255,255,255,0.1);
    border-radius: 20px;
    padding: 40px 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    color: #64748b;
    margin-top: 10px;
    min-height: 250px;
}
.no-results-icon { font-size: 3rem; margin-bottom: 16px; opacity: 0.5; }
.no-results-title { font-size: 1.1rem; font-weight: 600; color: #94a3b8; margin-bottom: 4px; }
.no-results-sub { font-size: 0.85rem; max-width: 250px; }
</style>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────────────────────
if "is_admin"        not in st.session_state: st.session_state.is_admin        = False
if "login_step"      not in st.session_state: st.session_state.login_step      = 0   # 0=closed, 1=username, 2=password
if "login_uid_input" not in st.session_state: st.session_state.login_uid_input = ""
if "drawer_open"     not in st.session_state: st.session_state.drawer_open     = False
if "submit_msg"      not in st.session_state: st.session_state.submit_msg      = None


# ── DB Helpers ─────────────────────────────────────────────────────────────────
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(exist_ok=True)
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id           TEXT PRIMARY KEY,
                created_date TEXT NOT NULL,
                closed_date  TEXT,
                area         TEXT NOT NULL,
                category     TEXT NOT NULL,
                priority     TEXT,
                status       TEXT NOT NULL DEFAULT 'Pending',
                description  TEXT NOT NULL
            )
        """)
        count = conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
        if count == 0 and CSV_PATH.exists():
            pd.read_csv(CSV_PATH).to_sql("complaints", conn, if_exists="append", index=False)


init_db()


@st.cache_data(ttl=30)
def load_all() -> pd.DataFrame:
    try:
        resp = requests.get(f"{API_URL}/complaints", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if not data:
                return pd.DataFrame(columns=["id", "created_date", "closed_date", "area", "category", "priority", "status", "description", "closure_days"])
            df = pd.DataFrame(data)
            df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
            df["closed_date"]  = pd.to_datetime(df["closed_date"],  errors="coerce")
            if "closure_days" not in df.columns:
                df["closure_days"] = (df["closed_date"] - df["created_date"]).dt.days
            return df
    except Exception as e:
        st.warning("Could not connect to API. Falling back to local database.")
        
    with get_connection() as conn:
        df = pd.read_sql_query("SELECT * FROM complaints", conn)
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["closed_date"]  = pd.to_datetime(df["closed_date"],  errors="coerce")
    df["closure_days"] = (df["closed_date"] - df["created_date"]).dt.days
    return df


def filter_df(df, start, end, area, category, status):
    f = df.copy()
    f = f[f["created_date"].dt.date >= start]
    f = f[f["created_date"].dt.date <= end]
    if area     != "All": f = f[f["area"]     == area]
    if category != "All": f = f[f["category"] == category]
    if status   != "All": f = f[f["status"]   == status]
    return f.sort_values("created_date", ascending=False)


def _refresh():
    st.cache_data.clear()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('## 📊 Analytics Dashboard')
    st.markdown("---")

    all_df = load_all()
    areas      = sorted(all_df["area"].dropna().unique().tolist())
    categories = sorted(all_df["category"].dropna().unique().tolist())
    statuses   = sorted(all_df["status"].dropna().unique().tolist())

    st.markdown("### 🔍 Filters")
    start_date = st.date_input("Start Date", value=date(2025, 1, 1))
    end_date   = st.date_input("End Date",   value=date.today())

    if start_date > end_date:
        st.warning("Start date is after end date")

    sel_area     = st.selectbox("Area",     ["All", *areas])
    sel_category = st.selectbox("Category", ["All", *categories])
    sel_status   = st.selectbox("Status",   ["All", *statuses])

    apply = st.button("🔍 Apply Filters", use_container_width=True)

    st.markdown("---")

    if st.session_state.is_admin:
        st.success("🔓 Admin mode active")
        if st.button("Logout", use_container_width=True):
            st.session_state.is_admin    = False
            st.session_state.login_step  = 0
            st.session_state.drawer_open = False
            st.rerun()
            
    elif st.session_state.login_step == 1:
        st.markdown("### 🔐 Admin Access")
        uid = st.text_input("Admin Name", placeholder="Enter Name", key="uid_field", label_visibility="collapsed")
        
        # Immediate transition on Enter
        if uid:
            if uid.strip() == ADMIN_USERNAME:
                st.session_state.login_uid_input = uid.strip()
                st.session_state.login_step = 2
                st.rerun()
            else:
                st.error("Username not found")
                
        if st.button("Cancel", use_container_width=True):
            st.session_state.login_step = 0
            st.rerun()
            
    elif st.session_state.login_step == 2:
        st.markdown(f"### 🔐 Password for {st.session_state.login_uid_input}")
        pwd = st.text_input("Password", type="password", placeholder="••••••••", key="pwd_field", label_visibility="collapsed")
        
        if pwd:
            if pwd == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.session_state.login_step = 0
                st.success("Welcome, Admin!")
                st.rerun()
            else:
                st.error("Incorrect password")
                
        if st.button("Back", use_container_width=True):
            st.session_state.login_step = 1
            st.rerun()
            
    else:
        if st.button("🔐 Admin Login", use_container_width=True):
            st.session_state.login_step = 1
            st.rerun()

# ── Main UI ──────────────────────────────────────────────────────────────────
df = filter_df(all_df, start_date, end_date, sel_area, sel_category, sel_status)

# Header
st.markdown(f"""
<div class="page-header">
    <div class="page-header-title">
        <svg viewBox="0 0 24 24" width="32" height="32" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="20" x2="18" y2="10"></line>
            <line x1="12" y1="20" x2="12" y2="4"></line>
            <line x1="6" y1="20" x2="6" y2="14"></line>
        </svg>
        Complaint Analytics Dashboard
    </div>
    <div class="page-header-sub">Advanced real-time monitoring and resolution tracking system.</div>
    <div class="header-badges">
        <div class="header-badge">📅 {start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}</div>
        <div class="header-badge">📍 {sel_area}</div>
        <div class="header-badge">🏷️ {sel_category}</div>
        <div class="header-badge">🔄 {len(df)} Records</div>
    </div>
</div>
""", unsafe_allow_html=True)

# KPI Row
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

with kpi1:
    total = len(df)
    st.markdown(f"""
    <div class="kpi-card" style="--accent: #6366f1;">
        <div>
            <div class="kpi-icon" style="--icon-bg: rgba(99,102,241,0.15); color: #818cf8;">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
            </div>
            <span class="kpi-label">Total</span>
            <span class="kpi-value">{total}</span>
        </div>
        <span class="kpi-sub">Across all filters</span>
    </div>
    """, unsafe_allow_html=True)

with kpi2:
    pending = len(df[df["status"] == "Pending"])
    perc_p = (pending/total*100) if total > 0 else 0
    st.markdown(f"""
    <div class="kpi-card" style="--accent: #f59e0b;">
        <div>
            <div class="kpi-icon" style="--icon-bg: rgba(245,158,11,0.15); color: #fbbf24;">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
            </div>
            <span class="kpi-label">Pending</span>
            <span class="kpi-value">{pending}</span>
        </div>
        <div class="progress-bar-wrap"><div class="progress-bar-fill" style="width: {perc_p}%; background: #f59e0b;"></div></div>
    </div>
    """, unsafe_allow_html=True)

with kpi3:
    progress = len(df[df["status"] == "In Progress"])
    perc_ip = (progress/total*100) if total > 0 else 0
    st.markdown(f"""
    <div class="kpi-card" style="--accent: #3b82f6;">
        <div>
            <div class="kpi-icon" style="--icon-bg: rgba(59,130,246,0.15); color: #60a5fa;">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
            </div>
            <span class="kpi-label">In Progress</span>
            <span class="kpi-value">{progress}</span>
        </div>
        <div class="progress-bar-wrap"><div class="progress-bar-fill" style="width: {perc_ip}%; background: #3b82f6;"></div></div>
    </div>
    """, unsafe_allow_html=True)

with kpi4:
    closed = len(df[df["status"] == "Closed"])
    perc_c = (closed/total*100) if total > 0 else 0
    st.markdown(f"""
    <div class="kpi-card" style="--accent: #10b981;">
        <div>
            <div class="kpi-icon" style="--icon-bg: rgba(16,185,129,0.15); color: #34d399;">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
            </div>
            <span class="kpi-label">Closed</span>
            <span class="kpi-value">{closed}</span>
        </div>
        <div class="progress-bar-wrap"><div class="progress-bar-fill" style="width: {perc_c}%; background: #10b981;"></div></div>
    </div>
    """, unsafe_allow_html=True)

with kpi5:
    avg_days = df["closure_days"].mean() if total > 0 else 0
    st.markdown(f"""
    <div class="kpi-card" style="--accent: #8b5cf6;">
        <div>
            <div class="kpi-icon" style="--icon-bg: rgba(139,92,246,0.15); color: #a78bfa;">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
            </div>
            <span class="kpi-label">Avg Closure</span>
            <span class="kpi-value">{avg_days:.1f}</span>
        </div>
        <span class="kpi-sub">Days to resolution</span>
    </div>
    """, unsafe_allow_html=True)

# Tabs
tab_trends, tab_areas, tab_records, tab_submit = st.tabs(["📈 Trends", "🗺️ Area Distribution", "📋 Records", "➕ Submit"])

with tab_trends:
    if not df.empty:
        trend_df = df.groupby(df["created_date"].dt.date).size().reset_index(name="count")
        fig = px.line(trend_df, x="created_date", y="count", title="Daily Complaint Volume",
                     color_discrete_sequence=["#6366f1"])
        
        # Consistent Chart Layout
        CHART_LAYOUT = dict(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8"),
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False),
            margin=dict(t=40, b=40, l=40, r=40)
        )
        
        fig.update_layout(**CHART_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.markdown("""
        <div class="no-results-card">
            <div class="no-results-icon">📈</div>
            <div class="no-results-title">No Trends to Display</div>
            <div class="no-results-sub">Adjust your filters to see historical complaint data.</div>
        </div>
        """, unsafe_allow_html=True)

with tab_areas:
    col1, col2 = st.columns(2)
    area_df = df.groupby("area").agg(
        total=("id", "count"),
        avg_closure_days=("closure_days", "mean")
    ).reset_index()

    with col1:
        st.subheader("📍 Complaints by Area")
        if not area_df.empty:
            fig = px.pie(area_df, values="total", names="area", hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(**CHART_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown("""
            <div class="no-results-card">
                <div class="no-results-icon">📍</div>
                <div class="no-results-title">No Area Data</div>
                <div class="no-results-sub">No complaints found for the selected criteria</div>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.subheader("⏱️ Avg Closure Days")
        if not area_df.empty and area_df["avg_closure_days"].notna().any():
            fig = px.bar(area_df.dropna(subset=["avg_closure_days"]), x="area", y="avg_closure_days",
                        color="avg_closure_days", color_continuous_scale="RdYlGn_r")
            fig.update_layout(**CHART_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown("""
            <div class="no-results-card">
                <div class="no-results-icon">⏱️</div>
                <div class="no-results-title">No Closure Data</div>
                <div class="no-results-sub">Closure analytics require 'Closed' status complaints</div>
            </div>
            """, unsafe_allow_html=True)

with tab_records:
    st.subheader("📋 Detailed Records")
    if not df.empty:
        st.dataframe(df.drop(columns=["closure_days"], errors="ignore"), use_container_width=True)
    else:
        st.markdown("""
        <div class="no-results-card" style="min-height: 400px;">
            <div class="no-results-icon">📋</div>
            <div class="no-results-title">No Matching Records</div>
            <div class="no-results-sub">Try broadening your search or resetting filters.</div>
        </div>
        """, unsafe_allow_html=True)

with tab_submit:
    if st.session_state.submit_msg:
        st.success(st.session_state.submit_msg)
        st.session_state.submit_msg = None

    st.subheader("➕ Register New Complaint")
    
    if "form_key" not in st.session_state:
        st.session_state.form_key = 0

    with st.form("new_complaint", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        new_id       = c1.text_input("ID", value=f"CMP-{datetime.now().strftime('%H%M%S')}", disabled=True)
        new_area     = c2.selectbox("Area", areas, key=f"new_area_{st.session_state.form_key}")
        new_category = c3.selectbox("Category", categories, key=f"new_category_{st.session_state.form_key}")
        new_date     = st.date_input("Date", value=date.today(), key=f"new_date_{st.session_state.form_key}")
        new_desc     = st.text_area("Description", placeholder="Describe the issue...", key=f"new_desc_{st.session_state.form_key}")

        if st.form_submit_button("Submit Complaint"):
            if len(new_desc.strip()) < 10:
                st.error("Please provide a more detailed description (min 10 chars).")
            else:
                payload = {
                    "id": new_id.strip(),
                    "created_date": new_date.isoformat(),
                    "area": new_area,
                    "category": new_category,
                    "description": new_desc.strip()
                }
                try:
                    resp = requests.post(f"{API_URL}/complaints", json=payload)
                    if resp.status_code == 201:
                        st.session_state.submit_msg = f"✅ Complaint {new_id} registered successfully!"
                        st.session_state.form_key += 1
                        _refresh()
                        st.rerun()
                    else:
                        st.error(f"Failed to submit: {resp.text}")
                except Exception as e:
                    st.error(f"Connection Error: {e}")

# ── Admin Section ──────────────────────────────────────────────────────────────
if st.session_state.is_admin:
    st.markdown("---")
    st.subheader("🛠️ Administrative Controls")
    
    adm_tab_update, adm_tab_delete = st.tabs(["✏️ Update Status", "🗑️ Purge Record"])
    
    with adm_tab_update:
        if not df.empty:
            sel_upd_id = st.selectbox("Select Record", df["id"].tolist())
            row = df[df["id"] == sel_upd_id].iloc[0]
            
            u1, u2 = st.columns(2)
            upd_status = u1.selectbox("New Status", ["Pending", "In Progress", "Closed"], 
                                    index=["Pending", "In Progress", "Closed"].index(row["status"]))
            upd_priority = u2.selectbox("Priority", ["Low", "Medium", "High"], 
                                      index=["Low", "Medium", "High"].index(row.get("priority", "Medium")) if row.get("priority") in ["Low", "Medium", "High"] else 1)
            
            upd_closed = st.date_input("Closed Date", value=date.today()) if upd_status == "Closed" else None
            
            if st.button("💾 Commit Changes", use_container_width=True):
                payload = {
                    "status": upd_status,
                    "priority": upd_priority,
                    "closed_date": upd_closed.isoformat() if upd_closed else None
                }
                try:
                    resp = requests.put(f"{API_URL}/complaints/{sel_upd_id}", json=payload)
                    if resp.status_code == 200:
                        st.success(f"Updated {sel_upd_id}")
                        _refresh()
                        st.rerun()
                    else:
                        st.error(f"Error: {resp.text}")
                except Exception as e:
                    st.error(f"Connection Error: {e}")
        else:
            st.info("No records to update.")

    with adm_tab_delete:
        if not df.empty:
            sel_del_id = st.selectbox("Select Record to Remove", df["id"].tolist())
            st.warning(f"Permanently delete {sel_del_id}?")
            if st.button("🗑️ Confirm Destruction", type="primary", use_container_width=True):
                try:
                    resp = requests.delete(f"{API_URL}/complaints/{sel_del_id}")
                    if resp.status_code == 200:
                        st.success("Record purged.")
                        _refresh()
                        st.rerun()
                    else:
                        st.error(f"Error: {resp.text}")
                except Exception as e:
                    st.error(f"Connection Error: {e}")
