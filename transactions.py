"""
transactions.py
Transaction recording and sales management for multi-business platform.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Optional, List
import database as db
import business_management as bm

# Design tokens
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

PAYMENT_METHODS = {
    'cash': {'name': 'Cash', 'icon': '💵'},
    'card': {'name': 'Credit/Debit Card', 'icon': '💳'},
    'digital': {'name': 'Digital Payment', 'icon': '📱'},
    'bank_transfer': {'name': 'Bank Transfer', 'icon': '🏦'},
    'check': {'name': 'Check', 'icon': '📄'}
}


def render_sales_page():
    """Render the main sales/transactions page."""
    business = bm.get_current_business_info()
    if not business:
        st.error("No business selected")
        return

    user = st.session_state.get("user")
    user_role = bm.check_business_access(user["id"], business["id"]) if user else None

    if not user_role:
        st.error("You don't have access to this business")
        return

    # Header
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;">
        <div>
            <h2 style="color:{C['text']};margin:0;">Sales & Transactions</h2>
            <p style="color:{C['muted']};margin:0;font-size:.9rem;">
                Record sales and manage transaction history
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tabs
    tab1, tab2, tab3 = st.tabs(["💳 Record Sale", "📊 Transaction History", "📈 Sales Analytics"])

    with tab1:
        _render_record_sale_form(business["id"], user["id"])

    with tab2:
        _render_transaction_history(business["id"])

    with tab3:
        _render_sales_analytics(business["id"])


def _render_record_sale_form(business_id: int, user_id: int):
    """Render form to record a new sale."""
    st.markdown("### Record New Sale")

    # Get available products/services
    items = db.get_business_products_services(business_id, active_only=True)

    if not items:
        st.warning("⚠️ No active products or services found. Add some items first in the Products & Services section.")
        return

    with st.form("record_sale"):
        # Product/Service selection
        st.markdown("**Item Details**")
        col1, col2 = st.columns(2)

        with col1:
            # Create options with type indicators and stock info
            item_options = {}
            for item in items:
                icon = "📦" if item["type"] == "product" else "🛠️"
                stock_info = ""
                if item["type"] == "product" and item["stock_quantity"] is not None:
                    stock_info = f" (Stock: {item['stock_quantity']})"
                label = f"{icon} {item['name']} - ${item['price']:.2f}{stock_info}"
                item_options[label] = item

            selected_label = st.selectbox("Select Product/Service *", options=list(item_options.keys()))
            selected_item = item_options[selected_label]

            quantity = st.number_input("Quantity *", min_value=1, value=1)

        with col2:
            # Auto-fill price but allow editing
            unit_price = st.number_input("Unit Price *", min_value=0.01, value=float(selected_item["price"]), step=0.01)

            # Payment method
            payment_method = st.selectbox(
                "Payment Method *",
                options=list(PAYMENT_METHODS.keys()),
                format_func=lambda x: f"{PAYMENT_METHODS[x]['icon']} {PAYMENT_METHODS[x]['name']}"
            )

        # Customer information (optional)
        st.markdown("**Customer Information (Optional)**")
        col3, col4, col5 = st.columns(3)

        with col3:
            customer_name = st.text_input("Customer Name", placeholder="John Doe")
        with col4:
            customer_email = st.text_input("Customer Email", placeholder="john@example.com")
        with col5:
            customer_phone = st.text_input("Customer Phone", placeholder="+1 (555) 123-4567")

        # Transaction details
        st.markdown("**Transaction Details**")
        col6, col7 = st.columns(2)

        with col6:
            transaction_date = st.date_input("Transaction Date", value=datetime.now().date())
            transaction_time = st.time_input("Transaction Time", value=datetime.now().time())

        with col7:
            notes = st.text_area("Notes (Optional)", placeholder="Additional notes...")

        # Calculate totals
        total_amount = quantity * unit_price
        profit_per_unit = unit_price - selected_item["cost"]
        total_profit = quantity * profit_per_unit

        # Show calculation summary
        st.markdown(f"""
        <div style="background:{C['surface2']};border-radius:10px;padding:1rem;margin:1rem 0;">
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;">
                <div style="text-align:center;">
                    <div style="color:{C['muted']};font-size:.8rem">TOTAL AMOUNT</div>
                    <div style="color:{C['text']};font-size:1.5rem;font-weight:700">${total_amount:.2f}</div>
                </div>
                <div style="text-align:center;">
                    <div style="color:{C['muted']};font-size:.8rem">PROFIT</div>
                    <div style="color:{C['emerald']};font-size:1.5rem;font-weight:700">${total_profit:.2f}</div>
                </div>
                <div style="text-align:center;">
                    <div style="color:{C['muted']};font-size:.8rem">MARGIN</div>
                    <div style="color:{C['indigo']};font-size:1.5rem;font-weight:700">
                        {(profit_per_unit / unit_price * 100):.1f}%
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Stock warning for products
        if selected_item["type"] == "product" and selected_item["stock_quantity"] is not None:
            if quantity > selected_item["stock_quantity"]:
                st.error(f"⚠️ Not enough stock! Available: {selected_item['stock_quantity']}")
            elif selected_item["stock_quantity"] - quantity <= selected_item["min_stock_level"]:
                st.warning(f"⚠️ This sale will bring stock to {selected_item['stock_quantity'] - quantity} units (below minimum level)")

        # Submit button
        submitted = st.form_submit_button("💰 Record Sale", use_container_width=True, type="primary")

        if submitted:
            # Validate stock for products
            if selected_item["type"] == "product" and selected_item["stock_quantity"] is not None:
                if quantity > selected_item["stock_quantity"]:
                    st.error("Cannot complete sale: insufficient stock")
                    return

            try:
                # Combine date and time
                transaction_datetime = datetime.combine(transaction_date, transaction_time).isoformat()

                # Create transaction
                transaction_id = db.create_transaction(
                    business_id=business_id,
                    product_service_id=selected_item["id"],
                    user_id=user_id,
                    quantity=quantity,
                    unit_price=unit_price,
                    unit_cost=selected_item["cost"],
                    payment_method=payment_method,
                    customer_name=customer_name.strip() if customer_name else None,
                    customer_email=customer_email.strip() if customer_email else None,
                    customer_phone=customer_phone.strip() if customer_phone else None,
                    notes=notes.strip() if notes else None,
                    transaction_date=transaction_datetime
                )

                # Success message
                st.success(f"✅ Sale recorded successfully! Transaction ID: {transaction_id}")
                st.balloons()

                # Show receipt
                _show_receipt(transaction_id)

                st.rerun()

            except Exception as e:
                st.error(f"Error recording sale: {e}")


def _show_receipt(transaction_id: int):
    """Show a receipt for the completed transaction."""
    transaction = db.get_transaction_by_id(transaction_id)
    if not transaction:
        return

    st.markdown("### 🧾 Receipt")

    receipt_html = f"""
    <div style="background:{C['surface']};border:1px solid {C['border']};
                border-radius:10px;padding:1.5rem;margin:1rem 0;max-width:400px;">
        <div style="text-align:center;margin-bottom:1rem;">
            <h4 style="color:{C['text']};margin:0;">RECEIPT</h4>
            <div style="color:{C['muted']};font-size:.8rem">#{transaction_id}</div>
        </div>

        <div style="border-bottom:1px solid {C['border']};padding-bottom:1rem;margin-bottom:1rem;">
            <div style="display:flex;justify-content:space-between;margin-bottom:.5rem;">
                <span style="color:{C['muted']}">Item:</span>
                <span style="color:{C['text']}">{transaction['product_service_name']}</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:.5rem;">
                <span style="color:{C['muted']}">Quantity:</span>
                <span style="color:{C['text']}">{transaction['quantity']}</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:.5rem;">
                <span style="color:{C['muted']}">Unit Price:</span>
                <span style="color:{C['text']}">${transaction['unit_price']:.2f}</span>
            </div>
            <div style="display:flex;justify-content:space-between;">
                <span style="color:{C['muted']}">Payment:</span>
                <span style="color:{C['text']}">{PAYMENT_METHODS[transaction['payment_method']]['name']}</span>
            </div>
        </div>

        <div style="display:flex;justify-content:space-between;font-size:1.2rem;font-weight:700;">
            <span style="color:{C['text']}">TOTAL:</span>
            <span style="color:{C['emerald']}">${transaction['total_amount']:.2f}</span>
        </div>

        <div style="text-align:center;margin-top:1rem;color:{C['muted']};font-size:.8rem;">
            {transaction['transaction_date'][:19].replace('T', ' ')}
        </div>
    </div>
    """

    st.markdown(receipt_html, unsafe_allow_html=True)


def _render_transaction_history(business_id: int):
    """Render transaction history with filters."""
    st.markdown("### Transaction History")

    # Filters
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        date_filter = st.selectbox(
            "Date Range",
            options=["all", "today", "week", "month", "custom"],
            format_func=lambda x: {
                "all": "All Time",
                "today": "Today",
                "week": "This Week",
                "month": "This Month",
                "custom": "Custom Range"
            }[x]
        )

    with col2:
        payment_filter = st.selectbox(
            "Payment Method",
            options=["all"] + list(PAYMENT_METHODS.keys()),
            format_func=lambda x: "All Methods" if x == "all" else PAYMENT_METHODS[x]["name"]
        )

    with col3:
        sort_by = st.selectbox(
            "Sort By",
            options=["date_desc", "date_asc", "amount_desc", "amount_asc"],
            format_func=lambda x: {
                "date_desc": "Newest First",
                "date_asc": "Oldest First",
                "amount_desc": "Highest Amount",
                "amount_asc": "Lowest Amount"
            }[x]
        )

    with col4:
        limit = st.selectbox("Show", options=[25, 50, 100, 200], index=1)

    # Custom date range
    start_date = end_date = None
    if date_filter == "custom":
        col_start, col_end = st.columns(2)
        with col_start:
            start_date = st.date_input("Start Date")
        with col_end:
            end_date = st.date_input("End Date")

    # Get transactions
    transactions = db.get_business_transactions(business_id, limit=limit)

    if not transactions:
        st.info("📊 No transactions found.")
        return

    # Apply filters
    filtered = []
    for txn in transactions:
        # Date filter
        txn_date = datetime.fromisoformat(txn["transaction_date"]).date()

        if date_filter == "today" and txn_date != datetime.now().date():
            continue
        elif date_filter == "week" and txn_date < (datetime.now() - timedelta(days=7)).date():
            continue
        elif date_filter == "month" and txn_date < (datetime.now() - timedelta(days=30)).date():
            continue
        elif date_filter == "custom" and start_date and end_date:
            if not (start_date <= txn_date <= end_date):
                continue

        # Payment method filter
        if payment_filter != "all" and txn["payment_method"] != payment_filter:
            continue

        filtered.append(txn)

    # Sort transactions
    if sort_by == "date_desc":
        filtered.sort(key=lambda x: x["transaction_date"], reverse=True)
    elif sort_by == "date_asc":
        filtered.sort(key=lambda x: x["transaction_date"])
    elif sort_by == "amount_desc":
        filtered.sort(key=lambda x: x["total_amount"], reverse=True)
    elif sort_by == "amount_asc":
        filtered.sort(key=lambda x: x["total_amount"])

    if not filtered:
        st.info("No transactions match your filters.")
        return

    # Summary stats
    total_amount = sum(txn["total_amount"] for txn in filtered)
    total_profit = sum((txn["unit_price"] - txn["unit_cost"]) * txn["quantity"] for txn in filtered)
    avg_transaction = total_amount / len(filtered) if filtered else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Sales", f"${total_amount:,.2f}")
    col2.metric("Total Profit", f"${total_profit:,.2f}")
    col3.metric("Transactions", len(filtered))
    col4.metric("Avg Transaction", f"${avg_transaction:.2f}")

    # Transaction list
    st.markdown("---")
    for txn in filtered:
        _render_transaction_item(txn)


def _render_transaction_item(txn: dict):
    """Render a single transaction item."""
    # Parse date
    txn_datetime = datetime.fromisoformat(txn["transaction_date"])
    date_str = txn_datetime.strftime("%b %d, %Y at %I:%M %p")

    # Calculate profit
    profit = (txn["unit_price"] - txn["unit_cost"]) * txn["quantity"]
    profit_color = C["emerald"] if profit > 0 else C["muted"]

    # Type icon
    type_icon = "📦" if txn["product_service_type"] == "product" else "🛠️"

    # Payment method
    payment_info = PAYMENT_METHODS.get(txn["payment_method"], {"name": "Unknown", "icon": "💳"})

    st.markdown(f"""
    <div style="background:{C['surface']};border:1px solid {C['border']};
                border-radius:10px;padding:1rem;margin-bottom:.8rem;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div style="flex:1;">
                <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.5rem;">
                    <span style="font-size:1.2rem">{type_icon}</span>
                    <strong style="color:{C['text']};font-size:1rem">{txn['product_service_name']}</strong>
                    <span style="background:{C['surface2']};color:{C['muted']};padding:.15rem .5rem;
                                 border-radius:10px;font-size:.7rem">#{txn['id']}</span>
                </div>

                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));
                            gap:.8rem;color:{C['muted']};font-size:.85rem;">
                    <div>
                        <strong style="color:{C['text']}">{txn['quantity']}</strong> ×
                        <strong style="color:{C['text']}">${txn['unit_price']:.2f}</strong>
                    </div>
                    <div>{payment_info['icon']} {payment_info['name']}</div>
                    <div>👤 {txn['staff_name']}</div>
                    <div>🕒 {date_str}</div>
                </div>

                {f'<div style="margin-top:.5rem;color:{C["muted"]};font-size:.8rem;">Customer: {txn["customer_name"]}</div>' if txn.get('customer_name') else ''}
                {f'<div style="color:{C["muted"]};font-size:.8rem;">{txn["notes"]}</div>' if txn.get('notes') else ''}
            </div>

            <div style="text-align:right;">
                <div style="font-size:1.3rem;font-weight:700;color:{C['text']}">
                    ${txn['total_amount']:.2f}
                </div>
                <div style="font-size:.8rem;color:{profit_color}">
                    Profit: ${profit:.2f}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_sales_analytics(business_id: int):
    """Render sales analytics and charts."""
    st.markdown("### Sales Analytics")

    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        period = st.selectbox(
            "Analysis Period",
            options=["7", "30", "90", "365"],
            format_func=lambda x: f"Last {x} days"
        )

    # Get data
    daily_data = db.get_daily_revenue_data(business_id, days=int(period))
    revenue_summary = db.get_business_revenue_summary(business_id)
    top_products = db.get_top_products_services(business_id)

    if not daily_data:
        st.info("📊 No sales data available for the selected period.")
        return

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Revenue", f"${revenue_summary['total_revenue']:,.2f}")
    col2.metric("Total Profit", f"${revenue_summary['total_profit']:,.2f}")
    col3.metric("Profit Margin", f"{revenue_summary['profit_margin']:.1f}%")
    col4.metric("Transactions", f"{revenue_summary['total_transactions']:,}")

    # Revenue trend chart
    st.markdown("#### Revenue Trend")
    df = pd.DataFrame(daily_data)

    if len(df) > 0:
        fig = go.Figure()

        # Revenue bars
        fig.add_trace(go.Bar(
            x=df['date'],
            y=df['revenue'],
            name='Revenue',
            marker_color=C['indigo'],
            opacity=0.8
        ))

        # Profit line
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['profit'],
            mode='lines+markers',
            name='Profit',
            line=dict(color=C['emerald'], width=3),
            yaxis='y2'
        ))

        fig.update_layout(
            title="Daily Revenue & Profit",
            xaxis_title="Date",
            yaxis_title="Revenue ($)",
            yaxis2=dict(
                title="Profit ($)",
                overlaying='y',
                side='right'
            ),
            hovermode='x unified',
            height=400,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )

        st.plotly_chart(fig, use_container_width=True)

    # Top products
    if top_products:
        st.markdown("#### Top Selling Items")

        # Create DataFrame for easier handling
        top_df = pd.DataFrame(top_products)

        col1, col2 = st.columns(2)

        with col1:
            # Revenue chart
            fig_revenue = px.bar(
                top_df.head(10),
                x='total_revenue',
                y='name',
                orientation='h',
                title='Top Items by Revenue',
                color='total_revenue',
                color_continuous_scale=['#f43f5e', '#6366f1']
            )
            fig_revenue.update_layout(height=400)
            st.plotly_chart(fig_revenue, use_container_width=True)

        with col2:
            # Quantity chart
            fig_qty = px.pie(
                top_df.head(8),
                values='total_quantity_sold',
                names='name',
                title='Quantity Sold Distribution'
            )
            fig_qty.update_layout(height=400)
            st.plotly_chart(fig_qty, use_container_width=True)

        # Top products table
        st.markdown("**Detailed Performance:**")
        display_df = top_df[['name', 'type', 'transactions_count', 'total_quantity_sold', 'total_revenue', 'total_profit']].copy()
        display_df.columns = ['Item', 'Type', 'Transactions', 'Qty Sold', 'Revenue', 'Profit']

        st.dataframe(
            display_df.style
            .format({
                'Revenue': '${:,.2f}',
                'Profit': '${:,.2f}',
                'Qty Sold': '{:,}',
                'Transactions': '{:,}'
            })
            .background_gradient(subset=['Revenue'], cmap='Greens')
            .background_gradient(subset=['Profit'], cmap='Blues'),
            use_container_width=True
        )


def get_business_sales_summary(business_id: int) -> dict:
    """Get sales summary for dashboard."""
    # Today's sales
    today = datetime.now().date().isoformat()
    today_summary = db.get_business_revenue_summary(business_id, start_date=today, end_date=today)

    # This month's sales
    month_start = datetime.now().replace(day=1).date().isoformat()
    month_summary = db.get_business_revenue_summary(business_id, start_date=month_start)

    # Recent transactions
    recent_transactions = db.get_business_transactions(business_id, limit=5)

    return {
        'today_revenue': today_summary['total_revenue'],
        'today_transactions': today_summary['total_transactions'],
        'month_revenue': month_summary['total_revenue'],
        'month_profit': month_summary['total_profit'],
        'month_transactions': month_summary['total_transactions'],
        'recent_transactions': recent_transactions
    }