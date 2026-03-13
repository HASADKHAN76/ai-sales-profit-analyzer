"""
app.py — AI Sales & Profit Analyzer  (professional UI v2)
Run with:  streamlit run app.py
"""

from __future__ import annotations
import os, io
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from data_connector import CSVConnector
from data_processor import (
    build_context_summary, load_and_clean, monthly_summary,
    top_customers, top_products, total_kpis, validate_dataframe,
)
from ai_assistant import SalesAIAssistant

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SalesIQ — AI Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Design system  (single source of truth for all colours / tokens)
# ─────────────────────────────────────────────────────────────────────────────
C = {
    "bg":        "#080d1a",
    "surface":   "#0d1526",
    "surface2":  "#111d35",
    "border":    "#1a2d50",
    "indigo":    "#6366f1",
    "indigo_lt": "#818cf8",
    "cyan":      "#06b6d4",
    "emerald":   "#10b981",
    "amber":     "#f59e0b",
    "rose":      "#f43f5e",
    "slate":     "#94a3b8",
    "text":      "#e2e8f0",
    "muted":     "#64748b",
}

PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor ="rgba(13,21,38,0.7)",
    font         =dict(color=C["text"], family="Inter, sans-serif", size=12),
    hoverlabel   =dict(bgcolor=C["surface2"], bordercolor=C["border"],
                       font_color=C["text"]),
)

# Reusable helpers — spread inside update_layout calls as needed
AX     = dict(gridcolor=C["border"], zeroline=False,
              linecolor=C["border"], tickfont=dict(color=C["slate"]))
LEGEND = dict(bgcolor="rgba(0,0,0,0)", bordercolor=C["border"],
              font=dict(color=C["text"]))
MARGIN = dict(l=0, r=0, t=36, b=0)

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Reset & base ─────────────────────────────────────────── */
html, body, [class*="css"], .stApp {{
    font-family: 'Inter', system-ui, sans-serif;
    background: {C["bg"]};
    color: {C["text"]};
}}
.stApp {{ background: {C["bg"]}; }}

/* ── Scrollbar ────────────────────────────────────────────── */
::-webkit-scrollbar {{ width:5px; height:5px; }}
::-webkit-scrollbar-track {{ background: {C["surface"]}; }}
::-webkit-scrollbar-thumb {{ background: {C["border"]}; border-radius:10px; }}

/* ── Remove default Streamlit chrome ──────────────────────── */
#MainMenu, footer, header {{ visibility:hidden; }}
.block-container {{ padding: 1.5rem 2rem 2rem; max-width:1400px; }}

/* ── Sidebar ──────────────────────────────────────────────── */
section[data-testid="stSidebar"] {{
    background: {C["surface"]};
    border-right: 1px solid {C["border"]};
    padding-top: 0;
}}
section[data-testid="stSidebar"] * {{ color: {C["text"]} !important; }}
section[data-testid="stSidebar"] .stFileUploader {{
    background: {C["surface2"]};
    border: 1px dashed {C["border"]};
    border-radius: 10px;
    padding: .6rem;
}}
section[data-testid="stSidebar"] hr {{
    border-color: {C["border"]} !important;
    margin: .8rem 0;
}}

/* ── Top nav bar ──────────────────────────────────────────── */
.topbar {{
    display:flex; align-items:center; justify-content:space-between;
    padding: .8rem 0 1.2rem;
    border-bottom: 1px solid {C["border"]};
    margin-bottom: 1.6rem;
}}
.topbar-logo {{
    display:flex; align-items:center; gap:.7rem;
}}
.topbar-logo-icon {{
    background: linear-gradient(135deg,{C["indigo"]},{C["cyan"]});
    border-radius:10px; width:36px; height:36px;
    display:flex; align-items:center; justify-content:center;
    font-size:1.1rem;
}}
.topbar-title {{
    font-size:1.2rem; font-weight:700; color:{C["text"]};
    letter-spacing:-.02em;
}}
.topbar-subtitle {{
    font-size:.72rem; color:{C["muted"]}; font-weight:400;
}}
.topbar-badge {{
    background:{C["surface2"]}; border:1px solid {C["border"]};
    border-radius:20px; padding:.25rem .75rem;
    font-size:.72rem; color:{C["slate"]}; font-weight:500;
}}

/* ── KPI cards ────────────────────────────────────────────── */
.kpi-grid {{
    display:grid;
    grid-template-columns: repeat(5, 1fr);
    gap:.9rem;
    margin-bottom:1.6rem;
}}
.kpi-card {{
    background: {C["surface"]};
    border: 1px solid {C["border"]};
    border-radius:14px;
    padding:1.1rem 1.3rem;
    position:relative;
    overflow:hidden;
    transition: border-color .2s;
}}
.kpi-card::before {{
    content:'';
    position:absolute; top:0; left:0;
    width:4px; height:100%;
    background: var(--accent, {C["indigo"]});
    border-radius:14px 0 0 14px;
}}
.kpi-card:hover {{ border-color:{C["indigo"]}44; }}
.kpi-icon {{
    font-size:1.3rem; margin-bottom:.5rem; opacity:.85;
}}
.kpi-label {{
    font-size:.68rem; text-transform:uppercase; letter-spacing:.1em;
    color:{C["muted"]}; font-weight:600; margin-bottom:.35rem;
}}
.kpi-value {{
    font-size:1.6rem; font-weight:700; color:{C["text"]};
    letter-spacing:-.03em; line-height:1.1;
}}
.kpi-footer {{
    display:flex; align-items:center; gap:.4rem;
    margin-top:.45rem;
}}
.kpi-sub {{ font-size:.72rem; color:{C["muted"]}; }}
.delta-up   {{ font-size:.72rem; color:{C["emerald"]}; font-weight:600; }}
.delta-down {{ font-size:.72rem; color:{C["rose"]};    font-weight:600; }}

/* ── Section headers ──────────────────────────────────────── */
.section-header {{
    display:flex; align-items:center; gap:.6rem;
    margin: 1.4rem 0 .8rem;
}}
.section-dot {{
    width:4px; height:18px;
    background: linear-gradient({C["indigo"]},{C["cyan"]});
    border-radius:4px; flex-shrink:0;
}}
.section-title {{
    font-size:.8rem; font-weight:700; color:{C["slate"]};
    text-transform:uppercase; letter-spacing:.1em;
}}

/* ── Chart panels ─────────────────────────────────────────── */
.chart-panel {{
    background:{C["surface"]};
    border:1px solid {C["border"]};
    border-radius:14px;
    padding:1.2rem 1.4rem 1rem;
    margin-bottom:1rem;
}}
.chart-panel-title {{
    font-size:.78rem; font-weight:600; color:{C["slate"]};
    text-transform:uppercase; letter-spacing:.08em;
    margin-bottom:.8rem;
}}

/* ── Tabs ─────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
    background:{C["surface"]};
    border-radius:12px; padding:.25rem;
    gap:.15rem;
    border: 1px solid {C["border"]};
}}
.stTabs [data-baseweb="tab"] {{
    background: transparent;
    color:{C["slate"]}; font-size:.8rem; font-weight:500;
    border-radius:9px; padding:.4rem .9rem;
    border:none;
}}
.stTabs [aria-selected="true"] {{
    background: linear-gradient(135deg,{C["indigo"]},{C["indigo_lt"]}) !important;
    color:#fff !important; font-weight:600;
}}
.stTabs [data-baseweb="tab-border"] {{ display:none; }}
.stTabs [data-baseweb="tab-panel"] {{ padding-top:1.4rem; }}

/* ── Buttons ──────────────────────────────────────────────── */
.stButton > button {{
    background: linear-gradient(135deg,{C["indigo"]},{C["indigo_lt"]});
    color:#fff; border:none; border-radius:9px;
    font-size:.8rem; font-weight:600; padding:.45rem 1.1rem;
    transition: opacity .2s, transform .15s;
}}
.stButton > button:hover {{ opacity:.88; transform:translateY(-1px); }}

.pill-btn {{
    display:inline-block;
    background:{C["surface2"]}; border:1px solid {C["border"]};
    border-radius:20px; padding:.3rem .8rem;
    font-size:.75rem; color:{C["slate"]}; cursor:pointer;
    margin:.2rem; transition:all .2s;
}}
.pill-btn:hover {{
    border-color:{C["indigo"]}; color:{C["indigo_lt"]};
    background:{C["indigo"]}15;
}}

/* ── Chat ─────────────────────────────────────────────────── */
.chat-wrap {{
    background:{C["surface"]};
    border:1px solid {C["border"]};
    border-radius:14px; padding:1rem 1.2rem;
    max-height:460px; overflow-y:auto;
    margin-bottom:.8rem;
}}
.chat-row {{ display:flex; align-items:flex-end; gap:.6rem; margin:.6rem 0; }}
.chat-row.user {{ flex-direction:row-reverse; }}
.chat-avatar {{
    width:30px; height:30px; border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    font-size:.8rem; flex-shrink:0;
}}
.avatar-bot  {{ background:linear-gradient(135deg,{C["indigo"]},{C["cyan"]}); }}
.avatar-user {{ background:linear-gradient(135deg,{C["emerald"]},{C["cyan"]}); }}
.chat-bubble {{
    max-width:78%; border-radius:14px;
    padding:.65rem 1rem; font-size:.85rem; line-height:1.55;
}}
.bubble-user {{
    background:linear-gradient(135deg,{C["indigo"]}cc,{C["indigo_lt"]}cc);
    color:#fff; border-radius:14px 14px 4px 14px;
}}
.bubble-bot  {{
    background:{C["surface2"]}; color:{C["text"]};
    border:1px solid {C["border"]}; border-radius:14px 14px 14px 4px;
}}
.chat-time {{ font-size:.65rem; color:{C["muted"]}; margin-top:.2rem; }}

/* ── Status dots ──────────────────────────────────────────── */
.status-dot {{
    display:inline-block;
    width:7px; height:7px; border-radius:50%;
    margin-right:.4rem; vertical-align:middle;
}}
.dot-green {{ background:{C["emerald"]}; box-shadow:0 0 6px {C["emerald"]}; }}
.dot-amber {{ background:{C["amber"]};   box-shadow:0 0 6px {C["amber"]}; }}

/* ── Data tables ──────────────────────────────────────────── */
.stDataFrame {{ border-radius:10px; overflow:hidden; border:1px solid {C["border"]}; }}
iframe[title="st_aggrid"] {{ border-radius:10px; }}

/* ── Download button ──────────────────────────────────────── */
.stDownloadButton > button {{
    background:{C["surface2"]}; color:{C["text"]};
    border:1px solid {C["border"]}; border-radius:9px;
    font-size:.78rem;
}}
.stDownloadButton > button:hover {{ border-color:{C["indigo"]}; }}

/* ── Welcome hero ─────────────────────────────────────────── */
.hero {{
    text-align:center; padding:5rem 2rem 4rem;
}}
.hero-badge {{
    display:inline-block;
    background:{C["indigo"]}20; border:1px solid {C["indigo"]}50;
    color:{C["indigo_lt"]}; border-radius:20px;
    padding:.3rem .9rem; font-size:.72rem; font-weight:600;
    letter-spacing:.06em; text-transform:uppercase; margin-bottom:1.2rem;
}}
.hero-title {{
    font-size:3rem; font-weight:800; color:{C["text"]};
    letter-spacing:-.04em; line-height:1.15; margin-bottom:1rem;
}}
.hero-title span {{
    background: linear-gradient(135deg,{C["indigo"]},{C["cyan"]});
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}}
.hero-sub {{
    font-size:1.05rem; color:{C["slate"]}; max-width:520px;
    margin:0 auto 2.2rem; line-height:1.65;
}}
.feature-grid {{
    display:grid; grid-template-columns:repeat(3,1fr);
    gap:1rem; max-width:700px; margin:2.5rem auto 0;
    text-align:left;
}}
.feature-card {{
    background:{C["surface"]}; border:1px solid {C["border"]};
    border-radius:12px; padding:1rem 1.1rem;
}}
.feature-icon {{ font-size:1.3rem; margin-bottom:.4rem; }}
.feature-name {{ font-size:.8rem; font-weight:600; color:{C["text"]}; }}
.feature-desc {{ font-size:.72rem; color:{C["muted"]}; margin-top:.2rem; }}

/* ── Sidebar logo block ───────────────────────────────────── */
.sb-logo {{
    background:linear-gradient({C["surface"]},{C["surface2"]});
    border-bottom:1px solid {C["border"]};
    padding:1.2rem 1rem 1rem;
    margin-bottom:.5rem;
}}
.sb-logo-mark {{
    background:linear-gradient(135deg,{C["indigo"]},{C["cyan"]});
    border-radius:10px; display:inline-flex;
    align-items:center; justify-content:center;
    width:34px; height:34px; font-size:1rem;
    vertical-align:middle; margin-right:.5rem;
}}
.sb-logo-text {{
    font-size:1rem; font-weight:700; vertical-align:middle;
    color:{C["text"]};
}}
.sb-logo-version {{
    display:inline-block; margin-left:.5rem;
    background:{C["indigo"]}25; color:{C["indigo_lt"]};
    border-radius:10px; padding:.08rem .45rem;
    font-size:.6rem; font-weight:600; vertical-align:middle;
}}
.sb-section-label {{
    font-size:.62rem; font-weight:700; color:{C["muted"]};
    text-transform:uppercase; letter-spacing:.12em;
    margin: .9rem 0 .4rem;
}}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────
def _init_state():
    for k, v in dict(
        df_raw=None, df=None, kpis=None, monthly=None,
        products=None, customers=None, context=None,
        assistant=None, chat_history=[],
    ).items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sb-logo">
        <span class="sb-logo-mark">📊</span>
        <span class="sb-logo-text">SalesIQ</span>
        <span class="sb-logo-version">v2.0</span>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="sb-section-label">Data Source</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Upload CSV", type=["csv"],
        help="Required: date · product · price · cost · quantity · customer",
        label_visibility="collapsed",
    )
    st.caption("date · product · price · cost · quantity · customer")

    st.markdown('<div class="sb-section-label">Quick Demo</div>', unsafe_allow_html=True)
    if st.button("📁  Load 25-row Sample Data", use_container_width=True):
        try:
            with open("small_sample.csv", "rb") as f:
                buf = io.BytesIO(f.read())
                buf.seek(0)
                st.session_state["_demo_bytes"] = buf
            st.session_state["_use_demo"] = True
            st.rerun()
        except FileNotFoundError:
            st.error("small_sample.csv not found in app directory")

    if st.button("⚡  Load 2 000-row Demo Dataset", use_container_width=True):
        from sample_data_generator import generate_dataset
        with st.spinner("Generating realistic demo data…"):
            demo_df = generate_dataset(2_000)
            buf = io.BytesIO()
            demo_df.to_csv(buf, index=False)
            buf.seek(0)
            st.session_state["_demo_bytes"] = buf
        st.session_state["_use_demo"] = True
        st.rerun()

    st.markdown('<div class="sb-section-label">AI Settings</div>', unsafe_allow_html=True)
    openai_key_input = st.text_input(
        "OpenAI API Key", value=os.getenv("OPENAI_API_KEY", ""),
        type="password", placeholder="sk-…  (optional)",
        label_visibility="collapsed",
        help="GPT-3.5-turbo or GPT-4o for richer answers. Leave blank for rule-based mode.",
    )
    if openai_key_input:
        os.environ["OPENAI_API_KEY"] = openai_key_input

    api_active = bool(os.getenv("OPENAI_API_KEY", "").strip())
    if api_active:
        st.markdown(
            f'<span class="status-dot dot-green"></span>'
            f'<span style="font-size:.75rem;color:#10b981">GPT connected</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<span class="status-dot dot-amber"></span>'
            f'<span style="font-size:.75rem;color:#f59e0b">Rule-based mode</span>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    if st.session_state["df"] is not None:
        df_info = st.session_state["df"]
        st.markdown(f"""
        <div style="background:{C["surface2"]};border:1px solid {C["border"]};
                    border-radius:10px;padding:.7rem .9rem;font-size:.73rem;">
            <div style="color:{C["muted"]};margin-bottom:.35rem;font-weight:600;
                        text-transform:uppercase;letter-spacing:.08em">Dataset Info</div>
            <div style="display:flex;justify-content:space-between;color:{C["text"]}">
                <span>Rows</span><span style="color:{C["indigo_lt"]};font-weight:600">{len(df_info):,}</span>
            </div>
            <div style="display:flex;justify-content:space-between;color:{C["text"]};margin-top:.25rem">
                <span>Products</span><span style="color:{C["cyan"]};font-weight:600">{df_info["product"].nunique()}</span>
            </div>
            <div style="display:flex;justify-content:space-between;color:{C["text"]};margin-top:.25rem">
                <span>Customers</span><span style="color:{C["emerald"]};font-weight:600">{df_info["customer"].nunique()}</span>
            </div>
            <div style="display:flex;justify-content:space-between;color:{C["text"]};margin-top:.25rem">
                <span>Date range</span>
                <span style="color:{C["slate"]};font-size:.68rem">
                    {df_info["date"].min().strftime("%b %Y")} – {df_info["date"].max().strftime("%b %Y")}
                </span>
            </div>
        </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────
source = None
if uploaded:
    source = uploaded
elif st.session_state.get("_use_demo") and st.session_state.get("_demo_bytes"):
    source = st.session_state["_demo_bytes"]
    st.session_state["_use_demo"] = False
elif st.session_state["df"] is None:
    # Auto-load sample data on first run if no data exists
    try:
        with open("small_sample.csv", "rb") as f:
            source = io.BytesIO(f.read())
    except FileNotFoundError:
        pass  # No sample file available, show welcome screen

if source is not None:
    try:
        connector = CSVConnector(source)
        raw_df    = connector.load()
        ok, err   = validate_dataframe(raw_df)
        if not ok:
            st.error(f"CSV validation failed: {err}")
        else:
            df      = load_and_clean(raw_df)
            context = build_context_summary(df)
            asst    = SalesAIAssistant(context)
            st.session_state.update(dict(
                df_raw=raw_df, df=df,
                kpis=total_kpis(df),
                monthly=monthly_summary(df),
                products=top_products(df),
                customers=top_customers(df),
                context=context,
                assistant=asst,
                chat_history=[],
            ))
    except Exception as exc:
        st.error(f"Error loading file: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Welcome screen
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state["df"] is None:
    st.markdown("""
    <div class="hero">
        <div class="hero-badge">AI-Powered · Real-time Analytics</div>
        <div class="hero-title">Turn Sales Data Into<br><span>Actionable Insights</span></div>
        <div class="hero-sub">
            Upload a CSV file or load the demo dataset to instantly explore
            revenue trends, profit margins, top-performing products, and
            get AI-powered business intelligence.
        </div>
        <div style="font-size:.8rem;color:#64748b">
            Required columns:
            <code style="background:#1e293b;padding:.15rem .4rem;border-radius:5px;">date</code>
            <code style="background:#1e293b;padding:.15rem .4rem;border-radius:5px;">product</code>
            <code style="background:#1e293b;padding:.15rem .4rem;border-radius:5px;">price</code>
            <code style="background:#1e293b;padding:.15rem .4rem;border-radius:5px;">cost</code>
            <code style="background:#1e293b;padding:.15rem .4rem;border-radius:5px;">quantity</code>
            <code style="background:#1e293b;padding:.15rem .4rem;border-radius:5px;">customer</code>
        </div>
        <div class="feature-grid">
            <div class="feature-card">
                <div class="feature-icon">📈</div>
                <div class="feature-name">Revenue & Profit Trends</div>
                <div class="feature-desc">Monthly breakdowns with MoM change and margin tracking</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🏆</div>
                <div class="feature-name">Product Intelligence</div>
                <div class="feature-desc">Rank products by revenue, profit and units sold</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🤖</div>
                <div class="feature-name">AI Chat Assistant</div>
                <div class="feature-desc">Ask plain-English questions about your sales data</div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Aliases
# ─────────────────────────────────────────────────────────────────────────────
df        = st.session_state["df"]
kpis      = st.session_state["kpis"]
monthly   = st.session_state["monthly"]
products  = st.session_state["products"]
customers = st.session_state["customers"]
assistant = st.session_state["assistant"]

# Best / worst month helpers
best_rev_month = monthly.loc[monthly["revenue"].idxmax(), "month_str"]
best_prf_month = monthly.loc[monthly["profit"].idxmax(),  "month_str"]


# ─────────────────────────────────────────────────────────────────────────────
# Top nav bar
# ─────────────────────────────────────────────────────────────────────────────
date_range = f"{df['date'].min().strftime('%b %d, %Y')} – {df['date'].max().strftime('%b %d, %Y')}"
st.markdown(f"""
<div class="topbar">
    <div class="topbar-logo">
        <div class="topbar-logo-icon">📊</div>
        <div>
            <div class="topbar-title">SalesIQ Dashboard</div>
            <div class="topbar-subtitle">AI Sales & Profit Analyzer</div>
        </div>
    </div>
    <div style="display:flex;gap:.6rem;align-items:center">
        <span class="topbar-badge">🗓 {date_range}</span>
        <span class="topbar-badge">{len(df):,} records</span>
    </div>
</div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tab layout
# ─────────────────────────────────────────────────────────────────────────────
tab_dash, tab_prod, tab_cust, tab_data, tab_chat = st.tabs([
    "  📈  Overview  ",
    "  🏆  Products  ",
    "  👥  Customers  ",
    "  🗃  Raw Data  ",
    "  🤖  AI Assistant  ",
])


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — Overview / Dashboard
# ═════════════════════════════════════════════════════════════════════════════
with tab_dash:

    # ── KPI cards ──────────────────────────────────────────────────────────
    prev_rev = monthly["revenue"].iloc[-2] if len(monthly) > 1 else None
    last_rev = monthly["revenue"].iloc[-1]
    rev_delta = ((last_rev - prev_rev) / prev_rev * 100) if prev_rev else None

    prev_prf = monthly["profit"].iloc[-2] if len(monthly) > 1 else None
    last_prf = monthly["profit"].iloc[-1]
    prf_delta = ((last_prf - prev_prf) / prev_prf * 100) if prev_prf else None

    def delta_html(val):
        if val is None:
            return ""
        arrow = "▲" if val >= 0 else "▼"
        cls   = "delta-up" if val >= 0 else "delta-down"
        return f'<span class="{cls}">{arrow} {abs(val):.1f}% MoM</span>'

    cards = [
        ("💰", "Total Revenue",   f"${kpis['total_revenue']:,.0f}",   delta_html(rev_delta),   C["indigo"]),
        ("📊", "Total Profit",    f"${kpis['total_profit']:,.0f}",    delta_html(prf_delta),   C["emerald"]),
        ("📐", "Profit Margin",   f"{kpis['profit_margin_pct']}%",    '<span class="kpi-sub">Overall margin</span>', C["cyan"]),
        ("🛒", "Total Orders",    f"{kpis['total_orders']:,}",        '<span class="kpi-sub">Line items</span>',     C["amber"]),
        ("💳", "Avg Order Value", f"${kpis['avg_order_value']:,.0f}", '<span class="kpi-sub">Per transaction</span>', C["rose"]),
    ]

    card_html = '<div class="kpi-grid">'
    for icon, label, value, footer, accent in cards:
        card_html += f"""
        <div class="kpi-card" style="--accent:{accent}">
            <div class="kpi-icon">{icon}</div>
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-footer">{footer}</div>
        </div>"""
    card_html += "</div>"
    st.markdown(card_html, unsafe_allow_html=True)

    # ── Main trend chart ───────────────────────────────────────────────────
    st.markdown("""<div class="section-header">
        <div class="section-dot"></div>
        <div class="section-title">Revenue &amp; Profit — Monthly Trend</div>
    </div>""", unsafe_allow_html=True)

    fig_trend = go.Figure()
    fig_trend.add_traces([
        go.Bar(
            x=monthly["month_str"], y=monthly["revenue"],
            name="Revenue", marker_color=C["indigo"],
            marker_line_width=0, opacity=0.9,
            hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.0f}<extra></extra>",
        ),
        go.Bar(
            x=monthly["month_str"], y=monthly["profit"],
            name="Profit", marker_color=C["cyan"],
            marker_line_width=0, opacity=0.9,
            hovertemplate="<b>%{x}</b><br>Profit: $%{y:,.0f}<extra></extra>",
        ),
        go.Scatter(
            x=monthly["month_str"], y=monthly["profit_margin_pct"],
            name="Margin %", yaxis="y2",
            line=dict(color=C["amber"], width=2.5),
            mode="lines+markers",
            marker=dict(size=6, symbol="circle", line=dict(color=C["bg"], width=2)),
            hovertemplate="<b>%{x}</b><br>Margin: %{y:.1f}%<extra></extra>",
        ),
    ])

    fig_trend.update_layout(
        **PLOTLY_BASE,
        barmode="group", height=400,
        bargap=0.25, bargroupgap=0.08,
        margin=MARGIN,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=11)),
        yaxis =dict(**AX, title="Amount ($)", tickprefix="$",
                    tickformat=",.0f"),
        yaxis2=dict(title=dict(text="Margin %", font=dict(color=C["amber"])),
                    overlaying="y", side="right",
                    showgrid=False, tickformat=".1f", ticksuffix="%",
                    tickfont=dict(color=C["amber"])),
        xaxis =dict(**AX, title=""),
    )
    st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
    st.plotly_chart(fig_trend, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Lower row: MoM change  +  Margin area ─────────────────────────────
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("""<div class="section-header">
            <div class="section-dot"></div>
            <div class="section-title">Month-over-Month Revenue Change</div>
        </div>""", unsafe_allow_html=True)

        mom_df = monthly.dropna(subset=["mom_revenue_chg_pct"])
        bar_colors = [C["emerald"] if v >= 0 else C["rose"]
                      for v in mom_df["mom_revenue_chg_pct"]]

        fig_mom = go.Figure(go.Bar(
            x=mom_df["month_str"], y=mom_df["mom_revenue_chg_pct"],
            marker_color=bar_colors, marker_line_width=0,
            text=[f"{v:+.1f}%" for v in mom_df["mom_revenue_chg_pct"]],
            textposition="outside", textfont=dict(size=10, color=C["slate"]),
            hovertemplate="<b>%{x}</b><br>Change: %{y:+.1f}%<extra></extra>",
        ))
        fig_mom.update_layout(
            **PLOTLY_BASE, height=290,
            margin=MARGIN,
            yaxis=dict(**AX, ticksuffix="%", title=""),
            xaxis=dict(**AX, title=""),
            showlegend=False,
        )
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.plotly_chart(fig_mom, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_r:
        st.markdown("""<div class="section-header">
            <div class="section-dot"></div>
            <div class="section-title">Profit Margin Trend (%)</div>
        </div>""", unsafe_allow_html=True)

        fig_margin = go.Figure()
        fig_margin.add_scatter(
            x=monthly["month_str"], y=monthly["profit_margin_pct"],
            mode="lines", name="Margin %",
            line=dict(color=C["indigo"], width=2.5),
            fill="tozeroy",
            fillcolor="rgba(99,102,241,0.13)",
            hovertemplate="<b>%{x}</b><br>Margin: %{y:.1f}%<extra></extra>",
        )
        fig_margin.add_scatter(
            x=monthly["month_str"], y=monthly["profit_margin_pct"],
            mode="markers", showlegend=False,
            marker=dict(size=7, color=C["indigo_lt"],
                        line=dict(color=C["bg"], width=2)),
        )
        fig_margin.update_layout(
            **PLOTLY_BASE, height=290,
            margin=MARGIN,
            yaxis=dict(**AX, ticksuffix="%", title=""),
            xaxis=dict(**AX, title=""),
            showlegend=False,
        )
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.plotly_chart(fig_margin, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Summary insight strip ──────────────────────────────────────────────
    tot_orders = kpis["total_orders"]
    st.markdown(f"""
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:.8rem;margin-top:.4rem">
        <div style="background:{C["surface"]};border:1px solid {C["border"]};border-radius:12px;
                    padding:.9rem 1.1rem;display:flex;align-items:center;gap:.7rem">
            <span style="font-size:1.5rem">🏅</span>
            <div>
                <div style="font-size:.68rem;color:{C["muted"]};text-transform:uppercase;letter-spacing:.08em">Best Revenue Month</div>
                <div style="font-size:.95rem;font-weight:700;color:{C["text"]}">{best_rev_month}</div>
            </div>
        </div>
        <div style="background:{C["surface"]};border:1px solid {C["border"]};border-radius:12px;
                    padding:.9rem 1.1rem;display:flex;align-items:center;gap:.7rem">
            <span style="font-size:1.5rem">💎</span>
            <div>
                <div style="font-size:.68rem;color:{C["muted"]};text-transform:uppercase;letter-spacing:.08em">Best Profit Month</div>
                <div style="font-size:.95rem;font-weight:700;color:{C["text"]}">{best_prf_month}</div>
            </div>
        </div>
        <div style="background:{C["surface"]};border:1px solid {C["border"]};border-radius:12px;
                    padding:.9rem 1.1rem;display:flex;align-items:center;gap:.7rem">
            <span style="font-size:1.5rem">📦</span>
            <div>
                <div style="font-size:.68rem;color:{C["muted"]};text-transform:uppercase;letter-spacing:.08em">Unique Products</div>
                <div style="font-size:.95rem;font-weight:700;color:{C["text"]}">{df["product"].nunique()} SKUs</div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — Products
# ═════════════════════════════════════════════════════════════════════════════
with tab_prod:
    st.markdown("""<div class="section-header">
        <div class="section-dot"></div>
        <div class="section-title">Product Performance Matrix</div>
    </div>""", unsafe_allow_html=True)

    col_left, col_right = st.columns([3, 2])

    with col_left:
        # Horizontal bar coloured by margin
        fig_prod = go.Figure(go.Bar(
            x=products.sort_values("total_revenue")["total_revenue"],
            y=products.sort_values("total_revenue")["product"],
            orientation="h",
            marker=dict(
                color=products.sort_values("total_revenue")["profit_margin_pct"],
                colorscale=[[0, C["rose"]], [0.5, C["amber"]], [1, C["emerald"]]],
                colorbar=dict(title=dict(text="Margin %", font=dict(color=C["slate"])),
                              ticksuffix="%",
                              tickfont=dict(color=C["slate"])),
                line=dict(width=0),
            ),
            hovertemplate=(
                "<b>%{y}</b><br>Revenue: $%{x:,.0f}"
                "<br>Margin: %{marker.color:.1f}%<extra></extra>"
            ),
            text=[f"${v:,.0f}" for v in products.sort_values("total_revenue")["total_revenue"]],
            textposition="outside",
            textfont=dict(size=10, color=C["slate"]),
        ))
        fig_prod.update_layout(
            **PLOTLY_BASE, height=420,
            margin=MARGIN,
            xaxis=dict(**AX, tickprefix="$", title="Revenue"),
            yaxis=dict(**AX, title=""),
            showlegend=False,
        )
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.plotly_chart(fig_prod, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        # Revenue vs Profit scatter bubble
        fig_scatter = px.scatter(
            products,
            x="total_revenue", y="profit_margin_pct",
            size="units_sold", color="total_profit",
            hover_name="product",
            color_continuous_scale=[[0, C["indigo"]], [1, C["emerald"]]],
            labels={"total_revenue": "Revenue ($)", "profit_margin_pct": "Margin %",
                    "total_profit": "Profit ($)"},
            size_max=40,
        )
        fig_scatter.update_layout(
            **PLOTLY_BASE, height=420,
            margin=MARGIN, legend=LEGEND,
            coloraxis_colorbar=dict(title=dict(text="Profit $", font=dict(color=C["slate"])),
                                    tickprefix="$",
                                    tickfont=dict(color=C["slate"])),
            xaxis=dict(**AX, tickprefix="$", title="Revenue ($)"),
            yaxis=dict(**AX, ticksuffix="%", title="Margin %"),
        )
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.plotly_chart(fig_scatter, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Donut + table row
    col_donut, col_tbl = st.columns([2, 3])

    with col_donut:
        st.markdown("""<div class="section-header">
            <div class="section-dot"></div>
            <div class="section-title">Units Sold Share</div>
        </div>""", unsafe_allow_html=True)
        fig_donut = go.Figure(go.Pie(
            labels=products["product"], values=products["units_sold"],
            hole=0.52,
            marker=dict(colors=px.colors.qualitative.Prism,
                        line=dict(color=C["bg"], width=2)),
            hovertemplate="<b>%{label}</b><br>Units: %{value:,}<br>Share: %{percent}<extra></extra>",
            textfont=dict(size=10),
        ))
        fig_donut.add_annotation(
            text=f"<b>{int(products['units_sold'].sum()):,}</b><br><span style='font-size:10px'>units</span>",
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False,
            font=dict(size=16, color=C["text"]),
        )
        fig_donut.update_layout(
            **PLOTLY_BASE, height=320,
            legend=dict(font=dict(size=10), orientation="v"),
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.plotly_chart(fig_donut, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_tbl:
        st.markdown("""<div class="section-header">
            <div class="section-dot"></div>
            <div class="section-title">Top Products Table</div>
        </div>""", unsafe_allow_html=True)
        display_prod = (
            products[["product", "total_revenue", "total_profit",
                       "units_sold", "profit_margin_pct"]]
            .rename(columns={
                "product": "Product", "total_revenue": "Revenue ($)",
                "total_profit": "Profit ($)", "units_sold": "Units Sold",
                "profit_margin_pct": "Margin %",
            })
        )
        st.dataframe(
            display_prod.style
            .format({"Revenue ($)": "${:,.0f}", "Profit ($)": "${:,.0f}",
                     "Units Sold": "{:,.0f}", "Margin %": "{:.1f}%"})
            .background_gradient(subset=["Revenue ($)"], cmap="Blues")
            .highlight_max(subset=["Margin %"], color="#10b98133"),
            use_container_width=True, height=320,
        )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — Customers
# ═════════════════════════════════════════════════════════════════════════════
with tab_cust:
    st.markdown("""<div class="section-header">
        <div class="section-dot"></div>
        <div class="section-title">Customer Revenue Analysis</div>
    </div>""", unsafe_allow_html=True)

    col_bar, col_scatter = st.columns(2)

    with col_bar:
        fig_cust_bar = go.Figure(go.Bar(
            x=customers.sort_values("total_revenue")["total_revenue"],
            y=customers.sort_values("total_revenue")["customer"],
            orientation="h",
            marker=dict(
                color=customers.sort_values("total_revenue")["total_revenue"],
                colorscale=[[0, C["indigo"]], [1, C["cyan"]]],
                line=dict(width=0),
            ),
            text=[f"${v:,.0f}" for v in customers.sort_values("total_revenue")["total_revenue"]],
            textposition="outside", textfont=dict(size=10, color=C["slate"]),
            hovertemplate="<b>%{y}</b><br>Revenue: $%{x:,.0f}<extra></extra>",
        ))
        fig_cust_bar.update_layout(
            **PLOTLY_BASE, height=400,
            margin=MARGIN,
            xaxis=dict(**AX, tickprefix="$", title="Revenue"),
            yaxis=dict(**AX, title=""),
            showlegend=False,
        )
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.plotly_chart(fig_cust_bar, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_scatter:
        fig_cust_scatter = px.scatter(
            customers,
            x="orders", y="total_revenue",
            size="avg_order_value", color="total_profit",
            hover_name="customer",
            color_continuous_scale=[[0, C["indigo"]], [1, C["emerald"]]],
            labels={"orders": "Number of Orders", "total_revenue": "Total Revenue ($)",
                    "avg_order_value": "Avg Order ($)", "total_profit": "Profit ($)"},
            size_max=40,
        )
        fig_cust_scatter.update_layout(
            **PLOTLY_BASE, height=400,
            margin=MARGIN, legend=LEGEND,
            xaxis=dict(**AX, title="Number of Orders"),
            yaxis=dict(**AX, tickprefix="$", title="Total Revenue ($)"),
            coloraxis_colorbar=dict(title=dict(text="Profit $", font=dict(color=C["slate"])),
                                    tickprefix="$",
                                    tickfont=dict(color=C["slate"])),
        )
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.plotly_chart(fig_cust_scatter, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("""<div class="section-header">
        <div class="section-dot"></div>
        <div class="section-title">Top Customers Table</div>
    </div>""", unsafe_allow_html=True)

    display_cust = (
        customers[["customer", "total_revenue", "total_profit", "orders", "avg_order_value"]]
        .rename(columns={
            "customer": "Customer", "total_revenue": "Revenue ($)",
            "total_profit": "Profit ($)", "orders": "Orders",
            "avg_order_value": "Avg Order ($)",
        })
    )
    st.dataframe(
        display_cust.style
        .format({"Revenue ($)": "${:,.0f}", "Profit ($)": "${:,.0f}",
                 "Avg Order ($)": "${:,.2f}"})
        .background_gradient(subset=["Revenue ($)"], cmap="Greens")
        .highlight_max(subset=["Avg Order ($)"], color="#06b6d433"),
        use_container_width=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — Raw Data
# ═════════════════════════════════════════════════════════════════════════════
with tab_data:
    show_cols = ["date", "product", "customer", "price", "cost",
                 "quantity", "revenue", "profit"]

    # Stat row
    c1, c2, c3, c4 = st.columns(4)
    for col, label, val in [
        (c1, "Total Rows",      f"{len(df):,}"),
        (c2, "Columns",         str(len(show_cols))),
        (c3, "Missing Values",  str(df[show_cols].isnull().sum().sum())),
        (c4, "Date Range",      f"{df['date'].min().strftime('%b %Y')} – {df['date'].max().strftime('%b %Y')}"),
    ]:
        col.markdown(f"""
        <div style="background:{C["surface"]};border:1px solid {C["border"]};
                    border-radius:10px;padding:.7rem 1rem;text-align:center">
            <div style="font-size:.65rem;color:{C["muted"]};text-transform:uppercase;
                        letter-spacing:.1em;margin-bottom:.3rem">{label}</div>
            <div style="font-size:1.05rem;font-weight:700;color:{C["text"]}">{val}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("""<div class="section-header" style="margin-top:1rem">
        <div class="section-dot"></div>
        <div class="section-title">Processed Dataset</div>
    </div>""", unsafe_allow_html=True)

    st.dataframe(df[show_cols].head(500), use_container_width=True, height=460)

    col_dl, col_info = st.columns([1, 3])
    csv_bytes = df[show_cols].to_csv(index=False).encode()
    col_dl.download_button(
        "⬇ Download Processed CSV", data=csv_bytes,
        file_name="processed_sales.csv", mime="text/csv",
    )
    col_info.markdown(
        f'<span style="font-size:.8rem;color:{C["muted"]}">Showing first 500 of {len(df):,} rows</span>',
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 5 — AI Assistant
# ═════════════════════════════════════════════════════════════════════════════
with tab_chat:

    # ── process a suggestion-button click queued from a previous run ────────
    if st.session_state.get("_pending_q"):
        _pq = st.session_state.pop("_pending_q")
        st.session_state["chat_history"].append({"role": "user", "content": _pq})
        try:
            _reply = assistant.chat(_pq)
        except Exception as _e:
            _reply = f"Sorry, I encountered an error: {_e}"
        st.session_state["chat_history"].append({"role": "assistant", "content": _reply})

    col_chat, col_ctx = st.columns([3, 2])

    with col_chat:
        # ── Status banner ───────────────────────────────────────────────────
        if api_active:
            st.markdown(f"""
            <div style="background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.3);
                        border-radius:10px;padding:.55rem 1rem;margin-bottom:.8rem;
                        display:flex;align-items:center;gap:.5rem">
                <span class="status-dot dot-green"></span>
                <span style="font-size:.78rem;color:{C["emerald"]};font-weight:600">GPT Connected</span>
                <span style="font-size:.72rem;color:{C["muted"]};margin-left:.3rem">Full conversational AI enabled</span>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);
                        border-radius:10px;padding:.55rem 1rem;margin-bottom:.8rem;
                        display:flex;align-items:center;gap:.5rem">
                <span class="status-dot dot-amber"></span>
                <span style="font-size:.78rem;color:{C["amber"]};font-weight:600">Rule-based Mode</span>
                <span style="font-size:.72rem;color:{C["muted"]};margin-left:.3rem">Add OpenAI key in sidebar for GPT answers</span>
            </div>""", unsafe_allow_html=True)

        # ── Suggestion buttons ──────────────────────────────────────────────
        st.markdown("""<div class="section-header">
            <div class="section-dot"></div>
            <div class="section-title">Quick Questions</div>
        </div>""", unsafe_allow_html=True)

        suggestions = [
            "Which month had the highest profit?",
            "Which product sells the most?",
            "Who is the top customer?",
            "What is the total revenue?",
            "Show the monthly revenue trend.",
            "Why did revenue change between months?",
        ]
        btn_cols = st.columns(3)
        for i, q in enumerate(suggestions):
            if btn_cols[i % 3].button(q, key=f"sug_{i}", use_container_width=True):
                # Queue question; processing happens at top of tab on next run
                st.session_state["_pending_q"] = q
                st.rerun()

        # ── Chat history via native st.chat_message ─────────────────────────
        st.markdown("""<div class="section-header">
            <div class="section-dot"></div>
            <div class="section-title">Conversation</div>
        </div>""", unsafe_allow_html=True)

        if not st.session_state["chat_history"]:
            st.markdown(
                f'<div style="text-align:center;padding:2rem;color:{C["muted"]};'
                f'font-size:.85rem;background:{C["surface"]};border:1px solid {C["border"]};'
                f'border-radius:12px">'
                f'<div style="font-size:2rem;margin-bottom:.5rem">🤖</div>'
                f'Ask me anything about your sales dataset.<br>'
                f'Click a quick question above or type below.</div>',
                unsafe_allow_html=True,
            )
        else:
            for msg in st.session_state["chat_history"]:
                avatar = "🤖" if msg["role"] == "assistant" else "👤"
                with st.chat_message(msg["role"], avatar=avatar):
                    st.markdown(msg["content"])

        # ── st.chat_input — does NOT reset tab selection on submit ──────────
        if prompt := st.chat_input("Ask a business question about your data…"):
            st.session_state["chat_history"].append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Analyzing…"):
                    try:
                        reply = assistant.chat(prompt)
                    except Exception as e:
                        reply = f"Sorry, I hit an error: {e}"
                st.markdown(reply)
            st.session_state["chat_history"].append({"role": "assistant", "content": reply})

        if st.session_state["chat_history"]:
            if st.button("🗑 Clear conversation"):
                st.session_state["chat_history"] = []
                if assistant:
                    assistant.reset_history()
                st.rerun()

    # ── Right panel: dataset context ────────────────────────────────────────
    with col_ctx:
        st.markdown("""<div class="section-header">
            <div class="section-dot"></div>
            <div class="section-title">What the AI Sees</div>
        </div>""", unsafe_allow_html=True)

        st.markdown(
            f'<div style="background:{C["surface"]};border:1px solid {C["border"]};'
            f'border-radius:12px;padding:.8rem 1rem">'
            f'<div style="font-size:.7rem;color:{C["muted"]};margin-bottom:.5rem;'
            f'text-transform:uppercase;letter-spacing:.08em;font-weight:600">'
            f'Dataset Summary Injected into System Prompt</div>'
            f'<div style="font-size:.72rem;color:{C["slate"]};line-height:1.6;'
            f'max-height:480px;overflow-y:auto;white-space:pre-wrap;font-family:monospace">'
            f'{st.session_state["context"]}</div></div>',
            unsafe_allow_html=True,
        )

