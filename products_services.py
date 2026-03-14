"""
products_services.py
Product and service management for multi-business platform.
"""

import streamlit as st
import pandas as pd
from typing import Optional
import database as db
import business_management as bm
from ui_utils import show_friendly_error

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


def render_products_services_page():
    """Render the main products/services management page."""
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
            <h2 style="color:{C['text']};margin:0;">Products & Services</h2>
            <p style="color:{C['muted']};margin:0;font-size:.9rem;">
                Manage your inventory and service offerings
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tabs
    tab1, tab2 = st.tabs(["📦 All Items", "➕ Add New"])

    with tab1:
        _render_products_services_list(business["id"], user_role)

    with tab2:
        if user_role in ["owner", "admin", "staff"]:
            _render_add_product_service_form(business["id"])
        else:
            st.error("You don't have permission to add products/services")


def _render_products_services_list(business_id: int, user_role: str):
    """Render the list of products/services."""
    items = db.get_business_products_services(business_id, active_only=False)

    if not items:
        st.info("📦 No products or services found. Add your first item in the 'Add New' tab.")
        return

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_type = st.selectbox(
            "Filter by Type",
            options=["all", "product", "service"],
            format_func=lambda x: {"all": "All Items", "product": "📦 Products", "service": "🛠️ Services"}[x]
        )

    with col2:
        filter_status = st.selectbox(
            "Filter by Status",
            options=["all", "active", "inactive"],
            format_func=lambda x: {"all": "All", "active": "Active", "inactive": "Inactive"}[x]
        )

    with col3:
        search = st.text_input("🔍 Search", placeholder="Product/service name...")

    # Apply filters
    filtered_items = items

    if filter_type != "all":
        filtered_items = [item for item in filtered_items if item["type"] == filter_type]

    if filter_status == "active":
        filtered_items = [item for item in filtered_items if item["is_active"] == 1]
    elif filter_status == "inactive":
        filtered_items = [item for item in filtered_items if item["is_active"] == 0]

    if search:
        filtered_items = [
            item for item in filtered_items
            if search.lower() in item["name"].lower()
        ]

    if not filtered_items:
        st.info("No items match your filters.")
        return

    # Display items
    for item in filtered_items:
        with st.container():
            _render_product_service_card(item, user_role)


def _render_product_service_card(item: dict, user_role: str):
    """Render a single product/service card."""
    is_product = item["type"] == "product"
    icon = "📦" if is_product else "🛠️"

    # Status indicators
    status_color = C["emerald"] if item["is_active"] else C["muted"]
    status_text = "Active" if item["is_active"] else "Inactive"

    # Stock warning for products
    stock_warning = ""
    if is_product and item["stock_quantity"] is not None:
        if item["stock_quantity"] <= 0:
            stock_warning = f'<span style="color:{C["rose"]};font-weight:600;">OUT OF STOCK</span>'
        elif item["stock_quantity"] <= item["min_stock_level"]:
            stock_warning = f'<span style="color:{C["amber"]};font-weight:600;">LOW STOCK</span>'

    # Calculate profit margin
    profit_margin = ((item["price"] - item["cost"]) / item["price"] * 100) if item["price"] > 0 else 0

    st.markdown(f"""
    <div style="background:{C['surface']};border:1px solid {C['border']};
                border-radius:12px;padding:1.2rem;margin-bottom:1rem;">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;">
            <div style="flex:1;">
                <div style="display:flex;align-items:center;gap:.8rem;margin-bottom:.5rem;">
                    <span style="font-size:1.5rem">{icon}</span>
                    <div>
                        <h4 style="color:{C['text']};margin:0;font-size:1.1rem">{item['name']}</h4>
                        <div style="display:flex;align-items:center;gap:1rem;margin-top:.3rem;">
                            <span style="background:{status_color}22;color:{status_color};
                                         padding:.15rem .5rem;border-radius:10px;font-size:.7rem;
                                         font-weight:600">{status_text}</span>
                            {stock_warning}
                        </div>
                    </div>
                </div>

                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));
                            gap:.8rem;margin-top:.8rem;">
                    <div>
                        <div style="color:{C['muted']};font-size:.7rem;text-transform:uppercase">Price</div>
                        <div style="color:{C['text']};font-weight:600">${item['price']:.2f}</div>
                    </div>
                    <div>
                        <div style="color:{C['muted']};font-size:.7rem;text-transform:uppercase">Cost</div>
                        <div style="color:{C['text']};font-weight:600">${item['cost']:.2f}</div>
                    </div>
                    <div>
                        <div style="color:{C['muted']};font-size:.7rem;text-transform:uppercase">Margin</div>
                        <div style="color:{C['emerald'] if profit_margin > 0 else C['rose']};font-weight:600">
                            {profit_margin:.1f}%
                        </div>
                    </div>
    """, unsafe_allow_html=True)

    # Additional info for products
    if is_product and item["stock_quantity"] is not None:
        st.markdown(f"""
                    <div>
                        <div style="color:{C['muted']};font-size:.7rem;text-transform:uppercase">Stock</div>
                        <div style="color:{C['text']};font-weight:600">{item['stock_quantity']}</div>
                    </div>
        """, unsafe_allow_html=True)

    # Additional info for services
    if not is_product and item["duration_days"]:
        st.markdown(f"""
                    <div>
                        <div style="color:{C['muted']};font-size:.7rem;text-transform:uppercase">Duration</div>
                        <div style="color:{C['text']};font-weight:600">{item['duration_days']} days</div>
                    </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Description
    if item["description"]:
        st.markdown(f"""
        <div style="color:{C['muted']};font-size:.85rem;margin-top:.8rem;
                    padding-top:.8rem;border-top:1px solid {C['border']};">
            {item['description']}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Action buttons
    if user_role in ["owner", "admin"]:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("✏️ Edit", key=f"edit_{item['id']}", use_container_width=True):
                st.session_state[f"edit_item_{item['id']}"] = True
                st.rerun()

        with col2:
            if is_product:
                if st.button("📊 Stock", key=f"stock_{item['id']}", use_container_width=True):
                    st.session_state[f"manage_stock_{item['id']}"] = True
                    st.rerun()

        with col3:
            toggle_text = "Deactivate" if item["is_active"] else "Activate"
            if st.button(f"🔄 {toggle_text}", key=f"toggle_{item['id']}", use_container_width=True):
                db.update_product_service(item["id"], is_active=1 - item["is_active"])
                st.success(f"Item {toggle_text.lower()}d successfully!")
                st.rerun()

        with col4:
            if st.button("🗑️ Delete", key=f"delete_{item['id']}", type="secondary", use_container_width=True):
                db.delete_product_service(item["id"])
                st.success("Item deleted successfully!")
                st.rerun()

    # Edit form
    if st.session_state.get(f"edit_item_{item['id']}"):
        _render_edit_product_service_form(item)

    # Stock management
    if st.session_state.get(f"manage_stock_{item['id']}"):
        _render_stock_management_form(item)


def _render_add_product_service_form(business_id: int):
    """Render form to add new product/service."""
    st.markdown("### Add New Product or Service")

    with st.form("add_product_service"):
        # Basic info
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Name *", placeholder="Product/Service name")
            item_type = st.selectbox("Type *", ["product", "service"])
            price = st.number_input("Price *", min_value=0.0, step=0.01, format="%.2f")
            cost = st.number_input("Cost", min_value=0.0, step=0.01, format="%.2f", value=0.0)

        with col2:
            category = st.text_input("Category", placeholder="e.g. Electronics, Beverages")
            sku = st.text_input("SKU/Code", placeholder="Product code or identifier")

            # Show relevant fields based on type
            if item_type == "product":
                stock_quantity = st.number_input("Initial Stock Quantity", min_value=0, value=0)
                min_stock_level = st.number_input("Low Stock Alert Level", min_value=1, value=5)
                duration_days = None
            else:  # service
                duration_days = st.number_input(
                    "Duration (days)",
                    min_value=1,
                    value=30,
                    help="For memberships or recurring services"
                )
                stock_quantity = None
                min_stock_level = None

        description = st.text_area("Description", placeholder="Optional description...")

        # Calculate and show profit margin
        if price > 0:
            margin = ((price - cost) / price) * 100
            margin_color = C["emerald"] if margin > 0 else C["rose"]
            st.markdown(f"""
            <div style="background:{C['surface2']};border-radius:8px;padding:.8rem;">
                <strong style="color:{margin_color}">Profit Margin: {margin:.1f}%</strong>
                <br><small style="color:{C['muted']}">Profit per unit: ${price - cost:.2f}</small>
            </div>
            """, unsafe_allow_html=True)

        submitted = st.form_submit_button("➕ Add Item", use_container_width=True)

        if submitted:
            if not name.strip():
                st.error("Name is required")
                return

            if price <= 0:
                st.error("Price must be greater than 0")
                return

            try:
                item_id = db.create_product_service(
                    business_id=business_id,
                    name=name.strip(),
                    type=item_type,
                    price=price,
                    cost=cost,
                    stock_quantity=stock_quantity,
                    min_stock_level=min_stock_level,
                    duration_days=duration_days,
                    description=description.strip() if description else None,
                    category=category.strip() if category else None,
                    sku=sku.strip() if sku else None
                )

                st.success(f"✅ {item_type.title()} '{name}' added successfully!")
                st.rerun()

            except Exception as e:
                show_friendly_error("Unable to add item right now.", "products_services.add_item", e)


def _render_edit_product_service_form(item: dict):
    """Render form to edit existing product/service."""
    st.markdown("### Edit Item")

    with st.form(f"edit_item_{item['id']}"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Name *", value=item['name'])
            price = st.number_input("Price *", min_value=0.0, step=0.01, value=float(item['price']))
            cost = st.number_input("Cost", min_value=0.0, step=0.01, value=float(item['cost']))

        with col2:
            category = st.text_input("Category", value=item['category'] or "")
            sku = st.text_input("SKU/Code", value=item['sku'] or "")

            if item['type'] == "service" and item['duration_days']:
                duration_days = st.number_input("Duration (days)", min_value=1, value=item['duration_days'])
            else:
                duration_days = item['duration_days']

        description = st.text_area("Description", value=item['description'] or "")

        col_save, col_cancel = st.columns(2)

        with col_save:
            if st.form_submit_button("💾 Save Changes", use_container_width=True):
                try:
                    db.update_product_service(
                        product_service_id=item['id'],
                        name=name,
                        price=price,
                        cost=cost,
                        category=category if category else None,
                        sku=sku if sku else None,
                        duration_days=duration_days,
                        description=description if description else None
                    )
                    st.success("✅ Item updated successfully!")
                    st.session_state[f"edit_item_{item['id']}"] = False
                    st.rerun()
                except Exception as e:
                    show_friendly_error("Unable to update item right now.", "products_services.update_item", e)

        with col_cancel:
            if st.form_submit_button("❌ Cancel", use_container_width=True):
                st.session_state[f"edit_item_{item['id']}"] = False
                st.rerun()


def _render_stock_management_form(item: dict):
    """Render stock management form for products."""
    st.markdown("### Stock Management")

    current_stock = item['stock_quantity'] or 0

    with st.form(f"stock_mgmt_{item['id']}"):
        st.info(f"**Current Stock:** {current_stock} units")

        col1, col2 = st.columns(2)

        with col1:
            action = st.selectbox("Action", ["add", "remove", "set"])
            quantity = st.number_input("Quantity", min_value=1, value=1)

        with col2:
            if action == "add":
                new_stock = current_stock + quantity
                st.success(f"New stock will be: **{new_stock}** units")
            elif action == "remove":
                new_stock = max(0, current_stock - quantity)
                st.warning(f"New stock will be: **{new_stock}** units")
            else:  # set
                new_stock = quantity
                st.info(f"Stock will be set to: **{new_stock}** units")

        notes = st.text_input("Notes (optional)", placeholder="Reason for stock change...")

        col_save, col_cancel = st.columns(2)

        with col_save:
            if st.form_submit_button("✅ Update Stock", use_container_width=True):
                try:
                    if action == "add":
                        final_stock = current_stock + quantity
                    elif action == "remove":
                        final_stock = max(0, current_stock - quantity)
                    else:  # set
                        final_stock = quantity

                    db.update_stock_quantity(item['id'], final_stock)
                    st.success(f"✅ Stock updated! New quantity: {final_stock}")
                    st.session_state[f"manage_stock_{item['id']}"] = False
                    st.rerun()
                except Exception as e:
                    show_friendly_error("Unable to update stock right now.", "products_services.update_stock", e)

        with col_cancel:
            if st.form_submit_button("❌ Cancel", use_container_width=True):
                st.session_state[f"manage_stock_{item['id']}"] = False
                st.rerun()


def get_business_inventory_summary(business_id: int) -> dict:
    """Get inventory summary for dashboard."""
    items = db.get_business_products_services(business_id, active_only=True)

    total_items = len(items)
    total_products = len([item for item in items if item['type'] == 'product'])
    total_services = len([item for item in items if item['type'] == 'service'])

    # Calculate total inventory value
    total_value = sum(
        (item['stock_quantity'] or 0) * item['cost']
        for item in items if item['type'] == 'product'
    )

    # Low stock alerts
    low_stock_items = db.get_low_stock_products(business_id)

    return {
        'total_items': total_items,
        'total_products': total_products,
        'total_services': total_services,
        'total_inventory_value': total_value,
        'low_stock_count': len(low_stock_items)
    }