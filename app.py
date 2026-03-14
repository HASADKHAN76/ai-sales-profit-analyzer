"""
app.py — RetailBrain AI  (Professional Retail & E-commerce SaaS)
Run with:  streamlit run app.py
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

import auth
import business_management as bm
import coaching_management as coaching
import database as db
import gym_management as gym
import inventory as inv
import products_services as ps
import reports
import transactions as txn
from admin_panel import render_admin_panel
from ai_assistant import SalesAIAssistant
from app_config import get_setting
from app_logging import log_exception
from auth_page import render_auth_page, render_user_sidebar
from profile_page import render_profile_page
from ui_utils import show_friendly_error

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RetailBrain AI — SaaS",
    page_icon="🧠",
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
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
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

/* ── Chat ─────────────────────────────────────────────────── */
.chat-wrap {{
    background:{C["surface"]};
    border:1px solid {C["border"]};
    border-radius:14px; padding:1rem 1.2rem;
    max-height:460px; overflow-y:auto;
    margin-bottom:.8rem;
}}

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

/* ── Download button ──────────────────────────────────────── */
.stDownloadButton > button {{
    background:{C["surface2"]}; color:{C["text"]};
    border:1px solid {C["border"]}; border-radius:9px;
    font-size:.78rem;
}}
.stDownloadButton > button:hover {{ border-color:{C["indigo"]}; }}

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
    defaults = {
        "auth_token": None,
        "user": None,
        "selected_business_id": None,
        "ai_assistant": None,
        "ai_assistant_signature": None,
        "chat_history": [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

_init_state()
db.init_db()


# ─────────────────────────────────────────────────────────────────────────────
# Early helpers needed during top-level sidebar rendering
# ─────────────────────────────────────────────────────────────────────────────
def _sync_runtime_setting(key: str, value: str) -> None:
    """Keep runtime environment settings in sync with sidebar inputs."""
    cleaned = value.strip()
    if cleaned:
        os.environ[key] = cleaned
    else:
        os.environ.pop(key, None)


# ─────────────────────────────────────────────────────────────────────────────
# Authentication Gate
# ─────────────────────────────────────────────────────────────────────────────
if not render_auth_page():
    st.stop()

current_user = st.session_state["user"]
user_businesses = db.get_user_businesses(current_user["id"])

if not user_businesses:
    bm.render_business_setup()
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sb-logo">
        <span class="sb-logo-mark">🧠</span>
        <span class="sb-logo-text">RetailBrain</span>
        <span class="sb-logo-version">AI</span>
    </div>""", unsafe_allow_html=True)

    render_user_sidebar(current_user)

    st.markdown('<div class="sb-section-label">Business</div>', unsafe_allow_html=True)
    selected_business_id = bm.render_business_selector(current_user["id"])

    st.markdown('<div class="sb-section-label">Navigation</div>', unsafe_allow_html=True)
    nav = st.radio(
        "Go to",
        [
            "📈 Dashboard",
            "📦 Products / Inventory",
            "👥 Members",
            "💳 Transactions",
            "📊 Analytics",
            "🤖 AI Assistant",
            "📋 Reports",
            "⚙️ Settings",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown('<div class="sb-section-label">AI Settings</div>', unsafe_allow_html=True)
    gemini_key_input = st.text_input(
        "Gemini API Key",
        value=get_setting("GEMINI_API_KEY", ""),
        type="password",
        placeholder="AIza…  (recommended)",
        label_visibility="collapsed",
        help="Free tier: 60 req/min. Get key at makersuite.google.com",
    )
    _sync_runtime_setting("GEMINI_API_KEY", gemini_key_input)

    openai_key_input = st.text_input(
        "OpenAI API Key",
        value=get_setting("OPENAI_API_KEY", ""),
        type="password",
        placeholder="sk-…  (optional)",
        label_visibility="collapsed",
        help="GPT-3.5/4o for richer AI answers. Leave blank for rule-based mode.",
    )
    _sync_runtime_setting("OPENAI_API_KEY", openai_key_input)

    gemini_active = bool(get_setting("GEMINI_API_KEY", "").strip())
    openai_active = bool(get_setting("OPENAI_API_KEY", "").strip())
    if gemini_active:
        st.markdown(
            f'<span class="status-dot dot-green"></span>'
            f'<span style="font-size:.75rem;color:{C["emerald"]}">Gemini AI connected</span>',
            unsafe_allow_html=True,
        )
    elif openai_active:
        st.markdown(
            f'<span class="status-dot dot-green"></span>'
            f'<span style="font-size:.75rem;color:{C["emerald"]}">GPT connected</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<span class="status-dot dot-amber"></span>'
            f'<span style="font-size:.75rem;color:{C["amber"]}">Rule-based mode</span>',
            unsafe_allow_html=True,
        )

if not selected_business_id:
    st.error("Please select a business.")
    st.stop()

user_role = bm.check_business_access(current_user["id"], selected_business_id)
if not user_role:
    st.error("You do not have access to this business.")
    st.stop()

business = bm.get_current_business_info()
if not business:
    st.error("Business context unavailable.")
    st.stop()

st.caption(f"{business['name']} | Type: {business['business_type'].title()} | Role: {user_role.title()}")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _render_topbar(title: str, subtitle: str) -> None:
    st.markdown(f"""
    <div class="topbar">
        <div class="topbar-logo">
            <div class="topbar-logo-icon">🧠</div>
            <div>
                <div class="topbar-title">{title}</div>
                <div class="topbar-subtitle">{subtitle}</div>
            </div>
        </div>
        <div style="display:flex;gap:.6rem;align-items:center">
            <span class="topbar-badge">{business['name']}</span>
            <span class="topbar-badge">{business['business_type'].title()}</span>
            <span class="topbar-badge">{user_role.title()}</span>
        </div>
    </div>""", unsafe_allow_html=True)


def _build_ai_context(business_id: int) -> str:
    business_info = bm.get_current_business_info() or {}
    summary = db.get_business_revenue_summary(business_id)
    top_items = db.get_top_products_services(business_id, limit=5)

    context_parts = [
        f"Business: {business_info.get('name', '')} ({business_info.get('business_type', '')})",
        f"Total Revenue: ${summary['total_revenue']:,.2f}",
        f"Total Profit: ${summary['total_profit']:,.2f}",
        f"Profit Margin: {summary['profit_margin']:.1f}%",
        f"Total Transactions: {summary['total_transactions']:,}",
    ]
    for item in top_items[:3]:
        context_parts.append(f"Top Item: {item['name']} (${item['total_revenue']:,.0f})")

    return "\n".join(context_parts)


def _get_ai_assistant(business_id: int) -> SalesAIAssistant:
    context_summary = _build_ai_context(business_id)
    signature = (
        business_id,
        context_summary,
        get_setting("GEMINI_API_KEY", ""),
        get_setting("OPENAI_API_KEY", ""),
    )

    if st.session_state.get("ai_assistant_signature") != signature:
        st.session_state["ai_assistant"] = SalesAIAssistant(context_summary)
        st.session_state["ai_assistant_signature"] = signature
        st.session_state["chat_history"] = []

    return st.session_state["ai_assistant"]


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────
def _render_dashboard(business_id: int) -> None:
    _render_topbar("Dashboard", "Metrics, charts, and quick business snapshot")

    sales_summary = txn.get_business_sales_summary(business_id)
    inventory_summary = ps.get_business_inventory_summary(business_id)
    alerts_summary = inv.get_inventory_alerts_count(business_id)

    cards = [
        ("💰", "Today Revenue",      f"${sales_summary['today_revenue']:,.0f}",      C["indigo"]),
        ("📊", "Month Revenue",      f"${sales_summary['month_revenue']:,.0f}",      C["emerald"]),
        ("📐", "Month Profit",       f"${sales_summary['month_profit']:,.0f}",       C["cyan"]),
        ("🔔", "Open Alerts",        f"{alerts_summary['total_alerts']}",            C["amber"]),
        ("🛒", "Today Transactions", f"{sales_summary['today_transactions']}",       C["rose"]),
    ]

    card_html = '<div class="kpi-grid">'
    for icon, label, value, accent in cards:
        card_html += f"""
        <div class="kpi-card" style="--accent:{accent}">
            <div class="kpi-icon">{icon}</div>
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>"""
    card_html += "</div>"
    st.markdown(card_html, unsafe_allow_html=True)

    # Revenue chart + snapshot
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("""<div class="section-header">
            <div class="section-dot"></div>
            <div class="section-title">Daily Revenue — Last 30 Days</div>
        </div>""", unsafe_allow_html=True)

        daily_data = db.get_daily_revenue_data(business_id, days=30)
        if daily_data:
            df = pd.DataFrame(daily_data)
            fig = px.line(df, x="date", y="revenue", markers=True,
                          color_discrete_sequence=[C["indigo"]])
            fig.update_layout(
                **PLOTLY_BASE, height=320, margin=MARGIN,
                xaxis=dict(**AX, title=""),
                yaxis=dict(**AX, tickprefix="$", title="Revenue"),
            )
            st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No transaction data available yet. Record sales in the Transactions page.")

    with col_right:
        st.markdown("""<div class="section-header">
            <div class="section-dot"></div>
            <div class="section-title">Snapshot</div>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:{C["surface"]};border:1px solid {C["border"]};
                    border-radius:12px;padding:1rem 1.2rem">
            <div style="display:flex;justify-content:space-between;color:{C["text"]};margin-bottom:.6rem">
                <span style="color:{C["muted"]}">Products/Services</span>
                <span style="font-weight:700;color:{C["indigo_lt"]}">{inventory_summary['total_items']}</span>
            </div>
            <div style="display:flex;justify-content:space-between;color:{C["text"]};margin-bottom:.6rem">
                <span style="color:{C["muted"]}">Low Stock Items</span>
                <span style="font-weight:700;color:{C["amber"]}">{inventory_summary['low_stock_count']}</span>
            </div>
            <div style="display:flex;justify-content:space-between;color:{C["text"]}">
                <span style="color:{C["muted"]}">Today's Transactions</span>
                <span style="font-weight:700;color:{C["emerald"]}">{sales_summary['today_transactions']}</span>
            </div>
        </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Analytics
# ─────────────────────────────────────────────────────────────────────────────
def _render_analytics(business_id: int) -> None:
    _render_topbar("Analytics", "Revenue and profitability trends")

    period = st.selectbox("Period", [7, 30, 90, 365], index=1)
    summary = db.get_business_revenue_summary(
        business_id,
        start_date=(datetime.now() - timedelta(days=period)).date().isoformat(),
    )

    cards = [
        ("💰", "Revenue",      f"${summary['total_revenue']:,.0f}",       C["indigo"]),
        ("📊", "Profit",       f"${summary['total_profit']:,.0f}",        C["emerald"]),
        ("📐", "Margin",       f"{summary['profit_margin']:.1f}%",        C["cyan"]),
        ("🛒", "Transactions", f"{summary['total_transactions']:,}",      C["amber"]),
    ]

    card_html = '<div class="kpi-grid">'
    for icon, label, value, accent in cards:
        card_html += f"""
        <div class="kpi-card" style="--accent:{accent}">
            <div class="kpi-icon">{icon}</div>
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>"""
    card_html += "</div>"
    st.markdown(card_html, unsafe_allow_html=True)

    st.markdown("""<div class="section-header">
        <div class="section-dot"></div>
        <div class="section-title">Top Products / Services</div>
    </div>""", unsafe_allow_html=True)

    top_products = db.get_top_products_services(business_id, limit=10)
    if top_products:
        df = pd.DataFrame(top_products)
        fig = go.Figure(go.Bar(
            x=df["total_revenue"],
            y=df["name"],
            orientation="h",
            marker=dict(
                color=df["total_revenue"],
                colorscale=[[0, C["indigo"]], [1, C["cyan"]]],
                line=dict(width=0),
            ),
            text=[f"${v:,.0f}" for v in df["total_revenue"]],
            textposition="outside",
            textfont=dict(size=10, color=C["slate"]),
            hovertemplate="<b>%{y}</b><br>Revenue: $%{x:,.0f}<extra></extra>",
        ))
        fig.update_layout(
            **PLOTLY_BASE, height=380,
            margin=MARGIN,
            xaxis=dict(**AX, tickprefix="$", title="Revenue"),
            yaxis=dict(**AX, title=""),
            showlegend=False,
        )
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No product/service data available yet.")


# ─────────────────────────────────────────────────────────────────────────────
# AI Insights
# ─────────────────────────────────────────────────────────────────────────────
def _render_ai_insights(business_id: int) -> None:
    st.markdown("""<div class="section-header">
        <div class="section-dot"></div>
        <div class="section-title">AI Insights</div>
    </div>""", unsafe_allow_html=True)
    assistant = _get_ai_assistant(business_id)

    gemini_active = bool(get_setting("GEMINI_API_KEY", "").strip())
    openai_active = bool(get_setting("OPENAI_API_KEY", "").strip())
    if gemini_active or openai_active:
        st.markdown(f"""
        <div style="background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.3);
                    border-radius:10px;padding:.55rem 1rem;margin-bottom:.8rem;
                    display:flex;align-items:center;gap:.5rem">
            <span class="status-dot dot-green"></span>
            <span style="font-size:.78rem;color:{C["emerald"]};font-weight:600">AI provider configured</span>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);
                    border-radius:10px;padding:.55rem 1rem;margin-bottom:.8rem;
                    display:flex;align-items:center;gap:.5rem">
            <span class="status-dot dot-amber"></span>
            <span style="font-size:.78rem;color:{C["amber"]};font-weight:600">Rule-based mode</span>
            <span style="font-size:.72rem;color:{C["muted"]};margin-left:.3rem">Add API key in Settings for AI answers</span>
        </div>""", unsafe_allow_html=True)

    questions = [
        "What is my best-selling item?",
        "How can I improve profit margin?",
        "What trends should I act on this month?",
    ]
    cols = st.columns(3)
    for idx, question in enumerate(questions):
        if cols[idx].button(question, key=f"quick_ai_{idx}", use_container_width=True):
            st.session_state["chat_history"].append({"role": "user", "content": question})
            try:
                answer = assistant.chat(question)
            except Exception as exc:
                log_exception("ai.quick_question", exc)
                answer = "I could not generate insights right now. Please try again shortly."
            st.session_state["chat_history"].append({"role": "assistant", "content": answer})
            st.rerun()

    for msg in st.session_state.get("chat_history", []):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Ask about revenue, operations, growth, or risk")
    if prompt:
        st.session_state["chat_history"].append({"role": "user", "content": prompt})
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                try:
                    answer = assistant.chat(prompt)
                except Exception as exc:
                    log_exception("ai.chat", exc)
                    answer = "I could not generate insights right now. Please try again shortly."
                st.markdown(answer)
        st.session_state["chat_history"].append({"role": "assistant", "content": answer})


# ─────────────────────────────────────────────────────────────────────────────
# Products / Inventory
# ─────────────────────────────────────────────────────────────────────────────
def _render_products_inventory(business_type: str) -> None:
    _render_topbar("Products / Inventory", "Catalog, stock levels, and service offerings")

    if business_type in {"gym", "coaching"}:
        ps.render_products_services_page()
        return

    tab_products, tab_inventory = st.tabs(["Products", "Inventory"])
    with tab_products:
        ps.render_products_services_page()
    with tab_inventory:
        inv.render_inventory_page()


# ─────────────────────────────────────────────────────────────────────────────
# Members
# ─────────────────────────────────────────────────────────────────────────────
def _render_members(business_type: str) -> None:
    _render_topbar("Members", "Membership and enrollment management")

    if business_type == "gym":
        gym.render_gym_management_page()
        return

    if business_type == "coaching":
        coaching.render_coaching_management_page()
        return

    st.info("Members module is not required for this business type. Use Transactions to manage customer records.")


# ═════════════════════════════════════════════════════════════════════════════
# Page routing
# ═════════════════════════════════════════════════════════════════════════════
try:
    if nav == "📈 Dashboard":
        _render_dashboard(selected_business_id)
    elif nav == "📦 Products / Inventory":
        _render_products_inventory(business["business_type"])
    elif nav == "👥 Members":
        _render_members(business["business_type"])
    elif nav == "💳 Transactions":
        _render_topbar("Transactions", "Sales entries, receipts, and payment records")
        txn.render_sales_page()
    elif nav == "📊 Analytics":
        _render_analytics(selected_business_id)
    elif nav == "🤖 AI Assistant":
        _render_topbar("AI Assistant", "Ask questions about your business data")
        _render_ai_insights(selected_business_id)
    elif nav == "📋 Reports":
        _render_topbar("Reports", "Downloadable records and summaries")
        reports.render_reports_page()
    elif nav == "⚙️ Settings":
        _render_topbar("Settings", "Business configuration and account controls")
        if auth.is_admin(current_user):
            render_admin_panel()
        elif user_role in {"owner", "admin"}:
            bm.render_business_settings()
        else:
            st.info("You can manage your account settings below.")
        render_profile_page(current_user)
except Exception as exc:
    show_friendly_error(
        "Something went wrong while loading this page. Please refresh and try again.",
        "app.routing",
        exc,
    )
