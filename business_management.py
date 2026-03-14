"""
business_management.py
Business registration, selection, and management for multi-business platform.
"""

import streamlit as st
from typing import Optional
import database as db

# Design tokens matching app.py
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

BUSINESS_TYPES = {
    'retail': {
        'name': 'Retail Store',
        'description': 'Physical or online store selling products',
        'icon': '🛍️'
    },
    'gym': {
        'name': 'Gym/Fitness Center',
        'description': 'Fitness center, gym, or wellness facility',
        'icon': '💪'
    },
    'coaching': {
        'name': 'Coaching Center',
        'description': 'Educational coaching, tutoring, or training',
        'icon': '📚'
    },
    'service': {
        'name': 'Service Business',
        'description': 'Professional services, consulting, or other services',
        'icon': '🛠️'
    }
}


def render_business_setup():
    """Render business setup/registration form."""
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{C['indigo']}22,{C['surface2']});
                border:1px solid {C['border']};border-radius:14px;
                padding:2rem;margin-bottom:2rem;text-align:center;">
        <div style="font-size:2.5rem;margin-bottom:1rem">🏢</div>
        <h2 style="color:{C['text']};margin:0 0 .5rem 0;">Welcome to RetailBrain AI</h2>
        <p style="color:{C['muted']};margin:0;font-size:.9rem;">
            Let's set up your business to get started with analytics and insights
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("business_setup"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Business Information**")
            business_name = st.text_input(
                "Business Name *",
                placeholder="e.g. My Retail Store"
            )

            business_type = st.selectbox(
                "Business Type *",
                options=list(BUSINESS_TYPES.keys()),
                format_func=lambda x: f"{BUSINESS_TYPES[x]['icon']} {BUSINESS_TYPES[x]['name']}"
            )

            description = st.text_area(
                "Description (Optional)",
                placeholder="Brief description of your business..."
            )

        with col2:
            st.markdown("**Contact Information**")
            address = st.text_area(
                "Address (Optional)",
                placeholder="Business address..."
            )

            phone = st.text_input(
                "Phone (Optional)",
                placeholder="+1 (555) 123-4567"
            )

            email = st.text_input(
                "Email (Optional)",
                placeholder="business@example.com"
            )

        # Show business type info
        if business_type:
            type_info = BUSINESS_TYPES[business_type]
            st.info(f"**{type_info['name']}**: {type_info['description']}")

        submitted = st.form_submit_button("🚀 Create Business", use_container_width=True)

        if submitted:
            if not business_name.strip():
                st.error("Business name is required")
                return None

            try:
                user = st.session_state.get("user")
                if not user:
                    st.error("User not found")
                    return None

                business_id = db.create_business(
                    name=business_name.strip(),
                    business_type=business_type,
                    owner_id=user["id"],
                    description=description.strip() if description else None,
                    address=address.strip() if address else None,
                    phone=phone.strip() if phone else None,
                    email=email.strip() if email else None
                )

                st.success(f"✅ Business '{business_name}' created successfully!")
                st.session_state["selected_business_id"] = business_id
                st.rerun()

            except Exception as e:
                st.error(f"Error creating business: {e}")

    return None


def render_business_selector(user_id: int) -> Optional[int]:
    """Render business selector dropdown. Returns selected business ID."""
    businesses = db.get_user_businesses(user_id)

    if not businesses:
        return None

    # Business selector
    business_options = {
        f"{BUSINESS_TYPES.get(b['business_type'], {}).get('icon', '🏢')} {b['name']} ({b['role']})": b['id']
        for b in businesses
    }

    # Get current selection
    current_business_id = st.session_state.get("selected_business_id")
    current_index = 0

    if current_business_id:
        for i, business in enumerate(businesses):
            if business['id'] == current_business_id:
                current_index = i
                break

    selected_label = st.selectbox(
        "Select Business",
        options=list(business_options.keys()),
        index=current_index,
        label_visibility="collapsed"
    )

    selected_business_id = business_options[selected_label]

    # Store in session state
    if selected_business_id != st.session_state.get("selected_business_id"):
        st.session_state["selected_business_id"] = selected_business_id
        st.rerun()

    return selected_business_id


def get_current_business_info() -> Optional[dict]:
    """Get current selected business information."""
    business_id = st.session_state.get("selected_business_id")
    if not business_id:
        return None
    return db.get_business_by_id(business_id)


def render_business_dashboard_header():
    """Render the business dashboard header."""
    business = get_current_business_info()
    if not business:
        return

    business_type = BUSINESS_TYPES.get(business['business_type'], {})
    icon = business_type.get('icon', '🏢')
    type_name = business_type.get('name', business['business_type'].title())

    st.markdown(f"""
    <div style="background:{C['surface']};border:1px solid {C['border']};
                border-radius:12px;padding:1rem 1.25rem;margin-bottom:1.5rem;
                display:flex;align-items:center;gap:1rem;">
        <div style="font-size:2rem">{icon}</div>
        <div>
            <div style="font-size:1.2rem;font-weight:700;color:{C['text']}">{business['name']}</div>
            <div style="font-size:.8rem;color:{C['muted']}">{type_name}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def check_business_access(user_id: int, business_id: int) -> Optional[str]:
    """Check if user has access to business. Returns role or None."""
    return db.user_has_business_access(user_id, business_id)


def render_business_settings():
    """Render business settings page."""
    business = get_current_business_info()
    if not business:
        st.error("No business selected")
        return

    user = st.session_state.get("user")
    if not user:
        st.error("User not found")
        return

    # Check permissions
    user_role = check_business_access(user["id"], business["id"])
    if user_role not in ["owner", "admin"]:
        st.error("You don't have permission to manage this business")
        return

    st.markdown("### Business Settings")

    tab1, tab2, tab3 = st.tabs(["Basic Info", "Team Members", "Advanced"])

    with tab1:
        st.markdown("**Business Information**")

        with st.form("update_business"):
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input("Business Name", value=business['name'])
                business_type = st.selectbox(
                    "Business Type",
                    options=list(BUSINESS_TYPES.keys()),
                    index=list(BUSINESS_TYPES.keys()).index(business['business_type']),
                    format_func=lambda x: f"{BUSINESS_TYPES[x]['icon']} {BUSINESS_TYPES[x]['name']}"
                )
                description = st.text_area("Description", value=business['description'] or "")

            with col2:
                address = st.text_area("Address", value=business['address'] or "")
                phone = st.text_input("Phone", value=business['phone'] or "")
                email = st.text_input("Email", value=business['email'] or "")

            if st.form_submit_button("💾 Update Business"):
                try:
                    db.update_business(
                        business_id=business['id'],
                        name=name,
                        business_type=business_type,
                        description=description,
                        address=address,
                        phone=phone,
                        email=email
                    )
                    st.success("✅ Business updated successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error updating business: {e}")

    with tab2:
        st.markdown("**Team Members**")

        # Show current team members
        team_members = db.get_business_users(business['id'])

        if team_members:
            st.markdown("**Current Team:**")
            for member in team_members:
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"**{member['username']}** ({member['email']})")
                with col2:
                    role_badge_color = {
                        'owner': C['emerald'],
                        'admin': C['indigo'],
                        'staff': C['amber']
                    }.get(member['role'], C['slate'])
                    st.markdown(f'''
                    <span style="background:{role_badge_color}22;color:{role_badge_color};
                                 padding:.2rem .6rem;border-radius:12px;font-size:.8rem;
                                 font-weight:600">{member['role'].upper()}</span>
                    ''', unsafe_allow_html=True)
                with col3:
                    if member['role'] != 'owner' and user_role == 'owner':
                        if st.button("Remove", key=f"remove_{member['id']}", type="secondary"):
                            db.remove_user_from_business(business['id'], member['id'])
                            st.success(f"Removed {member['username']} from business")
                            st.rerun()

        # Add new team member
        with st.expander("➕ Add Team Member"):
            with st.form("add_team_member"):
                new_member_email = st.text_input("User Email")
                new_member_role = st.selectbox("Role", ["staff", "admin"])

                if st.form_submit_button("Add Member"):
                    if new_member_email:
                        # Find user by email
                        new_user = db.get_user_by_email(new_member_email)
                        if new_user:
                            try:
                                db.add_user_to_business(business['id'], new_user['id'], new_member_role)
                                st.success(f"✅ Added {new_user['username']} as {new_member_role}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error adding team member: {e}")
                        else:
                            st.error("User not found with that email address")

    with tab3:
        st.markdown("**Advanced Settings**")

        if user_role == 'owner':
            st.warning("⚠️ **Danger Zone**")

            with st.expander("🗑️ Delete Business", expanded=False):
                st.error("**This action cannot be undone!**")
                st.write("Deleting this business will:")
                st.write("- Remove all products/services")
                st.write("- Delete all transaction history")
                st.write("- Remove all team members")
                st.write("- Permanently delete all data")

                if st.text_input("Type 'DELETE' to confirm") == "DELETE":
                    if st.button("🗑️ Permanently Delete Business", type="primary"):
                        # Implement business deletion
                        st.error("Business deletion coming soon...")
        else:
            st.info("Only business owners can access advanced settings.")