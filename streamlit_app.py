"""
Complaint Analytics Dashboard - Streamlit Frontend
Uses Supabase when configured, with SQLite as the local fallback
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
if not (PROJECT_ROOT / "backend").exists():
    PROJECT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import (
    DuplicateComplaintError,
    delete_complaint_record,
    insert_complaint,
    init_db,
    read_complaints_df,
    update_complaint_record,
)

# ── Paths ──────────────────────────────────────────────────────────────────────
# Resolve data/ folder regardless of where Streamlit launches the script from.
def _find_data_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parent / "data",          # root-level data/
        Path(__file__).resolve().parent.parent / "data",   # one level up
        Path.cwd() / "data",                               # Streamlit Cloud
    ]
    for c in candidates:
        if c.exists():
            return c
    candidates[0].mkdir(parents=True, exist_ok=True)
    return candidates[0]

DATA_DIR = _find_data_dir()
DB_PATH  = DATA_DIR / "complaints.db"
CSV_PATH = DATA_DIR / "demo_complaints.csv"

# Ensure data directory exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

st.set_page_config(
    page_title="Complaint Analytics Dashboard",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global Styles ──────────────────────────────────────────────────────────────
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
*:focus, *:active, *:focus-visible { outline: none !important; }

/* ── Widget backgrounds ── */
/* Text inputs, text areas & date inputs */
div[data-testid="stTextInput"] [data-baseweb="input"],
div[data-testid="stTextArea"] [data-baseweb="textarea"],
div[data-testid="stDateInput"] [data-baseweb="input"] {
  background: #2a2d3e !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  border-radius: 14px !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
div[data-testid="stTextInput"] [data-baseweb="input"]:focus-within,
div[data-testid="stTextArea"] [data-baseweb="textarea"]:focus-within,
div[data-testid="stDateInput"] [data-baseweb="input"]:focus-within {
  border-color: rgba(99, 102, 241, 0.8) !important;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
}
div[data-testid="stTextInput"] [data-baseweb="base-input"],
div[data-testid="stTextArea"] [data-baseweb="base-input"],
div[data-testid="stDateInput"] [data-baseweb="base-input"] {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
}
div[data-testid="stTextInput"] [data-baseweb="base-input"]:hover,
div[data-testid="stTextArea"] [data-baseweb="base-input"]:hover,
div[data-testid="stDateInput"] [data-baseweb="base-input"]:hover {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
}
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stDateInput"] input {
  background: transparent !important;
  border: none !important;
  color: #f1f5f9 !important;
}

/* Selectbox */
div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
  background: #2a2d3e !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  border-radius: 14px !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"] > div:hover {
  border-color: rgba(99,102,241,0.5) !important;
  background: #32364a !important;
}
/* Make selectbox input text visible but keep it minimal */
div[data-testid="stSelectbox"] input {
  color: #f1f5f9 !important;
  caret-color: transparent !important;
}
/* Style the dropdown list */
[data-baseweb="popover"] [data-baseweb="menu"] {
  background: #1e2130 !important;
  border: 1px solid rgba(99,102,241,0.3) !important;
  border-radius: 12px !important;
}
[data-baseweb="popover"] [role="option"] {
  background: transparent !important;
  color: #e2e8f0 !important;
  border-radius: 8px !important;
}
[data-baseweb="popover"] [role="option"]:hover,
[data-baseweb="popover"] [aria-selected="true"] {
  background: rgba(99,102,241,0.2) !important;
  color: #a5b4fc !important;
}

input:-webkit-autofill {
  -webkit-text-fill-color: #f1f5f9 !important;
  -webkit-box-shadow: 0 0 0px 1000px #2a2d3e inset !important;
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
<svg width="0" height="0">
  <defs>
    <linearGradient id="svg-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop stop-color="#ec4899" offset="0%" />
      <stop stop-color="#8b5cf6" offset="100%" />
    </linearGradient>
  </defs>
</svg>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────────────────────
if "is_admin"        not in st.session_state: st.session_state.is_admin        = False
if "login_step"      not in st.session_state: st.session_state.login_step      = 0   # 0=closed, 1=username, 2=password
if "login_uid_input" not in st.session_state: st.session_state.login_uid_input = ""
if "drawer_open"     not in st.session_state: st.session_state.drawer_open     = False
if "submit_msg"      not in st.session_state: st.session_state.submit_msg      = None


# ── Data Helpers ───────────────────────────────────────────────────────────────
try:
    init_db()
except Exception as e:
    st.error(f"Database initialization failed: {e}")


@st.cache_data(ttl=30)
def load_all() -> pd.DataFrame:
    df = read_complaints_df()
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce", utc=True).dt.tz_localize(None)
    df["closed_date"]  = pd.to_datetime(df["closed_date"],  errors="coerce", utc=True).dt.tz_localize(None)
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
    st.markdown('## Analytics Dashboard')
    st.markdown("---")

    all_df = load_all()
    # If the loaded DataFrame is empty (e.g., Supabase has no records), fall back to the local demo CSV
    if all_df.empty:
        try:
            all_df = pd.read_csv(CSV_PATH)
            st.info("Loaded demo data from local CSV.")
        except Exception as e:
            st.error(f"Failed to load demo CSV: {e}")
    # Get distinct areas and categories from data. If none exist, keep list empty.
    areas = sorted(all_df["area"].dropna().unique().tolist())
    categories = sorted(all_df["category"].dropna().unique().tolist())
    # Fallback defaults to avoid empty dropdowns when even CSV is empty
    if not areas:
        areas = ["General"]
    if not categories:
        categories = ["General"]
    statuses   = sorted(all_df["status"].dropna().unique().tolist())    or ["Pending"]

    st.markdown("### Filters")
    start_date = st.date_input("Start Date", value=date(2025, 1, 1))
    end_date   = st.date_input("End Date",   value=date.today())

    if start_date > end_date:
        st.warning("Start date is after end date")

    sel_area     = st.selectbox("Area",     ["All", *areas])
    sel_category = st.selectbox("Category", ["All", *categories])
    sel_status   = st.selectbox("Status",   ["All", *statuses])

    apply = st.button("Apply Filters", use_container_width=True)

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
        st.markdown(f"### 🔑 Hi, {st.session_state.login_uid_input}")
        # Use a form to require explicit login
        with st.form(key="login_form"):
            pwd = st.text_input("Password", type="password", placeholder="Enter Password", key="pwd_field", label_visibility="collapsed")
            login_btn = st.form_submit_button("Login")
            if login_btn:
                if pwd == ADMIN_PASSWORD:
                    st.session_state.is_admin = True
                    st.session_state.login_step = 0
                    st.session_state.drawer_open = True
                    st.rerun()
                else:
                    st.error("Incorrect password")
        if st.button("← Back", use_container_width=True):
            st.session_state.login_step = 1
            st.rerun()
    else:
        if st.button("🔐 Admin Panel", use_container_width=True):
            st.session_state.login_step = 1
            st.rerun()

# ── Filtered Data ──────────────────────────────────────────────────────────────
# Store last applied filter values in session state
if "applied_filters" not in st.session_state:
    st.session_state.applied_filters = {
        "start_date": start_date,
        "end_date": end_date,
        "area": sel_area,
        "category": sel_category,
        "status": sel_status,
    }

if apply:
    st.session_state.applied_filters = {
        "start_date": start_date,
        "end_date": end_date,
        "area": sel_area,
        "category": sel_category,
        "status": sel_status,
    }

af = st.session_state.applied_filters
df = filter_df(all_df, af["start_date"], af["end_date"], af["area"], af["category"], af["status"])

# ── Analytics ─────────────────────────────────────────────────────────────────
total     = len(df)
closed_df = df[df["status"] == "Closed"]
open_cnt  = len(df[df["status"] != "Closed"])
raw_avg   = closed_df["closure_days"].mean() if not closed_df.empty else 0.0
avg_days  = float(raw_avg) if raw_avg == raw_avg else 0.0
rate      = round((len(closed_df) / total) * 100, 2) if total else 0.0
rate_w    = min(int(rate), 100)

trend_df = (
    df.assign(month=df["created_date"].dt.to_period("M").astype(str))
    .groupby("month").size().reset_index(name="complaints").sort_values("month")
) if not df.empty else pd.DataFrame()

area_df = (
    df.groupby("area")
    .agg(complaints=("id","count"), avg_closure_days=("closure_days","mean"))
    .reset_index().sort_values("complaints", ascending=False)
) if not df.empty else pd.DataFrame()

category_df = (
    df.groupby("category").size().reset_index(name="complaints")
    .sort_values("complaints", ascending=False)
) if not df.empty else pd.DataFrame()

# ── Main Layout ────────────────────────────────────────────────────────────────
main_col = st.container()

with main_col:
    now_str    = ""  # overridden by browser JS below
    date_range = f"{af['start_date'].strftime('%b %d')} → {af['end_date'].strftime('%b %d, %Y')}"
    admin_badge = '<span class="header-badge" style="background:rgba(99,102,241,0.3);border-color:rgba(139,92,246,0.6)"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#a5b4fc" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg> Admin</span>' if st.session_state.is_admin else ""

    st.markdown(f"""
<div class="page-header">
  <div class="page-header-title">
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#a5b4fc" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
    Complaint Analytics
  </div>
  <div class="page-header-sub">Real-time public service complaint intelligence dashboard</div>
  <div class="header-badges">
    <span class="header-badge" id="live-clock-badge">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#a5b4fc" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
      <span id="live-clock">--</span>
    </span>
    <span class="header-badge">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#a5b4fc" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
      {date_range}
    </span>
    {admin_badge}
  </div>
</div>
""", unsafe_allow_html=True)

    # Inject JS to show browser's local time (updates every second) using a component
    import streamlit.components.v1 as components
    components.html("""
    <script>
      function updateClock() {
        var clock = window.parent.document.getElementById('live-clock');
        if (clock) {
          var now = new Date();
          var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
          var month = months[now.getMonth()];
          var day = String(now.getDate()).padStart(2, '0');
          var year = now.getFullYear();
          
          var rawHours = now.getHours();
          var ampm = rawHours >= 12 ? 'PM' : 'AM';
          var hours12 = rawHours % 12 || 12; // convert 0 to 12
          var hours = String(hours12).padStart(2, '0');
          var minutes = String(now.getMinutes()).padStart(2, '0');
          var seconds = String(now.getSeconds()).padStart(2, '0');
          
          clock.textContent = month + ' ' + day + ', ' + year + ' • ' + hours + ':' + minutes + ':' + seconds + ' ' + ampm;
        }
      }
      updateClock();
      if (window.parent.liveClockInterval) {
        clearInterval(window.parent.liveClockInterval);
      }
      window.parent.liveClockInterval = setInterval(updateClock, 1000);
    </script>
    """, height=0)

    st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card" style="--accent:linear-gradient(90deg,#6366f1,#8b5cf6);--icon-bg:rgba(99,102,241,0.15);--glow:rgba(99,102,241,0.35)">
    <div class="kpi-icon">
      <svg viewBox="0 0 24 24" fill="none" stroke="#a5b4fc" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/>
        <rect x="9" y="3" width="6" height="4" rx="1"/>
        <line x1="9" y1="12" x2="15" y2="12"/><line x1="9" y1="16" x2="13" y2="16"/>
      </svg>
    </div>
    <span class="kpi-label">TOTAL COMPLAINTS</span>
    <span class="kpi-value" style="color:#f1f5f9">{total:,}</span>
    <span class="kpi-sub">In selected range</span>
  </div>
  <div class="kpi-card" style="--accent:linear-gradient(90deg,#10b981,#34d399);--icon-bg:rgba(16,185,129,0.15);--glow:rgba(16,185,129,0.35)">
    <div class="kpi-icon">
      <svg viewBox="0 0 24 24" fill="none" stroke="#6ee7b7" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
        <polyline points="22 4 12 14.01 9 11.01"/>
      </svg>
    </div>
    <span class="kpi-label">CLOSED</span>
    <span class="kpi-value" style="color:#6ee7b7">{len(closed_df):,}</span>
    <span class="kpi-sub">Fully resolved</span>
  </div>
  <div class="kpi-card" style="--accent:linear-gradient(90deg,#f59e0b,#fbbf24);--icon-bg:rgba(245,158,11,0.15);--glow:rgba(245,158,11,0.35)">
    <div class="kpi-icon">
      <svg viewBox="0 0 24 24" fill="none" stroke="#fcd34d" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14"/>
      </svg>
    </div>
    <span class="kpi-label">OPEN / PENDING</span>
    <span class="kpi-value" style="color:#fcd34d">{open_cnt:,}</span>
    <span class="kpi-sub">Awaiting resolution</span>
  </div>
  <div class="kpi-card" style="--accent:linear-gradient(90deg,#3b82f6,#60a5fa);--icon-bg:rgba(59,130,246,0.15);--glow:rgba(59,130,246,0.35)">
    <div class="kpi-icon">
      <svg viewBox="0 0 24 24" fill="none" stroke="#93c5fd" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="4" width="18" height="18" rx="2"/>
        <line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/>
        <line x1="3" y1="10" x2="21" y2="10"/>
        <path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01"/>
      </svg>
    </div>
    <span class="kpi-label">AVG CLOSURE TIME</span>
    <span class="kpi-value" style="color:#93c5fd">{avg_days:.1f} <span style="font-size:0.9rem;color:#64748b">days</span></span>
    <span class="kpi-sub">To close</span>
  </div>
  <div class="kpi-card" style="--accent:linear-gradient(90deg,#8b5cf6,#a78bfa);--icon-bg:rgba(139,92,246,0.15);--glow:rgba(139,92,246,0.35)">
    <div class="kpi-icon">
      <svg viewBox="0 0 24 24" fill="none" stroke="#c4b5fd" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/>
        <line x1="6" y1="20" x2="6" y2="14"/>
        <polyline points="3 7 12 2 21 7"/>
      </svg>
    </div>
    <span class="kpi-label">CLOSURE RATE</span>
    <span class="kpi-value" style="color:#c4b5fd">{rate:.1f}<span style="font-size:0.9rem;color:#64748b">%</span></span>
    <div class="progress-bar-wrap"><div class="progress-bar-fill" style="width:{rate_w}%;background:linear-gradient(90deg,#8b5cf6,#a78bfa)"></div></div>
  </div>
</div>
""", unsafe_allow_html=True)

    CHART_LAYOUT = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8", size=11),
        margin=dict(l=10, r=10, t=45, b=10),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#f1f5f9")),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)", zeroline=False),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", zeroline=False),
    )

    tab_overview, tab_records, tab_submit = st.tabs(["Overview", "Records", "Raise a Complaint"])

    with tab_overview:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Monthly Trend")
            if not trend_df.empty:
                fig = go.Figure(go.Scatter(
                    x=trend_df["month"], y=trend_df["complaints"],
                    mode="lines+markers", line=dict(color="#6366f1", width=2.5),
                    marker=dict(size=7, color="#8b5cf6"),
                    fill="tozeroy", fillcolor="rgba(99,102,241,0.1)"
                ))
                fig.update_layout(**CHART_LAYOUT, height=280)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.markdown("""
                <div class="no-results-card">
                    <div class="no-results-icon">📈</div>
                    <div class="no-results-title">No Trend Data</div>
                    <div class="no-results-sub">Adjust your filters to see monthly complaint trends</div>
                </div>
                """, unsafe_allow_html=True)

        with col2:
            st.subheader("Category Distribution")
            if not category_df.empty:
                fig = go.Figure(go.Pie(
                    labels=category_df["category"], values=category_df["complaints"],
                    hole=0.6, marker=dict(colors=["#6366f1","#8b5cf6","#a78bfa","#c4b5fd"])
                ))
                fig.update_layout(**CHART_LAYOUT, height=280)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.markdown("""
                <div class="no-results-card">
                    <div class="no-results-icon">🗂️</div>
                    <div class="no-results-title">No Category Data</div>
                    <div class="no-results-sub">No categories found in the selected range</div>
                </div>
                """, unsafe_allow_html=True)

        col3, col4 = st.columns(2)
        with col3:
            st.subheader("Complaints by Area")
            if not area_df.empty:
                sorted_area = area_df.sort_values("complaints")
                AREA_PALETTE = [
                    "#6366f1","#8b5cf6","#a78bfa","#c4b5fd",
                    "#3b82f6","#60a5fa","#10b981","#34d399",
                    "#f59e0b","#fbbf24","#ef4444","#f87171",
                    "#ec4899","#f472b6","#14b8a6","#2dd4bf",
                ]
                n = len(sorted_area)
                bar_colors = [AREA_PALETTE[i % len(AREA_PALETTE)] for i in range(n)]
                fig = go.Figure(go.Bar(
                    x=sorted_area["complaints"], y=sorted_area["area"],
                    orientation="h", marker=dict(color=bar_colors),
                    text=sorted_area["complaints"], textposition="outside",
                    textfont=dict(color="#94a3b8", size=11),
                ))
                fig.update_layout(**CHART_LAYOUT, height=max(280, n * 36))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.markdown("""
                <div class="no-results-card">
                    <div class="no-results-icon">🏙️</div>
                    <div class="no-results-title">No Area Data</div>
                    <div class="no-results-sub">No area distribution available for these filters</div>
                </div>
                """, unsafe_allow_html=True)

        with col4:
            st.subheader("Avg Closure Days")
            if not area_df.empty and "avg_closure_days" in area_df.columns:
                plot_df = area_df.dropna(subset=["avg_closure_days"])
                if not plot_df.empty:
                    fig = go.Figure(go.Bar(
                        x=plot_df["area"], y=plot_df["avg_closure_days"],
                        marker=dict(color=plot_df["avg_closure_days"], colorscale="RdYlGn_r")
                    ))
                    fig.update_layout(**CHART_LAYOUT, height=280)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.markdown("""
                    <div class="no-results-card">
                        <div class="no-results-icon">⏱️</div>
                        <div class="no-results-title">No Closure Data</div>
                        <div class="no-results-sub">Not enough closed complaints to calculate averages</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="no-results-card">
                    <div class="no-results-icon">⏱️</div>
                    <div class="no-results-title">No Data</div>
                    <div class="no-results-sub">Select a broader range to see closure time analytics</div>
                </div>
                """, unsafe_allow_html=True)

    with tab_records:
        st.subheader("Complaint Records")
        display_df = df.drop(columns=["closure_days"], errors="ignore").copy()
        for col in ["created_date", "closed_date"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(
                    lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else ""
                )
        if not display_df.empty:
            st.dataframe(display_df, use_container_width=True, height=400)
            csv_data = display_df.to_csv(index=False).encode("utf-8")
            st.download_button("Export CSV", data=csv_data, file_name="complaints_export.csv", mime="text/csv")
        else:
            st.markdown("""
            <div class="no-results-card" style="min-height: 400px;">
                <div class="no-results-icon">📋</div>
                <div class="no-results-title">No Matching Records</div>
                <div class="no-results-sub">Try adjusting your filters or search criteria in the sidebar to find records.</div>
            </div>
            """, unsafe_allow_html=True)

    with tab_submit:
        if st.session_state.submit_msg:
            st.success(st.session_state.submit_msg)
            st.session_state.submit_msg = None

        st.subheader("Raise New Complaint")

        if "form_key_f" not in st.session_state:
            st.session_state.form_key_f = 0

        with st.form("new_complaint", clear_on_submit=False):
            c1, c2 = st.columns(2)
            new_area     = c1.selectbox("Area", areas, key=f"new_area_f_{st.session_state.form_key_f}")
            # Date input removed – using server time (synchronized with client)
            new_category = c2.selectbox("Category", categories, key=f"new_category_f_{st.session_state.form_key_f}")


            new_desc     = st.text_area("Description", placeholder="Min 10 characters", key=f"new_desc_f_{st.session_state.form_key_f}")


            if st.form_submit_button("Submit"):
                if len(new_desc.strip()) < 10:
                    st.error("Description too short")
                else:
                    try:
                        created_record = insert_complaint({
                            "created_date": datetime.now().astimezone().isoformat(),
                            "closed_date": None,
                            "area": new_area,
                            "category": new_category,
                            "priority": None,
                            "status": "Pending",
                            "description": new_desc.strip(),
                        })
                        st.session_state.submit_msg = f"Complaint {created_record['id']} registered"
                        st.session_state.form_key_f += 1
                        _refresh()
                        st.rerun()
                    except DuplicateComplaintError:
                        st.error("Complaint ID already exists")
                    except Exception as e:
                        st.error(f"Failed to save complaint: {e}")

# ── Admin Panel (below dashboard when logged in) ───────────────────────────────
if st.session_state.is_admin:
    st.markdown("---")
    st.subheader("Admin Panel")

    tab_update, tab_delete = st.tabs(["Update Complaint", "Delete Complaint"])

    with tab_update:
        if not df.empty:
            sel_id = st.selectbox("Select Complaint", df["id"].tolist(), key="adm_sel")
            matching_rows = df[df["id"] == sel_id]
            if matching_rows.empty:
                st.warning("Selected complaint not found in filtered data")
            else:
                row    = matching_rows.iloc[0]
                u1, u2, u3 = st.columns(3)
                upd_status   = u1.selectbox("Status", ["Pending", "In Progress", "Closed"],
                                            index=["Pending", "In Progress", "Closed"].index(row["status"]) if row["status"] in ["Pending", "In Progress", "Closed"] else 0, key="adm_status")
                upd_area     = u2.selectbox("Area", areas, index=areas.index(row["area"]) if row["area"] in areas else 0, key="adm_area")
                upd_priority = u3.selectbox("Priority", ["Low", "Medium", "High"],
                                            index=["Low", "Medium", "High"].index(row["priority"]) if pd.notna(row["priority"]) and row["priority"] in ["Low", "Medium", "High"] else 1, key="adm_pri")
                upd_category = st.selectbox("Category", categories, index=categories.index(row["category"]) if row["category"] in categories else 0, key="adm_cat")
                upd_closed   = st.date_input("Closed Date", value=date.today(), key="adm_closed") if upd_status == "Closed" else None
                upd_desc     = st.text_area("Description", value=str(row["description"]) if pd.notna(row["description"]) else "", key="adm_desc")
                if st.button("Save Changes", use_container_width=True, key="adm_save"):
                    closed_val = upd_closed.isoformat() if upd_closed else None
                    try:
                        update_complaint_record(sel_id, {
                            "created_date": row["created_date"].strftime("%Y-%m-%d") if pd.notna(row["created_date"]) else date.today().isoformat(),
                            "closed_date": closed_val,
                            "area": upd_area,
                            "category": upd_category,
                            "priority": upd_priority,
                            "status": upd_status,
                            "description": upd_desc,
                        })
                        st.success(f"Updated {sel_id}")
                        _refresh()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to update complaint: {e}")
        else:
            st.info("No complaints available.")

    with tab_delete:
        if not df.empty:
            del_id = st.selectbox("Select to Delete", df["id"].tolist(), key="adm_del")
            st.warning(f"This will permanently delete **{del_id}**.")
            if st.button("Confirm Delete", type="primary", use_container_width=True, key="adm_del_btn"):
                try:
                    delete_complaint_record(del_id)
                    st.success(f"Deleted {del_id}")
                    _refresh()
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to delete complaint: {e}")
        else:
            st.info("No complaints available.")
