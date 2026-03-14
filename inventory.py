"""
inventory.py
Inventory management and stock alerts for multi-business platform.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Optional
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


def render_inventory_page():
    """Render the main inventory management page."""
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
            <h2 style="color:{C['text']};margin:0;">Inventory Management</h2>
            <p style="color:{C['muted']};margin:0;font-size:.9rem;">
                Monitor stock levels and manage inventory alerts
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Get alerts first
    alerts = db.get_business_inventory_alerts(business["id"], unresolved_only=True)

    # Show alerts banner if any
    if alerts:
        _render_alerts_banner(alerts)

    # Tabs
    tab1, tab2, tab3 = st.tabs(["📦 Stock Overview", "🚨 Alerts", "📊 Inventory Reports"])

    with tab1:
        _render_stock_overview(business["id"])

    with tab2:
        _render_alerts_management(business["id"])

    with tab3:
        _render_inventory_reports(business["id"])


def _render_alerts_banner(alerts: List[dict]):
    """Render alerts banner at the top."""
    critical_alerts = [a for a in alerts if a["alert_type"] == "out_of_stock"]
    warning_alerts = [a for a in alerts if a["alert_type"] == "low_stock"]

    if critical_alerts:
        st.error(f"🚨 **{len(critical_alerts)} items are out of stock!** Check the Alerts tab for details.")

    if warning_alerts:
        st.warning(f"⚠️ **{len(warning_alerts)} items have low stock.** Consider restocking soon.")


def _render_stock_overview(business_id: int):
    """Render stock overview with current levels."""
    st.markdown("### Current Stock Levels")

    # Get all products (services don't have stock)
    products = [
        item for item in db.get_business_products_services(business_id, active_only=True)
        if item["type"] == "product"
    ]

    if not products:
        st.info("📦 No products found. Add some products in the Products & Services section.")
        return

    # Summary metrics
    total_products = len(products)
    tracked_products = len([p for p in products if p["stock_quantity"] is not None])
    out_of_stock = len([p for p in products if p["stock_quantity"] == 0])
    low_stock = len([p for p in products if p["stock_quantity"] is not None and
                     0 < p["stock_quantity"] <= p["min_stock_level"]])

    # Calculate total inventory value
    total_value = sum(
        (p["stock_quantity"] or 0) * p["cost"]
        for p in products if p["stock_quantity"] is not None
    )

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Products", total_products)
    col2.metric("Tracked Items", tracked_products)
    col3.metric("Out of Stock", out_of_stock, delta=f"-{out_of_stock}" if out_of_stock > 0 else None)
    col4.metric("Low Stock", low_stock, delta=f"-{low_stock}" if low_stock > 0 else None)
    col5.metric("Inventory Value", f"${total_value:,.2f}")

    # Stock level visualization
    if tracked_products > 0:
        st.markdown("#### Stock Level Distribution")

        # Create stock level categories
        stock_data = []
        for product in products:
            if product["stock_quantity"] is not None:
                if product["stock_quantity"] == 0:
                    category = "Out of Stock"
                    color = C["rose"]
                elif product["stock_quantity"] <= product["min_stock_level"]:
                    category = "Low Stock"
                    color = C["amber"]
                elif product["stock_quantity"] <= product["min_stock_level"] * 2:
                    category = "Medium Stock"
                    color = C["cyan"]
                else:
                    category = "Good Stock"
                    color = C["emerald"]

                stock_data.append({
                    "product": product["name"],
                    "stock": product["stock_quantity"],
                    "min_level": product["min_stock_level"],
                    "category": category,
                    "color": color,
                    "value": product["stock_quantity"] * product["cost"]
                })

        if stock_data:
            df = pd.DataFrame(stock_data)

            col1, col2 = st.columns(2)

            with col1:
                # Stock levels bar chart
                fig = px.bar(
                    df,
                    x="stock",
                    y="product",
                    color="category",
                    orientation="h",
                    title="Current Stock Levels",
                    color_discrete_map={
                        "Out of Stock": C["rose"],
                        "Low Stock": C["amber"],
                        "Medium Stock": C["cyan"],
                        "Good Stock": C["emerald"]
                    }
                )
                fig.update_layout(height=400, showlegend=True)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Stock category pie chart
                category_counts = df["category"].value_counts()
                fig_pie = px.pie(
                    values=category_counts.values,
                    names=category_counts.index,
                    title="Stock Status Distribution",
                    color=category_counts.index,
                    color_discrete_map={
                        "Out of Stock": C["rose"],
                        "Low Stock": C["amber"],
                        "Medium Stock": C["cyan"],
                        "Good Stock": C["emerald"]
                    }
                )
                fig_pie.update_layout(height=400)
                st.plotly_chart(fig_pie, use_container_width=True)

    # Detailed product table
    st.markdown("#### Product Details")

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            options=["all", "good", "low", "out"],
            format_func=lambda x: {
                "all": "All Products",
                "good": "Good Stock",
                "low": "Low Stock",
                "out": "Out of Stock"
            }[x]
        )

    with col2:
        sort_by = st.selectbox(
            "Sort By",
            options=["name", "stock_asc", "stock_desc", "value_desc"],
            format_func=lambda x: {
                "name": "Name (A-Z)",
                "stock_asc": "Stock (Low to High)",
                "stock_desc": "Stock (High to Low)",
                "value_desc": "Value (High to Low)"
            }[x]
        )

    # Apply filters
    filtered_products = products.copy()

    if status_filter == "out":
        filtered_products = [p for p in filtered_products if p["stock_quantity"] == 0]
    elif status_filter == "low":
        filtered_products = [p for p in filtered_products if
                           p["stock_quantity"] is not None and
                           0 < p["stock_quantity"] <= p["min_stock_level"]]
    elif status_filter == "good":
        filtered_products = [p for p in filtered_products if
                           p["stock_quantity"] is not None and
                           p["stock_quantity"] > p["min_stock_level"]]

    # Sort products
    if sort_by == "name":
        filtered_products.sort(key=lambda x: x["name"])
    elif sort_by == "stock_asc":
        filtered_products.sort(key=lambda x: x["stock_quantity"] or 0)
    elif sort_by == "stock_desc":
        filtered_products.sort(key=lambda x: x["stock_quantity"] or 0, reverse=True)
    elif sort_by == "value_desc":
        filtered_products.sort(key=lambda x: (x["stock_quantity"] or 0) * x["cost"], reverse=True)

    # Display products
    if not filtered_products:
        st.info("No products match your filters.")
    else:
        for product in filtered_products:
            _render_product_stock_card(product)


def _render_product_stock_card(product: dict):
    """Render a product stock card."""
    stock = product["stock_quantity"]
    min_level = product["min_stock_level"]

    # Determine status
    if stock is None:
        status = "Not Tracked"
        status_color = C["muted"]
        status_icon = "➖"
    elif stock == 0:
        status = "Out of Stock"
        status_color = C["rose"]
        status_icon = "🚫"
    elif stock <= min_level:
        status = "Low Stock"
        status_color = C["amber"]
        status_icon = "⚠️"
    else:
        status = "In Stock"
        status_color = C["emerald"]
        status_icon = "✅"

    # Calculate inventory value
    inventory_value = (stock or 0) * product["cost"]

    st.markdown(f"""
    <div style="background:{C['surface']};border:1px solid {C['border']};
                border-radius:12px;padding:1.2rem;margin-bottom:1rem;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div style="flex:1;">
                <div style="display:flex;align-items:center;gap:.8rem;margin-bottom:.8rem;">
                    <span style="font-size:1.5rem">📦</span>
                    <div>
                        <h4 style="color:{C['text']};margin:0;font-size:1.1rem">{product['name']}</h4>
                        <div style="display:flex;align-items:center;gap:.5rem;margin-top:.3rem;">
                            <span style="background:{status_color}22;color:{status_color};
                                         padding:.15rem .6rem;border-radius:12px;font-size:.75rem;
                                         font-weight:600">{status_icon} {status}</span>
                        </div>
                    </div>
                </div>

                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));
                            gap:.8rem;">
                    <div>
                        <div style="color:{C['muted']};font-size:.7rem;text-transform:uppercase">Current Stock</div>
                        <div style="color:{C['text']};font-weight:600;font-size:1.1rem">
                            {stock if stock is not None else 'N/A'}
                        </div>
                    </div>
                    <div>
                        <div style="color:{C['muted']};font-size:.7rem;text-transform:uppercase">Min Level</div>
                        <div style="color:{C['text']};font-weight:600">{min_level}</div>
                    </div>
                    <div>
                        <div style="color:{C['muted']};font-size:.7rem;text-transform:uppercase">Unit Cost</div>
                        <div style="color:{C['text']};font-weight:600">${product['cost']:.2f}</div>
                    </div>
                    <div>
                        <div style="color:{C['muted']};font-size:.7rem;text-transform:uppercase">Total Value</div>
                        <div style="color:{C['emerald']};font-weight:600">${inventory_value:.2f}</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_alerts_management(business_id: int):
    """Render inventory alerts management."""
    st.markdown("### Inventory Alerts")

    # Get all alerts (resolved and unresolved)
    all_alerts = db.get_business_inventory_alerts(business_id, unresolved_only=False)
    unresolved_alerts = [a for a in all_alerts if not a["is_resolved"]]

    if not unresolved_alerts:
        st.success("🎉 No active inventory alerts! All stock levels are adequate.")
    else:
        st.warning(f"⚠️ You have {len(unresolved_alerts)} active inventory alerts.")

    # Alert filters
    col1, col2 = st.columns(2)
    with col1:
        alert_filter = st.selectbox(
            "Show Alerts",
            options=["unresolved", "all"],
            format_func=lambda x: "Active Alerts Only" if x == "unresolved" else "All Alerts"
        )

    with col2:
        alert_type_filter = st.selectbox(
            "Alert Type",
            options=["all", "out_of_stock", "low_stock"],
            format_func=lambda x: {
                "all": "All Types",
                "out_of_stock": "🚫 Out of Stock",
                "low_stock": "⚠️ Low Stock"
            }[x]
        )

    # Filter alerts
    filtered_alerts = all_alerts if alert_filter == "all" else unresolved_alerts

    if alert_type_filter != "all":
        filtered_alerts = [a for a in filtered_alerts if a["alert_type"] == alert_type_filter]

    if not filtered_alerts:
        st.info("No alerts match your filters.")
        return

    # Group alerts by type
    out_of_stock_alerts = [a for a in filtered_alerts if a["alert_type"] == "out_of_stock"]
    low_stock_alerts = [a for a in filtered_alerts if a["alert_type"] == "low_stock"]

    # Out of Stock Alerts
    if out_of_stock_alerts:
        st.markdown("#### 🚫 Out of Stock Items")
        for alert in out_of_stock_alerts:
            _render_alert_item(alert, "critical")

    # Low Stock Alerts
    if low_stock_alerts:
        st.markdown("#### ⚠️ Low Stock Items")
        for alert in low_stock_alerts:
            _render_alert_item(alert, "warning")

    # Bulk actions
    if unresolved_alerts:
        st.markdown("---")
        st.markdown("#### Bulk Actions")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Mark All Low Stock as Resolved", use_container_width=True):
                for alert in unresolved_alerts:
                    if alert["alert_type"] == "low_stock":
                        db.resolve_inventory_alert(alert["id"])
                st.success("All low stock alerts marked as resolved!")
                st.rerun()

        with col2:
            st.info("💡 Out of stock alerts are automatically resolved when stock is replenished.")


def _render_alert_item(alert: dict, severity: str):
    """Render a single alert item."""
    if severity == "critical":
        border_color = C["rose"]
        bg_color = f"{C['rose']}15"
        icon = "🚫"
    else:
        border_color = C["amber"]
        bg_color = f"{C['amber']}15"
        icon = "⚠️"

    # Format date
    created_date = alert["created_at"][:10]  # Just the date part

    resolved_badge = ""
    if alert["is_resolved"]:
        resolved_badge = f'<span style="background:{C["emerald"]}22;color:{C["emerald"]};padding:.15rem .5rem;border-radius:10px;font-size:.7rem;font-weight:600;">Resolved</span>'

    st.markdown(f"""
    <div style="background:{bg_color};border:1px solid {border_color};
                border-radius:10px;padding:1rem;margin-bottom:.8rem;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div style="flex:1;">
                <div style="display:flex;align-items:center;gap:.8rem;margin-bottom:.5rem;">
                    <span style="font-size:1.2rem">{icon}</span>
                    <div>
                        <strong style="color:{C['text']};font-size:1rem">{alert['product_name']}</strong>
                        {resolved_badge}
                    </div>
                </div>

                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));
                            gap:.8rem;color:{C['muted']};font-size:.85rem;">
                    <div>
                        <div style="color:{C['muted']};font-size:.7rem;text-transform:uppercase">Current Stock</div>
                        <div style="color:{border_color};font-weight:600;font-size:1.1rem">{alert['current_stock']}</div>
                    </div>
                    <div>
                        <div style="color:{C['muted']};font-size:.7rem;text-transform:uppercase">Threshold</div>
                        <div style="color:{C['text']};font-weight:600">{alert['threshold']}</div>
                    </div>
                    <div>
                        <div style="color:{C['muted']};font-size:.7rem;text-transform:uppercase">Alert Date</div>
                        <div style="color:{C['text']}">{created_date}</div>
                    </div>
                    {f'<div><div style="color:{C["muted"]};font-size:.7rem;text-transform:uppercase">SKU</div><div style="color:{C["text"]}">{alert["sku"]}</div></div>' if alert.get('sku') else ''}
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Action buttons (only for unresolved alerts)
    if not alert["is_resolved"]:
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button(f"✅ Resolve", key=f"resolve_{alert['id']}", use_container_width=True):
                db.resolve_inventory_alert(alert["id"])
                st.success("Alert marked as resolved!")
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def _render_inventory_reports(business_id: int):
    """Render inventory analytics and reports."""
    st.markdown("### Inventory Reports")

    # Get products data
    products = [
        item for item in db.get_business_products_services(business_id, active_only=True)
        if item["type"] == "product" and item["stock_quantity"] is not None
    ]

    if not products:
        st.info("📊 No inventory data available for reporting.")
        return

    # Inventory value analysis
    st.markdown("#### Inventory Value Analysis")

    # Calculate metrics
    total_value = sum(p["stock_quantity"] * p["cost"] for p in products)
    total_units = sum(p["stock_quantity"] for p in products)
    avg_unit_cost = total_value / total_units if total_units > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Inventory Value", f"${total_value:,.2f}")
    col2.metric("Total Units", f"{total_units:,}")
    col3.metric("Average Unit Cost", f"${avg_unit_cost:.2f}")

    # Top products by value
    products_data = []
    for p in products:
        products_data.append({
            "name": p["name"],
            "stock": p["stock_quantity"],
            "unit_cost": p["cost"],
            "total_value": p["stock_quantity"] * p["cost"],
            "category": p["category"] or "Uncategorized"
        })

    df = pd.DataFrame(products_data)

    if len(df) > 0:
        col1, col2 = st.columns(2)

        with col1:
            # Top products by value
            top_value = df.nlargest(10, "total_value")
            fig_value = px.bar(
                top_value,
                x="total_value",
                y="name",
                orientation="h",
                title="Top Products by Inventory Value",
                color="total_value",
                color_continuous_scale=["#f43f5e", "#6366f1"]
            )
            fig_value.update_layout(height=400)
            st.plotly_chart(fig_value, use_container_width=True)

        with col2:
            # Category distribution
            category_value = df.groupby("category")["total_value"].sum().reset_index()
            fig_cat = px.pie(
                category_value,
                values="total_value",
                names="category",
                title="Inventory Value by Category"
            )
            fig_cat.update_layout(height=400)
            st.plotly_chart(fig_cat, use_container_width=True)

        # Detailed inventory table
        st.markdown("#### Detailed Inventory Report")

        display_df = df.copy()
        display_df = display_df.sort_values("total_value", ascending=False)

        st.dataframe(
            display_df.style
            .format({
                "unit_cost": "${:.2f}",
                "total_value": "${:,.2f}",
                "stock": "{:,}"
            })
            .background_gradient(subset=["total_value"], cmap="Greens")
            .background_gradient(subset=["stock"], cmap="Blues"),
            use_container_width=True,
            column_config={
                "name": "Product Name",
                "stock": st.column_config.NumberColumn("Stock Quantity"),
                "unit_cost": st.column_config.NumberColumn("Unit Cost", format="$%.2f"),
                "total_value": st.column_config.NumberColumn("Total Value", format="$%.2f"),
                "category": "Category"
            }
        )

        # Export functionality
        st.markdown("#### Export Options")
        col1, col2 = st.columns(2)

        with col1:
            csv = df.to_csv(index=False)
            st.download_button(
                "📄 Download as CSV",
                csv,
                file_name=f"inventory_report_{business_id}.csv",
                mime="text/csv",
                use_container_width=True
            )


def get_inventory_alerts_count(business_id: int) -> dict:
    """Get count of inventory alerts for dashboard."""
    alerts = db.get_business_inventory_alerts(business_id, unresolved_only=True)

    out_of_stock = len([a for a in alerts if a["alert_type"] == "out_of_stock"])
    low_stock = len([a for a in alerts if a["alert_type"] == "low_stock"])

    return {
        'total_alerts': len(alerts),
        'out_of_stock': out_of_stock,
        'low_stock': low_stock
    }