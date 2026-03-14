"""
app.py — RetailBrain AI Multi-Business Management Platform
A comprehensive business management platform for retail, gym, coaching, and service businesses.
Run with: streamlit run app.py
"""

from __future__ import annotations
import os
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Import our modules
import database as db
import auth
from auth_page import render_auth_page, render_user_sidebar
from admin_panel import render_admin_panel
from profile_page import render_profile_page
import business_management as bm
import products_services as ps
import transactions as txn
import inventory as inv
import gym_management as gym
from ai_assistant import SalesAIAssistant

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RetailBrain AI — Business Management",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Design system
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
    plot_bgcolor="rgba(13,21,38,0.7)",
    font=dict(color=C["text"], family="Inter, sans-serif", size=12),
    hoverlabel=dict(bgcolor=C["surface2"], bordercolor=C["border"],
                   font_color=C["text"]),
)

AX = dict(gridcolor=C["border"], zeroline=False,
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

/* ── Metric cards ─────────────────────────────────────────── */
.metric-card {{
    background: {C["surface"]};
    border: 1px solid {C["border"]};
    border-radius: 12px;
    padding: 1rem 1.2rem;
    text-align: center;
}}

.metric-value {{
    font-size: 1.5rem;
    font-weight: 700;
    color: {C["text"]};
    margin: 0.3rem 0;
}}

.metric-label {{
    font-size: 0.8rem;
    color: {C["muted"]};
    text-transform: uppercase;
    letter-spacing: 0.1em;
}}

/* ── Navigation tabs ──────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
    background: {C["surface"]};
    border-radius: 12px;
    padding: 0.25rem;
    gap: 0.15rem;
    border: 1px solid {C["border"]};
}}

.stTabs [data-baseweb="tab"] {{
    background: transparent;
    color: {C["slate"]};
    font-size: 0.85rem;
    font-weight: 500;
    border-radius: 9px;
    padding: 0.6rem 1rem;
    border: none;
}}

.stTabs [aria-selected="true"] {{
    background: linear-gradient(135deg, {C["indigo"]}, {C["indigo_lt"]}) !important;
    color: #fff !important;
    font-weight: 600;
}}

.stTabs [data-baseweb="tab-border"] {{ display: none; }}
.stTabs [data-baseweb="tab-panel"] {{ padding-top: 1.4rem; }}

/* ── Buttons ──────────────────────────────────────────────── */
.stButton > button {{
    background: linear-gradient(135deg, {C["indigo"]}, {C["indigo_lt"]});
    color: #fff;
    border: none;
    border-radius: 9px;
    font-size: 0.85rem;
    font-weight: 600;
    padding: 0.5rem 1.2rem;
    transition: opacity 0.2s, transform 0.15s;
}}

.stButton > button:hover {{
    opacity: 0.88;
    transform: translateY(-1px);
}}

/* ── Sidebar logo ─────────────────────────────────────────── */
.sb-logo {{
    background: linear-gradient({C["surface"]}, {C["surface2"]});
    border-bottom: 1px solid {C["border"]};
    padding: 1.2rem 1rem 1rem;
    margin-bottom: 0.5rem;
}}

.sb-logo-mark {{
    background: linear-gradient(135deg, {C["indigo"]}, {C["cyan"]});
    border-radius: 10px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    font-size: 1rem;
    vertical-align: middle;
    margin-right: 0.5rem;
}}

.sb-logo-text {{
    font-size: 1rem;
    font-weight: 700;
    vertical-align: middle;
    color: {C["text"]};
}}

.sb-logo-version {{
    display: inline-block;
    margin-left: 0.5rem;
    background: {C["indigo"]}25;
    color: {C["indigo_lt"]};
    border-radius: 10px;
    padding: 0.08rem 0.45rem;
    font-size: 0.6rem;
    font-weight: 600;
    vertical-align: middle;
}}

.sb-section-label {{
    font-size: 0.62rem;
    font-weight: 700;
    color: {C["muted"]};
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin: 0.9rem 0 0.4rem;
}}

/* ── Status indicators ────────────────────────────────────── */
.status-indicator {{
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0.8rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
}}

.status-success {{
    background: {C["emerald"]}22;
    color: {C["emerald"]};
}}

.status-warning {{
    background: {C["amber"]}22;
    color: {C["amber"]};
}}

.status-error {{
    background: {C["rose"]}22;
    color: {C["rose"]};
}}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Session state initialization
# ─────────────────────────────────────────────────────────────────────────────
def _init_state():
    """Initialize session state variables."""
    defaults = {
        'auth_token': None,
        'user': None,
        'selected_business_id': None,
        'business_context': None,
        'ai_assistant': None,
        'chat_history': []
    }

    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

_init_state()

# ─────────────────────────────────────────────────────────────────────────────
# Dashboard Rendering Functions (defined early to avoid NameError)
# ─────────────────────────────────────────────────────────────────────────────

def render_business_dashboard(business_id: int):
    """Render the main business dashboard."""

    # Get summary data
    sales_summary = txn.get_business_sales_summary(business_id)
    inventory_summary = ps.get_business_inventory_summary(business_id)
    alerts_summary = inv.get_inventory_alerts_count(business_id)
    revenue_summary = db.get_business_revenue_summary(business_id)

    # Key metrics row
    st.markdown("### Key Metrics")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Today's Revenue</div>
            <div class="metric-value" style="color:{C['emerald']}">${sales_summary['today_revenue']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Month Revenue</div>
            <div class="metric-value" style="color:{C['indigo']}">${sales_summary['month_revenue']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Month Profit</div>
            <div class="metric-value" style="color:{C['cyan']}">${sales_summary['month_profit']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Items</div>
            <div class="metric-value" style="color:{C['slate']}">{inventory_summary['total_items']}</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        alert_color = C['rose'] if alerts_summary['total_alerts'] > 0 else C['emerald']
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Alerts</div>
            <div class="metric-value" style="color:{alert_color}">{alerts_summary['total_alerts']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Recent activity and charts
    col_left, col_right = st.columns([2, 1])

    with col_left:
        # Revenue trend
        st.markdown("#### Revenue Trend (Last 30 Days)")

        daily_data = db.get_daily_revenue_data(business_id, days=30)

        if daily_data:
            import pandas as pd
            df = pd.DataFrame(daily_data)

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['revenue'],
                mode='lines+markers',
                name='Revenue',
                line=dict(color=C['indigo'], width=3),
                marker=dict(size=6, color=C['indigo_lt'])
            ))

            fig.update_layout(
                **PLOTLY_BASE,
                height=300,
                margin=MARGIN,
                showlegend=False,
                xaxis=dict(**AX, title=""),
                yaxis=dict(**AX, title="Revenue ($)", tickprefix="$")
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 No sales data yet. Start recording sales to see trends!")

    with col_right:
        # Recent transactions
        st.markdown("#### Recent Transactions")

        if sales_summary['recent_transactions']:
            for i, transaction in enumerate(sales_summary['recent_transactions'][:5]):
                # Parse date
                txn_date = datetime.fromisoformat(transaction['transaction_date'])
                time_str = txn_date.strftime("%I:%M %p")

                st.markdown(f"""
                <div style="background:{C['surface2']};border-radius:8px;padding:0.8rem;margin-bottom:0.5rem;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <div style="color:{C['text']};font-weight:600;font-size:0.9rem">
                                {transaction['product_service_name'][:25]}...
                            </div>
                            <div style="color:{C['muted']};font-size:0.75rem">{time_str}</div>
                        </div>
                        <div style="color:{C['emerald']};font-weight:700">${transaction['total_amount']:.0f}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("💳 No recent transactions")

    # Alerts section
    if alerts_summary['total_alerts'] > 0:
        st.markdown("---")
        st.markdown("### 🚨 Inventory Alerts")

        if alerts_summary['out_of_stock'] > 0:
            st.error(f"🚫 **{alerts_summary['out_of_stock']} items are out of stock**")

        if alerts_summary['low_stock'] > 0:
            st.warning(f"⚠️ **{alerts_summary['low_stock']} items have low stock**")

        if st.button("📦 View Inventory Alerts"):
            st.switch_page("Inventory")  # This would switch to inventory tab in real implementation


def render_analytics_dashboard(business_id: int):
    """Render advanced analytics dashboard."""
    st.markdown("### Business Analytics")

    # Time period selector
    col1, col2 = st.columns([1, 3])

    with col1:
        period = st.selectbox(
            "Analysis Period",
            options=["7", "30", "90", "365"],
            format_func=lambda x: f"Last {x} days",
            index=1
        )

    # Get analytics data
    start_date = (datetime.now() - timedelta(days=int(period))).date().isoformat()
    analytics_summary = db.get_business_revenue_summary(business_id, start_date=start_date)
    top_products = db.get_top_products_services(business_id, limit=10)
    daily_data = db.get_daily_revenue_data(business_id, days=int(period))

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        f"Revenue ({period} days)",
        f"${analytics_summary['total_revenue']:,.0f}"
    )
    col2.metric(
        f"Profit ({period} days)",
        f"${analytics_summary['total_profit']:,.0f}"
    )
    col3.metric(
        "Profit Margin",
        f"{analytics_summary['profit_margin']:.1f}%"
    )
    col4.metric(
        f"Transactions ({period} days)",
        f"{analytics_summary['total_transactions']:,}"
    )

    if daily_data and top_products:
        # Charts
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.markdown("#### Daily Revenue Trend")

            import pandas as pd
            df = pd.DataFrame(daily_data)

            fig = px.area(
                df,
                x='date',
                y='revenue',
                title="",
                color_discrete_sequence=[C['indigo']]
            )
            fig.update_layout(**PLOTLY_BASE, height=350, margin=MARGIN)
            st.plotly_chart(fig, use_container_width=True)

        with col_chart2:
            st.markdown("#### Top Products by Revenue")

            products_df = pd.DataFrame(top_products[:8])

            fig = px.pie(
                products_df,
                values='total_revenue',
                names='name',
                title=""
            )
            fig.update_layout(**PLOTLY_BASE, height=350, margin=MARGIN)
            st.plotly_chart(fig, use_container_width=True)

        # Products performance table
        st.markdown("#### Product Performance Details")

        display_df = pd.DataFrame(top_products)
        if not display_df.empty:
            display_df = display_df[['name', 'type', 'transactions_count', 'total_quantity_sold', 'total_revenue', 'total_profit']]
            display_df.columns = ['Product', 'Type', 'Transactions', 'Qty Sold', 'Revenue', 'Profit']

            st.dataframe(
                display_df.style.format({
                    'Revenue': '${:,.0f}',
                    'Profit': '${:,.0f}',
                    'Qty Sold': '{:,}',
                    'Transactions': '{:,}'
                }),
                use_container_width=True
            )
    else:
        st.info("📊 Start recording sales to see detailed analytics!")


def render_ai_assistant(business_id: int):
    """Render AI assistant for business insights."""
    st.markdown("### AI Business Assistant")

    # Get business context for AI
    business = bm.get_current_business_info()
    revenue_summary = db.get_business_revenue_summary(business_id)
    top_products = db.get_top_products_services(business_id, limit=5)

    # Build context summary
    context_parts = [
        f"Business: {business['name']} ({business['business_type']})",
        f"Total Revenue: ${revenue_summary['total_revenue']:,.2f}",
        f"Total Profit: ${revenue_summary['total_profit']:,.2f}",
        f"Profit Margin: {revenue_summary['profit_margin']:.1f}%",
        f"Total Transactions: {revenue_summary['total_transactions']:,}",
    ]

    if top_products:
        context_parts.append("Top Products:")
        for product in top_products[:3]:
            context_parts.append(f"- {product['name']}: ${product['total_revenue']:,.0f} revenue")

    context = "\n".join(context_parts)

    # Initialize AI assistant if needed
    if 'ai_assistant' not in st.session_state or st.session_state['ai_assistant'] is None:
        st.session_state['ai_assistant'] = SalesAIAssistant(context)

    # AI status
    gemini_active = bool(os.getenv("GEMINI_API_KEY", "").strip())
    openai_active = bool(os.getenv("OPENAI_API_KEY", "").strip())

    if gemini_active or openai_active:
        ai_name = "Gemini AI" if gemini_active else "OpenAI GPT"
        st.success(f"🤖 {ai_name} connected - Full AI analysis available")
    else:
        st.warning("⚡ Rule-based mode - Add API key in sidebar for advanced AI insights")

    # Pre-defined questions
    st.markdown("#### Quick Questions")

    questions = [
        "What's my best selling product?",
        "How's my profit margin looking?",
        "Which month had the highest revenue?",
        "What business insights can you provide?",
        "How can I improve my sales?",
        "Show me my revenue trends"
    ]

    cols = st.columns(3)
    for i, question in enumerate(questions):
        if cols[i % 3].button(question, key=f"q_{i}", use_container_width=True):
            st.session_state['chat_history'].append({"role": "user", "content": question})
            try:
                response = st.session_state['ai_assistant'].chat(question)
                # Log AI request
                if current_user:
                    db.log_ai_request(
                        current_user["id"],
                        st.session_state['ai_assistant'].provider or "rule-based",
                        question
                    )
            except Exception as e:
                response = f"Sorry, I encountered an error: {e}"
            st.session_state['chat_history'].append({"role": "assistant", "content": response})
            st.rerun()

    # Chat interface
    st.markdown("#### Conversation")

    # Display chat history
    for message in st.session_state.get('chat_history', []):
        avatar = "🤖" if message["role"] == "assistant" else "👤"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask me anything about your business..."):
        st.session_state['chat_history'].append({"role": "user", "content": prompt})

        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Analyzing your business data..."):
                try:
                    response = st.session_state['ai_assistant'].chat(prompt)
                    # Log AI request
                    if current_user:
                        db.log_ai_request(
                            current_user["id"],
                            st.session_state['ai_assistant'].provider or "rule-based",
                            prompt
                        )
                except Exception as e:
                    response = f"Sorry, I encountered an error: {e}"
            st.markdown(response)

        st.session_state['chat_history'].append({"role": "assistant", "content": response})

    # Clear conversation
    if st.session_state.get('chat_history') and st.button("🗑️ Clear Conversation"):
        st.session_state['chat_history'] = []
        if st.session_state.get('ai_assistant'):
            st.session_state['ai_assistant'].reset_history()
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Authentication Gate
# ─────────────────────────────────────────────────────────────────────────────
if not render_auth_page():
    st.stop()

current_user = st.session_state["user"]

# ─────────────────────────────────────────────────────────────────────────────
# Business Selection Logic
# ─────────────────────────────────────────────────────────────────────────────
user_businesses = db.get_user_businesses(current_user["id"])

# If user has no businesses, show business setup
if not user_businesses:
    bm.render_business_setup()
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    # Logo
    st.markdown("""
    <div class="sb-logo">
        <span class="sb-logo-mark">🧠</span>
        <span class="sb-logo-text">RetailBrain</span>
        <span class="sb-logo-version">AI</span>
    </div>""", unsafe_allow_html=True)

    # User info
    render_user_sidebar(current_user)

    # Business selector
    st.markdown('<div class="sb-section-label">Select Business</div>', unsafe_allow_html=True)
    selected_business_id = bm.render_business_selector(current_user["id"])

    if selected_business_id:
        # Get business info for sidebar stats
        business = bm.get_current_business_info()
        if business:
            # Quick stats
            sales_summary = txn.get_business_sales_summary(selected_business_id)
            inventory_summary = ps.get_business_inventory_summary(selected_business_id)
            alerts_summary = inv.get_inventory_alerts_count(selected_business_id)

            st.markdown('<div class="sb-section-label">Today\'s Overview</div>', unsafe_allow_html=True)

            st.markdown(f"""
            <div style="background:{C["surface2"]};border:1px solid {C["border"]};
                        border-radius:10px;padding:0.8rem;font-size:0.8rem;">
                <div style="display:flex;justify-content:space-between;margin-bottom:0.4rem;">
                    <span style="color:{C["muted"]}">Revenue</span>
                    <span style="color:{C["emerald"]};font-weight:600">${sales_summary['today_revenue']:,.0f}</span>
                </div>
                <div style="display:flex;justify-content:space-between;margin-bottom:0.4rem;">
                    <span style="color:{C["muted"]}">Transactions</span>
                    <span style="color:{C["text"]};font-weight:600">{sales_summary['today_transactions']}</span>
                </div>
                <div style="display:flex;justify-content:space-between;margin-bottom:0.4rem;">
                    <span style="color:{C["muted"]}">Products</span>
                    <span style="color:{C["cyan"]};font-weight:600">{inventory_summary['total_products']}</span>
                </div>
                <div style="display:flex;justify-content:space-between;">
                    <span style="color:{C["muted"]}">Alerts</span>
                    <span style="color:{C["amber"] if alerts_summary['total_alerts'] > 0 else C["emerald"]};font-weight:600">
                        {alerts_summary['total_alerts']}
                    </span>
                </div>
            </div>""", unsafe_allow_html=True)

    # AI Settings
    st.markdown('<div class="sb-section-label">AI Settings</div>', unsafe_allow_html=True)

    # Check if keys are already set
    gemini_set = bool(os.getenv("GEMINI_API_KEY", "").strip())
    openai_set = bool(os.getenv("OPENAI_API_KEY", "").strip())

    # Gemini API Key
    if gemini_set:
        st.markdown(f"""
        <div style="background:{C['emerald']}20;border:1px solid {C['emerald']};
                    border-radius:8px;padding:0.5rem;margin-bottom:0.5rem;">
            <div style="color:{C['emerald']};font-size:0.8rem;font-weight:600;">
                ✅ Gemini API Key Active
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🔄 Update Gemini Key", key="update_gemini"):
            st.session_state["updating_gemini"] = True
            st.rerun()
    else:
        st.session_state["updating_gemini"] = True

    if st.session_state.get("updating_gemini", False):
        gemini_key_input = st.text_input(
            "Google Gemini API Key",
            value="",
            type="password",
            placeholder="AIza... (free tier)",
            help="Get free key at https://makersuite.google.com",
            key="gemini_input"
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save", key="save_gemini"):
                if gemini_key_input.strip():
                    os.environ["GEMINI_API_KEY"] = gemini_key_input.strip()
                    st.session_state["updating_gemini"] = False
                    st.success("✅ Gemini key saved!")
                    st.rerun()
        with col2:
            if st.button("❌ Cancel", key="cancel_gemini"):
                st.session_state["updating_gemini"] = False
                st.rerun()

    # OpenAI API Key
    if openai_set:
        st.markdown(f"""
        <div style="background:{C['indigo']}20;border:1px solid {C['indigo']};
                    border-radius:8px;padding:0.5rem;margin-bottom:0.5rem;">
            <div style="color:{C['indigo']};font-size:0.8rem;font-weight:600;">
                ✅ OpenAI API Key Active
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🔄 Update OpenAI Key", key="update_openai"):
            st.session_state["updating_openai"] = True
            st.rerun()
    else:
        st.session_state["updating_openai"] = True

    if st.session_state.get("updating_openai", False):
        openai_key_input = st.text_input(
            "OpenAI API Key",
            value="",
            type="password",
            placeholder="sk-... (optional)",
            help="For enhanced AI capabilities",
            key="openai_input"
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save", key="save_openai"):
                if openai_key_input.strip():
                    os.environ["OPENAI_API_KEY"] = openai_key_input.strip()
                    st.session_state["updating_openai"] = False
                    st.success("✅ OpenAI key saved!")
                    st.rerun()
        with col2:
            if st.button("❌ Cancel", key="cancel_openai"):
                st.session_state["updating_openai"] = False
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────────────────────────────────────

# Check if business is selected
if not selected_business_id:
    st.error("Please select a business from the sidebar.")
    st.stop()

# Render business header
bm.render_business_dashboard_header()

# Check business access
user_role = bm.check_business_access(current_user["id"], selected_business_id)
if not user_role:
    st.error("You don't have access to this business.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# Navigation Tabs (Business-Type Specific)
# ─────────────────────────────────────────────────────────────────────────────
# Get current business info to determine business type
current_business = bm.get_current_business_info()
business_type = current_business['business_type'] if current_business else None

if auth.is_admin(current_user) or user_role == "owner":
    # Create different tab layouts based on business type
    if business_type == "gym":
        tabs = st.tabs([
            "📊 Dashboard",
            "🏋️‍♂️ Gym Management",
            "💳 Sales",
            "📦 Products & Services",
            "📈 Analytics",
            "🔔 Inventory",
            "🤖 AI Assistant",
            "👤 Profile",
            "⚙️ Settings"
        ])
        tab_dashboard, tab_gym, tab_sales, tab_products, tab_analytics, tab_inventory, tab_ai, tab_profile, tab_settings = tabs
    else:
        tabs = st.tabs([
            "📊 Dashboard",
            "💳 Sales",
            "📦 Products & Services",
            "📈 Analytics",
            "🔔 Inventory",
            "🤖 AI Assistant",
            "👤 Profile",
            "⚙️ Settings"
        ])
        tab_dashboard, tab_sales, tab_products, tab_analytics, tab_inventory, tab_ai, tab_profile, tab_settings = tabs
        tab_gym = None
else:
    # Create different tab layouts based on business type for non-admin users
    if business_type == "gym":
        tabs = st.tabs([
            "📊 Dashboard",
            "🏋️‍♂️ Gym Management",
            "💳 Sales",
            "📦 Products & Services",
            "📈 Analytics",
            "🔔 Inventory",
            "🤖 AI Assistant",
            "👤 Profile"
        ])
        tab_dashboard, tab_gym, tab_sales, tab_products, tab_analytics, tab_inventory, tab_ai, tab_profile = tabs
        tab_settings = None
    else:
        tabs = st.tabs([
            "📊 Dashboard",
            "💳 Sales",
            "📦 Products & Services",
            "📈 Analytics",
            "🔔 Inventory",
            "🤖 AI Assistant",
            "👤 Profile"
        ])
        tab_dashboard, tab_sales, tab_products, tab_analytics, tab_inventory, tab_ai, tab_profile = tabs
        tab_settings = None
        tab_gym = None

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — Dashboard
# ═════════════════════════════════════════════════════════════════════════════
with tab_dashboard:
    render_business_dashboard(selected_business_id)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — Gym Management (Gym Businesses Only)
# ═════════════════════════════════════════════════════════════════════════════
if tab_gym is not None:
    with tab_gym:
        gym.render_gym_management_page()

# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — Sales
# ═════════════════════════════════════════════════════════════════════════════
with tab_sales:
    txn.render_sales_page()

# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — Products & Services
# ═════════════════════════════════════════════════════════════════════════════
with tab_products:
    ps.render_products_services_page()

# ═════════════════════════════════════════════════════════════════════════════
# TAB 5 — Analytics
# ═════════════════════════════════════════════════════════════════════════════
with tab_analytics:
    render_analytics_dashboard(selected_business_id)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 6 — Inventory
# ═════════════════════════════════════════════════════════════════════════════
with tab_inventory:
    inv.render_inventory_page()

# ═════════════════════════════════════════════════════════════════════════════
# TAB 7 — AI Assistant
# ═════════════════════════════════════════════════════════════════════════════
with tab_ai:
    render_ai_assistant(selected_business_id)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 8 — Profile
# ═════════════════════════════════════════════════════════════════════════════
with tab_profile:
    render_profile_page(current_user)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 9 — Settings (Admin/Owner only)
# ═════════════════════════════════════════════════════════════════════════════
if tab_settings is not None:
    with tab_settings:
        if auth.is_admin(current_user):
            # Super admin panel
            render_admin_panel()
        else:
            # Business settings
            bm.render_business_settings()

