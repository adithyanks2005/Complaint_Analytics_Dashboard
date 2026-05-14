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
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap');
html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }

/* Animated App Background */
.stApp { 
  background-color: #030014;
  background-image: 
    radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
    radial-gradient(at 100% 0%, rgba(139, 92, 246, 0.15) 0px, transparent 50%),
    radial-gradient(at 100% 100%, rgba(236, 72, 153, 0.1) 0px, transparent 50%),
    radial-gradient(at 0% 100%, rgba(16, 185, 129, 0.1) 0px, transparent 50%);
  background-attachment: fixed;
  color: #f8fafc; 
  position: relative;
  overflow-x: hidden;
}
.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: url('data:image/svg+xml;utf8,%3Csvg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"%3E%3Cfilter id="noiseFilter"%3E%3CfeTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%25" height="100%25" filter="url(%23noiseFilter)" opacity="0.05"/%3E%3C/svg%3E');
    pointer-events: none;
    z-index: 9999;
    opacity: 0.8;
}

.main .block-container { padding: 3rem 4rem !important; max-width: 100% !important; z-index: 1; position: relative; }

/* Sidebar styling */
section[data-testid="stSidebar"] { 
  background: rgba(10, 10, 15, 0.4) !important; 
  backdrop-filter: blur(40px) saturate(150%) !important;
  -webkit-backdrop-filter: blur(40px) saturate(150%) !important;
  border-right: 1px solid rgba(255, 255, 255, 0.05) !important; 
  box-shadow: inset -1px 0 0 rgba(255,255,255,0.02);
}
section[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
section[data-testid="stSidebar"] hr { border-color: rgba(255, 255, 255, 0.05); }

/* Custom Scrollbar */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 20px; border: 2px solid transparent; background-clip: padding-box; }
::-webkit-scrollbar-thumb:hover { background: rgba(139,92,246,0.6); border: 2px solid transparent; background-clip: padding-box; }

/* Fade-in Animation */
.main .block-container { animation: appSlideUpFade 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards; opacity: 0; }
@keyframes appSlideUpFade { from { opacity: 0; transform: translateY(40px) scale(0.96); } to { opacity: 1; transform: translateY(0) scale(1); } }

/* Hyper-Advanced Page Header */
.page-header { 
  background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%); 
  backdrop-filter: blur(30px);
  -webkit-backdrop-filter: blur(30px);
  border-radius: 30px; 
  padding: 40px 48px; 
  margin-bottom: 40px; 
  box-shadow: 0 30px 60px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.1), inset 0 0 40px rgba(139,92,246,0.1);
  position: relative;
  overflow: hidden;
  transform-style: preserve-3d;
}
.page-header::before {
  content: ''; position: absolute; inset: -2px; border-radius: 32px;
  background: linear-gradient(90deg, #ec4899, #8b5cf6, #3b82f6, #10b981, #ec4899);
  background-size: 400%;
  z-index: -1;
  animation: rgbBorderGlow 8s linear infinite;
  opacity: 0.4;
  filter: blur(8px);
}
.page-header::after {
  content: ''; position: absolute; inset: 0; border-radius: 30px;
  background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, transparent 100%);
  pointer-events: none;
}
@keyframes rgbBorderGlow { 0% { background-position: 0% 50%; } 100% { background-position: 100% 50%; } }

.page-header-title { 
  font-size: 3rem; font-weight: 900; 
  background: linear-gradient(to right, #fff, #a5b4fc);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 12px; display:flex; align-items:center; gap:16px; letter-spacing: -0.03em; z-index:1; position:relative;
  text-shadow: 0 10px 30px rgba(99,102,241,0.2);
}
.page-header-title svg { filter: drop-shadow(0 0 12px rgba(165,180,252,0.8)); stroke: url(#svg-gradient); }
.page-header-sub { font-size: 1.1rem; color: #cbd5e1; margin-bottom: 24px; font-weight: 400; z-index:1; position:relative; max-width: 600px; line-height: 1.6; opacity: 0.8;}

.header-badges { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 20px; z-index:1; position:relative; }
.header-badge { 
  background: rgba(255,255,255,0.03); 
  border: 1px solid rgba(255,255,255,0.1); 
  backdrop-filter: blur(20px);
  border-radius: 100px; 
  padding: 10px 24px; 
  font-size: 0.85rem; 
  color: #e2e8f0; 
  font-weight: 700; 
  display:inline-flex; 
  align-items:center; 
  gap:10px; 
  transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow: inset 0 1px 1px rgba(255,255,255,0.05);
}
.header-badge:hover {
  transform: translateY(-4px) scale(1.05);
  background: rgba(139,92,246,0.15);
  border-color: rgba(139,92,246,0.4);
  color: #fff;
  box-shadow: 0 15px 30px rgba(139,92,246,0.3), inset 0 1px 1px rgba(255,255,255,0.2);
}
.admin-pulse { animation: adminPulse 2s infinite; }
@keyframes adminPulse { 0% { box-shadow: 0 0 0 0 rgba(139,92,246,0.4); } 70% { box-shadow: 0 0 0 15px rgba(139,92,246,0); } 100% { box-shadow: 0 0 0 0 rgba(139,92,246,0); } }

/* Hyper-Advanced KPI Cards */
.kpi-grid { 
  display: flex; 
  gap: 24px; 
  margin-bottom: 48px; 
  align-items: stretch; 
  justify-content: center; 
  perspective: 2000px;
}
.kpi-card {
  background: linear-gradient(145deg, rgba(30, 30, 35, 0.4), rgba(15, 15, 20, 0.6));
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 32px;
  padding: 32px 28px;
  position: relative;
  overflow: hidden;
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: all 0.6s cubic-bezier(0.23, 1, 0.32, 1);
  box-shadow: 0 10px 30px rgba(0,0,0,0.2);
  transform-style: preserve-3d;
  animation: staggerUp 0.8s backwards;
}
.kpi-card:nth-child(1) { animation-delay: 0.1s; }
.kpi-card:nth-child(2) { animation-delay: 0.2s; }
.kpi-card:nth-child(3) { animation-delay: 0.3s; }
.kpi-card:nth-child(4) { animation-delay: 0.4s; }
.kpi-card:nth-child(5) { animation-delay: 0.5s; }
@keyframes staggerUp { from { opacity: 0; transform: translateY(60px) rotateX(-15deg); } to { opacity: 1; transform: translateY(0) rotateX(0); } }

.kpi-card::before { 
  content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background: radial-gradient(circle at 50% 0%, var(--accent, rgba(255,255,255,0.1)) 0%, transparent 60%); 
  opacity: 0.1; transition: opacity 0.6s, transform 0.6s;
  pointer-events: none;
}
.kpi-card::after {
  content: ''; position: absolute; inset: 0; border-radius: 32px;
  padding: 2px; background: linear-gradient(135deg, var(--accent), transparent 60%);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor; mask-composite: exclude; opacity: 0; transition: opacity 0.6s;
}

.kpi-grid:hover .kpi-card { filter: blur(2px) brightness(0.7); transform: scale(0.95); }
.kpi-grid .kpi-card:hover {
  filter: blur(0) brightness(1.1);
  transform: translateY(-16px) scale(1.08) rotateX(5deg) rotateY(-2deg);
  background: linear-gradient(145deg, rgba(40, 40, 45, 0.5), rgba(20, 20, 25, 0.7));
  box-shadow: 0 40px 80px rgba(0,0,0,0.4), 0 0 40px var(--glow, rgba(99,102,241,0.2));
  z-index: 10;
}
.kpi-card:hover::before { opacity: 0.3; transform: scale(1.2) translateY(10%); }
.kpi-card:hover::after { opacity: 1; }

.kpi-icon { 
  width:64px; height:64px; border-radius:20px; display:flex; align-items:center; justify-content:center; 
  margin-bottom:24px; 
  background: var(--icon-bg, rgba(255,255,255,0.05)); 
  border: 1px solid rgba(255,255,255,0.1); 
  box-shadow: 0 10px 20px rgba(0,0,0,0.1), inset 0 2px 4px rgba(255,255,255,0.1); 
  transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1); 
  position: relative;
  overflow: hidden;
}
.kpi-icon::after {
    content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
    background: linear-gradient(45deg, transparent, rgba(255,255,255,0.3), transparent);
    transform: rotate(45deg) translateY(-100%); transition: transform 0.6s;
}
.kpi-card:hover .kpi-icon { transform: scale(1.15) translateZ(30px); box-shadow: 0 20px 40px var(--glow, rgba(0,0,0,0.3)); }
.kpi-card:hover .kpi-icon::after { transform: rotate(45deg) translateY(100%); }
.kpi-icon svg { width:32px; height:32px; filter: drop-shadow(0 4px 6px rgba(0,0,0,0.3)); transition: transform 0.6s; }
.kpi-card:hover .kpi-icon svg { transform: scale(1.1); }

.kpi-label { font-size: 0.8rem; color: #94a3b8; letter-spacing: 0.15em; text-transform: uppercase; font-weight: 800; display: block; z-index: 1; position: relative; transition: color 0.3s; }
.kpi-card:hover .kpi-label { color: #cbd5e1; }
.kpi-value { font-size: 3rem; font-weight: 900; line-height: 1.1; margin-top: 12px; display: block; letter-spacing: -0.03em; z-index: 1; position: relative; text-shadow: 0 4px 20px rgba(0,0,0,0.4); transform: translateZ(20px); }
.kpi-sub { font-size: 0.85rem; color: #64748b; margin-top: 12px; display: block; font-weight: 500; z-index: 1; position: relative; }

.progress-bar-wrap { background: rgba(255,255,255,0.03); border-radius: 99px; height: 10px; overflow: hidden; margin-top: 20px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.02); }
.progress-bar-fill { height: 100%; border-radius: 99px; position: relative; overflow: hidden; box-shadow: 0 0 10px var(--glow); transition: width 1.5s cubic-bezier(0.16, 1, 0.3, 1); }
.progress-bar-fill::after { content: ''; position: absolute; top:0; left:0; right:0; bottom:0; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.6), transparent); animation: shimmerFast 1.5s infinite; }
@keyframes shimmerFast { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }

/* Hyper Glassmorphic Tabs */
.stTabs [data-baseweb="tab-list"] { 
  background: rgba(255,255,255,0.03); 
  backdrop-filter: blur(20px);
  border-radius: 20px; 
  padding: 8px; 
  gap: 12px; 
  border: 1px solid rgba(255,255,255,0.08); 
  box-shadow: 0 10px 20px rgba(0,0,0,0.1), inset 0 1px 1px rgba(255,255,255,0.05);
}
.stTabs [data-baseweb="tab"] { 
  border-radius: 14px; 
  color: #94a3b8; 
  font-weight: 700; 
  font-size: 1rem; 
  padding: 12px 28px;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  letter-spacing: 0.02em;
}
.stTabs [data-baseweb="tab"]:hover { background: rgba(255,255,255,0.08); color: #f8fafc; transform: translateY(-2px); }
.stTabs [aria-selected="true"] { 
  background: linear-gradient(135deg, #6366f1, #d946ef) !important; 
  color: white !important; 
  box-shadow: 0 8px 24px rgba(217,70,239,0.4), inset 0 2px 2px rgba(255,255,255,0.2) !important;
  text-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

/* Stunning Buttons */
.stButton > button { 
  background: linear-gradient(135deg, #3b82f6, #8b5cf6); 
  color: white; 
  border: none;
  border-radius: 16px; 
  font-weight: 700; 
  font-size: 1rem;
  padding: 14px 32px; 
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow: 0 10px 20px rgba(139, 92, 246, 0.3), inset 0 2px 2px rgba(255,255,255,0.2);
  position: relative;
  overflow: hidden;
  z-index: 1;
}
.stButton > button::before {
    content: ''; position: absolute; top:0; left:0; width:100%; height:100%;
    background: linear-gradient(135deg, #ec4899, #8b5cf6);
    opacity: 0; transition: opacity 0.4s; z-index: -1;
}
.stButton > button:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: 0 15px 30px rgba(236, 72, 153, 0.4), inset 0 2px 2px rgba(255,255,255,0.3);
}
.stButton > button:hover::before { opacity: 1; }
.stButton > button:active { transform: translateY(2px) scale(0.98); }

/* Hyper Input Fields - Deep Liquid Glass */
div[data-testid="stTextInput"] [data-baseweb="base-input"],
div[data-testid="stTextArea"] [data-baseweb="base-input"],
div[data-testid="stSelectbox"] [data-baseweb="select"],
div[data-testid="stDateInput"] [data-baseweb="base-input"] {
  background: rgba(0,0,0,0.3) !important; 
  border: 1px solid rgba(255,255,255,0.06) !important; 
  border-radius: 20px !important; 
  backdrop-filter: blur(16px) !important;
  padding: 6px 20px !important;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important;
  box-shadow: inset 0 4px 8px rgba(0,0,0,0.4) !important;
}

div[data-testid="stTextInput"] [data-baseweb="base-input"]:focus-within,
div[data-testid="stTextArea"] [data-baseweb="base-input"]:focus-within,
div[data-testid="stSelectbox"] [data-baseweb="select"]:focus-within,
div[data-testid="stDateInput"] [data-baseweb="base-input"]:focus-within {
  border-color: #d946ef !important; 
  background: rgba(217,70,239,0.05) !important;
  transform: translateY(-2px);
  box-shadow: 0 0 0 4px rgba(217,70,239,0.15), inset 0 2px 4px rgba(0,0,0,0.2), 0 10px 20px rgba(217,70,239,0.1) !important;
}

div[data-testid="stTextInput"] input, 
div[data-testid="stTextArea"] textarea {
  background: transparent !important;
  border: none !important;
  color: #f8fafc !important;
  font-size: 1.05rem !important;
  font-weight: 500 !important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"] { color: #f8fafc !important; font-size: 1.05rem !important; font-weight: 500 !important;}
div[data-testid="stSelectbox"] [data-baseweb="select"] > div { border: none !important; box-shadow: none !important; }
div[data-testid="stDateInput"] input { color: #f8fafc !important; font-size: 1.05rem !important; font-weight: 500 !important;}

/* Eliminate borders globally on rounded inputs */
div[data-testid="stTextInput"] > div, 
div[data-testid="stTextArea"] > div, 
div[data-testid="stSelectbox"] > div,
div[data-testid="stDateInput"] > div { border: none !important; box-shadow: none !important; overflow: visible !important; }

/* No Results Card - Polished Holographic */
.no-results-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
    border: 1px dashed rgba(255,255,255,0.15);
    backdrop-filter: blur(12px);
    border-radius: 32px;
    padding: 60px 30px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    color: #64748b;
    margin-top: 24px;
    min-height: 320px;
    transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
    overflow: hidden;
}
.no-results-card::after {
    content: ''; position: absolute; top:0; left:-100%; width:50%; height:100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent);
    animation: holoPass 4s infinite linear;
}
@keyframes holoPass { 0% { left: -100%; } 100% { left: 200%; } }
.no-results-card:hover { 
    border-color: rgba(139,92,246,0.5); 
    background: rgba(139,92,246,0.05); 
    transform: translateY(-8px);
    box-shadow: 0 20px 40px rgba(0,0,0,0.2), inset 0 0 20px rgba(139,92,246,0.1);
}
.no-results-icon { font-size: 4rem; margin-bottom: 24px; opacity: 0.8; filter: drop-shadow(0 10px 15px rgba(0,0,0,0.3)); animation: floatGlow 4s ease-in-out infinite; }
@keyframes floatGlow { 0% { transform: translateY(0); filter: drop-shadow(0 10px 15px rgba(139,92,246,0.2)); } 50% { transform: translateY(-15px); filter: drop-shadow(0 25px 25px rgba(139,92,246,0.5)); } 100% { transform: translateY(0); filter: drop-shadow(0 10px 15px rgba(139,92,246,0.2)); } }
.no-results-title { font-size: 1.5rem; font-weight: 800; color: #f8fafc; margin-bottom: 12px; letter-spacing: -0.02em; }
.no-results-sub { font-size: 1rem; max-width: 320px; line-height: 1.6; color: #94a3b8; }

/* Global overrides */
* { outline: none !important; }
*:focus, *:active, *:focus-visible { outline: none !important; box-shadow: none !important; }
input:-webkit-autofill { -webkit-text-fill-color: #f1f5f9 !important; -webkit-box-shadow: 0 0 0px 1000px #1e293b inset !important; }
::selection { background: rgba(217,70,239,0.4); color: white; }
div[data-testid="InputInstructions"] { display: none !important; }
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
        st.markdown(f"### 🔑 Hi, {st.session_state.login_uid_input}")
        pwd = st.text_input("Password", type="password", placeholder="Enter Password", key="pwd_field", label_visibility="collapsed")
        
        # Immediate login on Enter
        if pwd:
            if pwd == ADMIN_PASSWORD:
                st.session_state.is_admin    = True
                st.session_state.login_step  = 0
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
    now_str    = datetime.now().strftime("%b %d, %Y · %H:%M")
    date_range = f"{start_date.strftime('%b %d')} → {end_date.strftime('%b %d, %Y')}"
    admin_badge = '<span class="header-badge" style="background:rgba(99,102,241,0.3)">🔓 Admin</span>' if st.session_state.is_admin else ""

    st.markdown(f"""
<div class="page-header">
  <div class="page-header-title">
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#a5b4fc" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
    Complaint Analytics
  </div>
  <div class="page-header-sub">Real-time public service complaint intelligence dashboard</div>
  <div class="header-badges">
    <span class="header-badge">&#128337; {now_str}</span>
    <span class="header-badge">&#128197; {date_range}</span>
    {admin_badge}
  </div>
</div>
""", unsafe_allow_html=True)

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

    tab_overview, tab_records, tab_submit = st.tabs(["📊 Overview", "📋 Records", "➕ Raise a Complaint"])

    with tab_overview:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📈 Monthly Trend")
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
            st.subheader("🗂️ Category Distribution")
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
            st.subheader("🏙️ Complaints by Area")
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
            st.subheader("⏱️ Avg Closure Days")
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
        st.subheader("📋 Complaint Records")
        display_df = df.drop(columns=["closure_days"], errors="ignore").copy()
        for col in ["created_date", "closed_date"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].dt.strftime("%Y-%m-%d")
        if not display_df.empty:
            st.dataframe(display_df, use_container_width=True, height=400)
            csv_data = display_df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Export CSV", data=csv_data, file_name="complaints_export.csv", mime="text/csv")
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

        st.subheader("➕ Register New Complaint")

        if "form_key" not in st.session_state:
            st.session_state.form_key = 0

        with st.form("new_complaint", clear_on_submit=False):
            c1, c2, c3 = st.columns(3)
            new_id       = c1.text_input("ID", value=f"CMP-{datetime.now().strftime('%H%M%S')}", disabled=True)
            new_area     = c2.selectbox("Area", areas, key=f"new_area_{st.session_state.form_key}")
            new_category = c3.selectbox("Category", categories, key=f"new_category_{st.session_state.form_key}")
            new_date     = st.date_input("Date", value=date.today(), key=f"new_date_{st.session_state.form_key}")
            new_desc     = st.text_area("Description", placeholder="Min 10 characters", key=f"new_desc_{st.session_state.form_key}")

            if st.form_submit_button("Submit"):
                if len(new_desc.strip()) < 10:
                    st.error("Description too short")
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
                            st.session_state.submit_msg = f"Complaint {new_id} registered"
                            st.session_state.form_key += 1
                            _refresh()
                            st.rerun()
                        elif resp.status_code == 409:
                            st.error("Complaint ID already exists")
                        else:
                            st.error(f"API Error: {resp.text}")
                    except Exception as e:
                        st.error(f"Failed to connect to API: {e}")

# ── Admin Panel (below dashboard when logged in) ───────────────────────────────
if st.session_state.is_admin:
    st.markdown("---")
    st.subheader("🛠️ Admin Panel")

    tab_update, tab_delete = st.tabs(["✏️ Update Complaint", "🗑️ Delete Complaint"])

    with tab_update:
        if not df.empty:
            sel_id = st.selectbox("Select Complaint", df["id"].tolist(), key="adm_sel")
            row    = df[df["id"] == sel_id].iloc[0]
            u1, u2, u3 = st.columns(3)
            upd_status   = u1.selectbox("Status", ["Pending", "In Progress", "Closed"],
                                        index=["Pending", "In Progress", "Closed"].index(row.get("status", "Pending")), key="adm_status")
            upd_area     = u2.selectbox("Area", areas, index=areas.index(row["area"]), key="adm_area")
            upd_priority = u3.selectbox("Priority", ["Low", "Medium", "High"], 
                                        index=["Low", "Medium", "High"].index(row.get("priority", "Medium")) if row.get("priority") in ["Low", "Medium", "High"] else 1, key="adm_pri")
            upd_category = st.selectbox("Category", categories, index=categories.index(row["category"]), key="adm_cat")
            upd_closed   = st.date_input("Closed Date", value=date.today(), key="adm_closed") if upd_status == "Closed" else None
            upd_desc     = st.text_area("Description", value=row.get("description", ""), key="adm_desc")
            if st.button("💾 Save Changes", use_container_width=True, key="adm_save"):
                closed_val = upd_closed.isoformat() if upd_closed else None
                payload = {
                    "status": upd_status,
                    "priority": upd_priority,
                    "area": upd_area,
                    "category": upd_category,
                    "closed_date": closed_val,
                    "description": upd_desc
                }
                try:
                    resp = requests.put(f"{API_URL}/complaints/{sel_id}", json=payload)
                    if resp.status_code == 200:
                        st.success(f"✅ Updated {sel_id}")
                        _refresh()
                        st.rerun()
                    else:
                        st.error(f"API Error: {resp.text}")
                except Exception as e:
                    st.error(f"Failed to connect to API: {e}")
        else:
            st.info("No complaints available.")

    with tab_delete:
        if not df.empty:
            del_id = st.selectbox("Select to Delete", df["id"].tolist(), key="adm_del")
            st.warning(f"This will permanently delete **{del_id}**.")
            if st.button("🗑️ Confirm Delete", type="primary", use_container_width=True, key="adm_del_btn"):
                try:
                    resp = requests.delete(f"{API_URL}/complaints/{del_id}")
                    if resp.status_code == 200:
                        st.success(f"Deleted {del_id}")
                        _refresh()
                        st.rerun()
                    else:
                        st.error(f"API Error: {resp.text}")
                except Exception as e:
                    st.error(f"Failed to connect to API: {e}")
        else:
            st.info("No complaints available.")


