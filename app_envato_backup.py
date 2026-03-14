"""Production-ready Streamlit SaaS app entrypoint with Envato-inspired UI skin."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
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

st.set_page_config(
    page_title="RetailBrain SaaS",
    page_icon="RB",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _inject_envato_assets() -> None:
    """Load Envato-inspired CSS/JS assets adapted for Streamlit."""
    base_dir = Path(__file__).resolve().parent
    css_path = base_dir / "theme" / "envato_streamlit.css"
    js_path = base_dir / "theme" / "envato_streamlit.js"

    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

    if js_path.exists():
        js_payload = js_path.read_text(encoding="utf-8")
        components.html(f"<script>{js_payload}</script>", height=0)


def _init_state() -> None:
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


def _render_topbar(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="rb-topbar">
            <div>
                <div class="rb-topbar-title">{title}</div>
                <div class="rb-topbar-sub">{subtitle}</div>
            </div>
            <span class="rb-pill">Live</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _sync_runtime_setting(key: str, value: str) -> None:
    """Keep runtime environment settings in sync with sidebar inputs."""
    cleaned = value.strip()
    if cleaned:
        os.environ[key] = cleaned
    else:
        os.environ.pop(key, None)


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


def _render_dashboard(business_id: int) -> None:
    _render_topbar("Dashboard", "Envato-style metrics, charts, and quick business snapshot")

    sales_summary = txn.get_business_sales_summary(business_id)
    inventory_summary = ps.get_business_inventory_summary(business_id)
    alerts_summary = inv.get_inventory_alerts_count(business_id)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"<div class='rb-card rb-kpi'><div class='rb-kpi-label'>Today Revenue</div><div class='rb-kpi-value'>${sales_summary['today_revenue']:,.0f}</div><div class='rb-kpi-delta'>Updated now</div></div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"<div class='rb-card rb-kpi'><div class='rb-kpi-label'>Month Revenue</div><div class='rb-kpi-value'>${sales_summary['month_revenue']:,.0f}</div></div>",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"<div class='rb-card rb-kpi'><div class='rb-kpi-label'>Month Profit</div><div class='rb-kpi-value'>${sales_summary['month_profit']:,.0f}</div></div>",
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f"<div class='rb-card rb-kpi'><div class='rb-kpi-label'>Open Alerts</div><div class='rb-kpi-value'>{alerts_summary['total_alerts']}</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown(" ")
    col_left, col_right = st.columns([2, 1])

    with col_left:
        daily_data = db.get_daily_revenue_data(business_id, days=30)
        if daily_data:
            df = pd.DataFrame(daily_data)
            fig = px.line(df, x="date", y="revenue", markers=True, color_discrete_sequence=["#4f46e5"])
            fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No transaction data available yet.")

    with col_right:
        st.markdown('<div class="rb-content-title">Snapshot</div>', unsafe_allow_html=True)
        st.write(f"Products/Services: **{inventory_summary['total_items']}**")
        st.write(f"Low Stock Items: **{inventory_summary['low_stock_count']}**")
        st.write(f"Today's Transactions: **{sales_summary['today_transactions']}**")


def _render_analytics(business_id: int) -> None:
    _render_topbar("Analytics", "Revenue and profitability trends")

    period = st.selectbox("Period", [7, 30, 90, 365], index=1)
    summary = db.get_business_revenue_summary(
        business_id,
        start_date=(datetime.now() - timedelta(days=period)).date().isoformat(),
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Revenue", f"${summary['total_revenue']:,.0f}")
    col2.metric("Profit", f"${summary['total_profit']:,.0f}")
    col3.metric("Margin", f"{summary['profit_margin']:.1f}%")
    col4.metric("Transactions", f"{summary['total_transactions']:,}")

    top_products = db.get_top_products_services(business_id, limit=10)
    if top_products:
        df = pd.DataFrame(top_products)
        fig = px.bar(df.head(8), x="name", y="total_revenue", color_discrete_sequence=["#4f46e5"])
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)


def _render_ai_insights(business_id: int) -> None:
    st.markdown('<div class="rb-content-title">AI Insights</div>', unsafe_allow_html=True)
    assistant = _get_ai_assistant(business_id)

    gemini_active = bool(get_setting("GEMINI_API_KEY", "").strip())
    openai_active = bool(get_setting("OPENAI_API_KEY", "").strip())
    if gemini_active or openai_active:
        st.success("AI provider configured.")
    else:
        st.info("AI keys not configured. Running in built-in insights mode.")

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


def _render_members(business_type: str) -> None:
    _render_topbar("Members", "Membership and enrollment management")

    if business_type == "gym":
        gym.render_gym_management_page()
        return

    if business_type == "coaching":
        coaching.render_coaching_management_page()
        return

    st.info("Members module is not required for this business type. Use Transactions to manage customer records.")


def main() -> None:
    _inject_envato_assets()
    _init_state()
    db.init_db()

    if not render_auth_page():
        st.stop()

    current_user = st.session_state["user"]
    user_businesses = db.get_user_businesses(current_user["id"])

    if not user_businesses:
        bm.render_business_setup()
        st.stop()

    with st.sidebar:
        st.markdown(
            """
            <div class="rb-sidebar-logo">
                <span class="rb-logo-mark">RB</span>
                <div>
                    <div class="rb-logo-text">RetailBrain</div>
                    <div style="font-size:.68rem;opacity:.8">Reback Envato Skin</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        render_user_sidebar(current_user)
        st.markdown("### Business")
        selected_business_id = bm.render_business_selector(current_user["id"])

        st.markdown("### Navigation")
        nav = st.radio(
            "Go to",
            [
                "Dashboard",
                "Products / Inventory",
                "Members",
                "Transactions",
                "Analytics",
                "AI Assistant",
                "Reports",
                "Settings",
            ],
            label_visibility="collapsed",
        )

        st.markdown("---")
        st.markdown("### AI Settings")
        gemini_key_input = st.text_input(
            "Gemini API Key",
            value=get_setting("GEMINI_API_KEY", ""),
            type="password",
            placeholder="AIza... (recommended)",
            label_visibility="collapsed",
            help="Free tier: 60 req/min. Get key at makersuite.google.com",
        )
        _sync_runtime_setting("GEMINI_API_KEY", gemini_key_input)

        openai_key_input = st.text_input(
            "OpenAI API Key",
            value=get_setting("OPENAI_API_KEY", ""),
            type="password",
            placeholder="sk-... (optional)",
            label_visibility="collapsed",
            help="Leave blank to use the built-in rule-based assistant.",
        )
        _sync_runtime_setting("OPENAI_API_KEY", openai_key_input)

        gemini_active = bool(get_setting("GEMINI_API_KEY", "").strip())
        openai_active = bool(get_setting("OPENAI_API_KEY", "").strip())
        if gemini_active:
            st.success("Gemini AI connected")
        elif openai_active:
            st.success("OpenAI connected")
        else:
            st.info("Rule-based mode active")

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

    if nav == "Dashboard":
        _render_dashboard(selected_business_id)
    elif nav == "Products / Inventory":
        _render_products_inventory(business["business_type"])
    elif nav == "Members":
        _render_members(business["business_type"])
    elif nav == "Transactions":
        _render_topbar("Transactions", "Sales entries, receipts, and payment records")
        txn.render_sales_page()
    elif nav == "Analytics":
        _render_analytics(selected_business_id)
    elif nav == "AI Assistant":
        _render_topbar("AI Assistant", "Ask questions about your business data")
        _render_ai_insights(selected_business_id)
    elif nav == "Reports":
        _render_topbar("Reports", "Downloadable records and summaries")
        reports.render_reports_page()
    elif nav == "Settings":
        _render_topbar("Settings", "Business configuration and account controls")
        if auth.is_admin(current_user):
            render_admin_panel()
        elif user_role in {"owner", "admin"}:
            bm.render_business_settings()
        else:
            st.info("You can manage your account settings below.")
        render_profile_page(current_user)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        show_friendly_error(
            "Something went wrong while loading the dashboard. Please refresh and try again.",
            "app.main",
            exc,
        )
