"""
gym_management.py
Comprehensive gym management system for RetailBrain AI platform.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
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


def render_gym_management_page():
    """Main gym management page."""
    business = bm.get_current_business_info()
    if not business or business["business_type"] != "gym":
        st.error("🏋️‍♂️ This page is only available for gym businesses. Please select a gym from your businesses or create one.")
        return

    user = st.session_state.get("user")
    user_role = bm.check_business_access(user["id"], business["id"]) if user else None

    if not user_role:
        st.error("You don't have access to this gym.")
        return

    # Header
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;">
        <div>
            <h2 style="color:{C['text']};margin:0;">🏋️‍♂️ Gym Management</h2>
            <p style="color:{C['muted']};margin:0;font-size:.9rem;">
                Member check-ins, memberships, and facility management
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Quick stats
    today = datetime.now().strftime('%Y-%m-%d')
    daily_summary = db.get_gym_daily_summary(business["id"], today)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div style="background:{C['surface']};border:1px solid {C['border']};
                    border-radius:12px;padding:1rem;text-align:center;">
            <div style="color:{C['muted']};font-size:0.8rem;text-transform:uppercase">Today's Check-ins</div>
            <div style="color:{C['emerald']};font-weight:700;font-size:1.5rem;margin:0.3rem 0">
                {daily_summary['daily_check_ins']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background:{C['surface']};border:1px solid {C['border']};
                    border-radius:12px;padding:1rem;text-align:center;">
            <div style="color:{C['muted']};font-size:0.8rem;text-transform:uppercase">Day Pass Revenue</div>
            <div style="color:{C['indigo']};font-weight:700;font-size:1.5rem;margin:0.3rem 0">
                ${daily_summary['daily_revenue']:.0f}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="background:{C['surface']};border:1px solid {C['border']};
                    border-radius:12px;padding:1rem;text-align:center;">
            <div style="color:{C['muted']};font-size:0.8rem;text-transform:uppercase">Active Members</div>
            <div style="color:{C['cyan']};font-weight:700;font-size:1.5rem;margin:0.3rem 0">
                {daily_summary['total_active_members']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        operational_pct = (daily_summary['operational_equipment'] / daily_summary['total_equipment'] * 100) if daily_summary['total_equipment'] > 0 else 100
        equipment_color = C['emerald'] if operational_pct >= 90 else C['amber'] if operational_pct >= 70 else C['rose']
        st.markdown(f"""
        <div style="background:{C['surface']};border:1px solid {C['border']};
                    border-radius:12px;padding:1rem;text-align:center;">
            <div style="color:{C['muted']};font-size:0.8rem;text-transform:uppercase">Equipment Status</div>
            <div style="color:{equipment_color};font-weight:700;font-size:1.5rem;margin:0.3rem 0">
                {operational_pct:.0f}%
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Navigation tabs
    tabs = st.tabs([
        "🚪 Check-in/Out",
        "👥 Members",
        "💳 Memberships",
        "🎫 Day Passes",
        "🏋️‍♀️ Equipment",
        "📊 Reports"
    ])

    with tabs[0]:
        render_gym_checkin_page(business["id"], user_role)

    with tabs[1]:
        render_gym_members_page(business["id"], user_role)

    with tabs[2]:
        render_gym_memberships_page(business["id"], user_role)

    with tabs[3]:
        render_gym_day_passes_page(business["id"], user_role)

    with tabs[4]:
        render_gym_equipment_page(business["id"], user_role)

    with tabs[5]:
        render_gym_reports_page(business["id"])


def render_gym_checkin_page(business_id: int, user_role: str):
    """Gym check-in/check-out interface."""
    st.markdown("### 🚪 Member Check-in")

    col_checkin, col_history = st.columns([1, 1])

    with col_checkin:
        st.markdown("#### Quick Check-in")

        # Member lookup
        member_lookup = st.text_input("🔍 Member ID or Name", placeholder="Enter member ID or search by name...")

        if member_lookup:
            # Search members
            members = db.get_gym_members(business_id)
            matching_members = [
                m for m in members
                if member_lookup.lower() in m['member_id'].lower() or
                   member_lookup.lower() in f"{m['first_name']} {m['last_name']}".lower()
            ]

            if matching_members:
                member = st.selectbox(
                    "Select Member:",
                    options=matching_members,
                    format_func=lambda x: f"{x['member_id']} - {x['first_name']} {x['last_name']}"
                )

                if member:
                    # Check membership status
                    active_memberships = db.get_gym_memberships(business_id, member['id'], active_only=True)

                    col_entry1, col_entry2 = st.columns(2)

                    with col_entry1:
                        if active_memberships:
                            st.success(f"✅ Active Membership: {active_memberships[0]['membership_type_name']}")
                            if st.button("🚪 Check In (Membership)", use_container_width=True):
                                check_in_id = db.create_gym_check_in(
                                    business_id, member['id'], 'membership',
                                    checked_in_by=st.session_state.get('user', {}).get('id')
                                )
                                st.success(f"✅ {member['first_name']} checked in successfully!")
                                st.rerun()
                        else:
                            st.warning("⚠️ No active membership")

                    with col_entry2:
                        # Day pass option
                        day_pass_price = st.number_input("Day Pass Price ($)", min_value=0.0, value=15.0, step=1.0)
                        payment_method = st.selectbox("Payment Method",
                                                    ['cash', 'card', 'digital', 'bank_transfer'])

                        if st.button("🎫 Purchase Day Pass", use_container_width=True):
                            check_in_id = db.create_gym_check_in(
                                business_id, member['id'], 'day_pass',
                                amount_paid=day_pass_price,
                                payment_method=payment_method,
                                checked_in_by=st.session_state.get('user', {}).get('id')
                            )
                            st.success(f"✅ Day pass purchased! {member['first_name']} checked in.")
                            st.rerun()

            else:
                st.info("🔍 No members found. Check the member ID or add a new member.")

    with col_history:
        st.markdown("#### Today's Check-ins")
        today = datetime.now().strftime('%Y-%m-%d')
        check_ins = db.get_gym_check_ins(business_id, date_filter=today, limit=10)

        if check_ins:
            for checkin in check_ins:
                checkin_time = datetime.fromisoformat(checkin['check_in_time']).strftime('%H:%M')
                entry_icon = "💳" if checkin['entry_type'] == 'membership' else "🎫"

                col_name, col_time, col_action = st.columns([2, 1, 1])

                with col_name:
                    st.markdown(f"{entry_icon} **{checkin['first_name']} {checkin['last_name']}**")
                    st.caption(f"ID: {checkin['custom_member_id']}")

                with col_time:
                    st.markdown(f"**{checkin_time}**")
                    if checkin['amount_paid'] > 0:
                        st.caption(f"${checkin['amount_paid']:.0f}")

                with col_action:
                    if not checkin['check_out_time']:
                        if st.button("Check Out", key=f"out_{checkin['id']}", type="secondary"):
                            db.update_gym_check_out(checkin['id'])
                            st.success("✅ Checked out!")
                            st.rerun()
                    else:
                        checkout_time = datetime.fromisoformat(checkin['check_out_time']).strftime('%H:%M')
                        st.caption(f"Out: {checkout_time}")

                st.markdown("---")
        else:
            st.info("📋 No check-ins today yet.")


def render_gym_members_page(business_id: int, user_role: str):
    """Gym members management."""
    tab1, tab2 = st.tabs(["👥 All Members", "➕ Add Member"])

    with tab1:
        st.markdown("### 👥 Gym Members")

        # Search and filters
        col1, col2 = st.columns(2)
        with col1:
            search = st.text_input("🔍 Search Members", placeholder="Name or Member ID...")
        with col2:
            show_inactive = st.checkbox("Show Inactive Members")

        # Get members
        members = db.get_gym_members(business_id, active_only=not show_inactive)

        if search:
            members = [
                m for m in members
                if search.lower() in f"{m['first_name']} {m['last_name']}".lower() or
                   search.lower() in m['member_id'].lower()
            ]

        if members:
            for member in members:
                # Get active memberships
                memberships = db.get_gym_memberships(business_id, member['id'], active_only=True)

                with st.container():
                    st.markdown(f"""
                    <div style="background:{C['surface']};border:1px solid {C['border']};
                                border-radius:12px;padding:1.2rem;margin-bottom:1rem;">
                    """, unsafe_allow_html=True)

                    col_info, col_status, col_actions = st.columns([2, 1, 1])

                    with col_info:
                        status_color = C['emerald'] if member['is_active'] else C['muted']
                        st.markdown(f"""
                        <h4 style="color:{C['text']};margin:0;">
                            {member['first_name']} {member['last_name']}
                        </h4>
                        <div style="color:{C['muted']};margin-bottom:0.5rem;">
                            ID: {member['member_id']} •
                            <span style="color:{status_color};">
                                {'Active' if member['is_active'] else 'Inactive'}
                            </span>
                        </div>
                        """, unsafe_allow_html=True)

                        if member['email']:
                            st.caption(f"📧 {member['email']}")
                        if member['phone']:
                            st.caption(f"📱 {member['phone']}")

                    with col_status:
                        if memberships:
                            membership = memberships[0]
                            end_date = datetime.strptime(membership['end_date'], '%Y-%m-%d')
                            days_left = (end_date - datetime.now()).days

                            if days_left > 7:
                                st.success(f"✅ Active\n({days_left} days)")
                            elif days_left > 0:
                                st.warning(f"⚠️ Expiring\n({days_left} days)")
                            else:
                                st.error("❌ Expired")

                            st.caption(f"{membership['membership_type_name']}")
                        else:
                            st.info("💳 No active membership")

                    with col_actions:
                        if user_role in ['owner', 'admin']:
                            if st.button("✏️ Edit", key=f"edit_member_{member['id']}"):
                                st.session_state[f'edit_member_{member["id"]}'] = True
                                st.rerun()

                    st.markdown("</div>", unsafe_allow_html=True)

                    # Edit form
                    if st.session_state.get(f'edit_member_{member["id"]}', False):
                        _render_edit_member_form(member)

        else:
            st.info("👥 No members found. Add your first member in the 'Add Member' tab.")

    with tab2:
        if user_role in ['owner', 'admin', 'staff']:
            _render_add_member_form(business_id)
        else:
            st.error("You don't have permission to add members.")


def _render_add_member_form(business_id: int):
    """Form to add new member."""
    st.markdown("### ➕ Add New Member")

    with st.form("add_gym_member"):
        col1, col2 = st.columns(2)

        with col1:
            member_id = st.text_input("Member ID *", placeholder="e.g., GYM001")
            first_name = st.text_input("First Name *")
            last_name = st.text_input("Last Name *")
            email = st.text_input("Email")

        with col2:
            phone = st.text_input("Phone Number")
            joining_date = st.date_input("Joining Date", value=None)
            emergency_contact_name = st.text_input("Emergency Contact Name")
            emergency_contact_phone = st.text_input("Emergency Contact Phone")

        medical_conditions = st.text_area("Medical Conditions / Notes",
                                        placeholder="Any medical conditions or special notes...")

        if st.form_submit_button("➕ Add Member", use_container_width=True):
            if not member_id or not first_name or not last_name:
                st.error("Member ID, First Name, and Last Name are required.")
                return

            # Check if member ID already exists
            existing = db.get_gym_member_by_member_id(business_id, member_id)
            if existing:
                st.error(f"Member ID '{member_id}' already exists.")
                return

            try:
                new_member_id = db.create_gym_member(
                    business_id=business_id,
                    member_id=member_id,
                    first_name=first_name,
                    last_name=last_name,
                    email=email if email else None,
                    phone=phone if phone else None,
                    joining_date=joining_date.isoformat() if joining_date else None,
                    emergency_contact_name=emergency_contact_name if emergency_contact_name else None,
                    emergency_contact_phone=emergency_contact_phone if emergency_contact_phone else None,
                    medical_conditions=medical_conditions if medical_conditions else None
                )

                st.success(f"✅ Member '{first_name} {last_name}' added successfully!")
                st.rerun()

            except Exception as e:
                show_friendly_error("Unable to add member right now.", "gym_management.add_member", e)


def _render_edit_member_form(member: dict):
    """Form to edit existing member."""
    st.markdown("### ✏️ Edit Member")

    with st.form(f"edit_member_{member['id']}"):
        col1, col2 = st.columns(2)

        with col1:
            first_name = st.text_input("First Name", value=member['first_name'])
            last_name = st.text_input("Last Name", value=member['last_name'])
            email = st.text_input("Email", value=member['email'] or "")

        with col2:
            phone = st.text_input("Phone", value=member['phone'] or "")
            emergency_contact_name = st.text_input("Emergency Contact",
                                                  value=member['emergency_contact_name'] or "")
            emergency_contact_phone = st.text_input("Emergency Phone",
                                                   value=member['emergency_contact_phone'] or "")

        medical_conditions = st.text_area("Medical Conditions",
                                        value=member['medical_conditions'] or "")
        is_active = st.checkbox("Active Member", value=bool(member['is_active']))

        col_save, col_cancel = st.columns(2)

        with col_save:
            if st.form_submit_button("💾 Save Changes", use_container_width=True):
                try:
                    db.update_gym_member(
                        member['id'],
                        first_name=first_name,
                        last_name=last_name,
                        email=email if email else None,
                        phone=phone if phone else None,
                        emergency_contact_name=emergency_contact_name if emergency_contact_name else None,
                        emergency_contact_phone=emergency_contact_phone if emergency_contact_phone else None,
                        medical_conditions=medical_conditions if medical_conditions else None,
                        is_active=1 if is_active else 0
                    )
                    st.success("✅ Member updated successfully!")
                    st.session_state[f'edit_member_{member["id"]}'] = False
                    st.rerun()
                except Exception as e:
                    show_friendly_error("Unable to update member right now.", "gym_management.update_member", e)

        with col_cancel:
            if st.form_submit_button("❌ Cancel", use_container_width=True):
                st.session_state[f'edit_member_{member["id"]}'] = False
                st.rerun()


def render_gym_memberships_page(business_id: int, user_role: str):
    """Gym memberships management."""
    tab1, tab2 = st.tabs(["💳 Active Memberships", "➕ New Membership"])

    with tab1:
        st.markdown("### 💳 Active Memberships")

        # Expiring soon alert
        expiring_memberships = db.get_gym_membership_expiring_soon(business_id, days_ahead=7)
        if expiring_memberships:
            st.warning(f"⚠️ **{len(expiring_memberships)} memberships** expiring in the next 7 days!")

        memberships = db.get_gym_memberships(business_id, active_only=True)

        if memberships:
            for membership in memberships:
                end_date = datetime.strptime(membership['end_date'], '%Y-%m-%d')
                days_left = (end_date - datetime.now()).days

                # Status color
                if days_left > 7:
                    status_color = C['emerald']
                    status_text = f"{days_left} days left"
                elif days_left > 0:
                    status_color = C['amber']
                    status_text = f"⚠️ {days_left} days left"
                else:
                    status_color = C['rose']
                    status_text = "❌ Expired"

                st.markdown(f"""
                <div style="background:{C['surface']};border:1px solid {C['border']};
                            border-radius:12px;padding:1.2rem;margin-bottom:1rem;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <h4 style="color:{C['text']};margin:0;">
                                {membership['first_name']} {membership['last_name']}
                            </h4>
                            <div style="color:{C['muted']};margin:0.3rem 0;">
                                {membership['membership_type_name']} • ID: {membership['custom_member_id']}
                            </div>
                            <div style="color:{C['slate']};font-size:0.9rem;">
                                {membership['start_date']} to {membership['end_date']}
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="color:{status_color};font-weight:600;">{status_text}</div>
                            <div style="color:{C['muted']};font-size:0.9rem;">
                                ${membership['amount_paid']:.0f} paid
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        else:
            st.info("💳 No active memberships found.")

    with tab2:
        if user_role in ['owner', 'admin', 'staff']:
            _render_new_membership_form(business_id)
        else:
            st.error("You don't have permission to create memberships.")


def _render_new_membership_form(business_id: int):
    """Form to create new membership."""
    st.markdown("### ➕ Create New Membership")

    # Get members and membership types
    members = db.get_gym_members(business_id, active_only=True)
    membership_types = db.get_business_products_services(business_id, active_only=True)
    membership_services = [mt for mt in membership_types if mt['type'] == 'service']

    if not members:
        st.warning("⚠️ No active members found. Please add members first.")
        return

    if not membership_services:
        st.warning("⚠️ No membership types found. Please add membership services in Products & Services.")
        return

    with st.form("create_membership"):
        # Member selection
        member = st.selectbox(
            "Select Member *",
            options=members,
            format_func=lambda x: f"{x['member_id']} - {x['first_name']} {x['last_name']}"
        )

        # Membership type selection
        membership_type = st.selectbox(
            "Membership Type *",
            options=membership_services,
            format_func=lambda x: f"{x['name']} - ${x['price']:.0f}"
        )

        col1, col2 = st.columns(2)

        with col1:
            start_date = st.date_input("Start Date", value=date.today())

        with col2:
            # Auto-calculate end date based on duration
            if membership_type and membership_type['duration_days']:
                default_end_date = start_date + timedelta(days=membership_type['duration_days'])
                end_date = st.date_input("End Date", value=default_end_date)
            else:
                end_date = st.date_input("End Date", value=start_date + timedelta(days=30))

        col3, col4 = st.columns(2)

        with col3:
            amount_paid = st.number_input("Amount Paid ($)",
                                        min_value=0.0,
                                        value=float(membership_type['price']) if membership_type else 0.0,
                                        step=1.0)

        with col4:
            payment_method = st.selectbox("Payment Method *",
                                        ['cash', 'card', 'digital', 'bank_transfer', 'check'])

        if st.form_submit_button("💳 Create Membership", use_container_width=True):
            if not member or not membership_type:
                st.error("Please select both member and membership type.")
                return

            if end_date <= start_date:
                st.error("End date must be after start date.")
                return

            try:
                membership_id = db.create_gym_membership(
                    business_id=business_id,
                    member_id=member['id'],
                    membership_type_id=membership_type['id'],
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                    amount_paid=amount_paid,
                    payment_method=payment_method,
                    created_by=st.session_state.get('user', {}).get('id', 0)
                )

                st.success(f"✅ Membership created for {member['first_name']} {member['last_name']}!")
                st.rerun()

            except Exception as e:
                show_friendly_error("Unable to create membership right now.", "gym_management.create_membership", e)


def render_gym_day_passes_page(business_id: int, user_role: str):
    """Day passes and walk-in management."""
    st.markdown("### 🎫 Day Passes & Walk-ins")

    # Quick stats
    today = datetime.now().strftime('%Y-%m-%d')
    day_pass_revenue = db.get_gym_check_ins(business_id, date_filter=today)
    day_pass_revenue = sum(c['amount_paid'] for c in day_pass_revenue if c['entry_type'] == 'day_pass')

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Today's Day Pass Revenue", f"${day_pass_revenue:.0f}")

    # Recent day pass purchases
    st.markdown("#### Recent Day Pass Purchases")

    day_pass_checkins = [c for c in db.get_gym_check_ins(business_id, limit=20)
                        if c['entry_type'] == 'day_pass']

    if day_pass_checkins:
        for checkin in day_pass_checkins[:10]:
            checkin_date = datetime.fromisoformat(checkin['check_in_time']).strftime('%Y-%m-%d %H:%M')

            st.markdown(f"""
            <div style="background:{C['surface2']};border-radius:8px;padding:0.8rem;margin-bottom:0.5rem;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <div style="color:{C['text']};font-weight:600;">
                            🎫 {checkin['first_name']} {checkin['last_name']}
                        </div>
                        <div style="color:{C['muted']};font-size:0.8rem;">{checkin_date}</div>
                    </div>
                    <div style="color:{C['emerald']};font-weight:700;">${checkin['amount_paid']:.0f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("🎫 No day pass purchases yet today.")


def render_gym_equipment_page(business_id: int, user_role: str):
    """Gym equipment management."""
    tab1, tab2 = st.tabs(["🏋️‍♀️ Equipment List", "➕ Add Equipment"])

    with tab1:
        st.markdown("### 🏋️‍♀️ Gym Equipment")

        equipment_list = db.get_gym_equipment(business_id)

        if equipment_list:
            # Group by type
            equipment_by_type = {}
            for eq in equipment_list:
                eq_type = eq['equipment_type']
                if eq_type not in equipment_by_type:
                    equipment_by_type[eq_type] = []
                equipment_by_type[eq_type].append(eq)

            for eq_type, equipment in equipment_by_type.items():
                st.markdown(f"#### {eq_type.title()} Equipment")

                for eq in equipment:
                    status_color = C['emerald'] if eq['is_operational'] else C['rose']
                    status_text = "✅ Operational" if eq['is_operational'] else "❌ Out of Order"

                    with st.expander(f"{eq['equipment_name']} - {status_text}"):
                        col1, col2 = st.columns(2)

                        with col1:
                            if eq['brand']:
                                st.write(f"**Brand:** {eq['brand']}")
                            if eq['model']:
                                st.write(f"**Model:** {eq['model']}")
                            if eq['serial_number']:
                                st.write(f"**Serial:** {eq['serial_number']}")

                        with col2:
                            if eq['purchase_date']:
                                st.write(f"**Purchased:** {eq['purchase_date']}")
                            if eq['warranty_expiry']:
                                st.write(f"**Warranty:** {eq['warranty_expiry']}")
                            if eq['last_maintenance']:
                                st.write(f"**Last Maintenance:** {eq['last_maintenance']}")

                        if eq['maintenance_notes']:
                            st.write(f"**Notes:** {eq['maintenance_notes']}")

                        # Maintenance logging
                        if user_role in ['owner', 'admin']:
                            with st.form(f"maintenance_{eq['id']}"):
                                st.markdown("**Log Maintenance**")
                                maintenance_notes = st.text_input("Maintenance Notes")
                                next_maintenance = st.date_input("Next Maintenance Due", value=None)

                                if st.form_submit_button("📝 Log Maintenance"):
                                    db.update_gym_equipment_maintenance(
                                        eq['id'],
                                        maintenance_notes,
                                        next_maintenance.isoformat() if next_maintenance else None
                                    )
                                    st.success("✅ Maintenance logged!")
                                    st.rerun()

        else:
            st.info("🏋️‍♀️ No equipment added yet.")

    with tab2:
        if user_role in ['owner', 'admin']:
            _render_add_equipment_form(business_id)
        else:
            st.error("You don't have permission to add equipment.")


def _render_add_equipment_form(business_id: int):
    """Form to add new equipment."""
    st.markdown("### ➕ Add New Equipment")

    with st.form("add_equipment"):
        col1, col2 = st.columns(2)

        with col1:
            equipment_name = st.text_input("Equipment Name *", placeholder="e.g., Treadmill #1")
            equipment_type = st.selectbox("Equipment Type *",
                                        ['cardio', 'strength', 'functional', 'free_weights', 'other'])
            brand = st.text_input("Brand", placeholder="e.g., NordicTrack")

        with col2:
            model = st.text_input("Model", placeholder="e.g., Commercial 1750")
            serial_number = st.text_input("Serial Number")
            purchase_date = st.date_input("Purchase Date", value=None)

        warranty_expiry = st.date_input("Warranty Expiry", value=None)

        if st.form_submit_button("➕ Add Equipment", use_container_width=True):
            if not equipment_name or not equipment_type:
                st.error("Equipment name and type are required.")
                return

            try:
                equipment_id = db.create_gym_equipment(
                    business_id=business_id,
                    equipment_name=equipment_name,
                    equipment_type=equipment_type,
                    brand=brand if brand else None,
                    model=model if model else None,
                    serial_number=serial_number if serial_number else None,
                    purchase_date=purchase_date.isoformat() if purchase_date else None,
                    warranty_expiry=warranty_expiry.isoformat() if warranty_expiry else None
                )

                st.success(f"✅ Equipment '{equipment_name}' added successfully!")
                st.rerun()

            except Exception as e:
                show_friendly_error("Unable to add equipment right now.", "gym_management.add_equipment", e)


def render_gym_reports_page(business_id: int):
    """Gym reports and analytics."""
    st.markdown("### 📊 Gym Reports")

    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=date.today() - timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", value=date.today())

    # Generate report data
    date_range = []
    current_date = start_date
    while current_date <= end_date:
        daily_summary = db.get_gym_daily_summary(business_id, current_date.isoformat())
        daily_summary['date'] = current_date.isoformat()
        date_range.append(daily_summary)
        current_date += timedelta(days=1)

    if date_range:
        df = pd.DataFrame(date_range)

        # Charts
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.markdown("#### Daily Check-ins")
            st.line_chart(df.set_index('date')['daily_check_ins'])

        with col_chart2:
            st.markdown("#### Daily Revenue")
            st.line_chart(df.set_index('date')['daily_revenue'])

        # Summary stats
        total_checkins = df['daily_check_ins'].sum()
        total_revenue = df['daily_revenue'].sum()
        avg_daily_checkins = df['daily_check_ins'].mean()
        peak_day = df.loc[df['daily_check_ins'].idxmax()]

        st.markdown("#### Summary Statistics")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Check-ins", f"{total_checkins:,}")
        col2.metric("Total Revenue", f"${total_revenue:,.0f}")
        col3.metric("Avg Daily Check-ins", f"{avg_daily_checkins:.1f}")
        col4.metric("Peak Day", f"{peak_day['daily_check_ins']} ({peak_day['date']})")

    # Membership expiry alerts
    st.markdown("#### Membership Alerts")
    expiring_soon = db.get_gym_membership_expiring_soon(business_id, days_ahead=30)

    if expiring_soon:
        st.markdown("**Memberships expiring in the next 30 days:**")

        for membership in expiring_soon[:10]:
            end_date = datetime.strptime(membership['end_date'], '%Y-%m-%d')
            days_left = (end_date - datetime.now()).days

            if days_left <= 7:
                alert_color = C['rose']
                alert_icon = "🚨"
            elif days_left <= 14:
                alert_color = C['amber']
                alert_icon = "⚠️"
            else:
                alert_color = C['cyan']
                alert_icon = "ℹ️"

            st.markdown(f"""
            <div style="background:{C['surface2']};border-left:4px solid {alert_color};
                        padding:0.8rem;margin-bottom:0.5rem;">
                {alert_icon} **{membership['first_name']} {membership['last_name']}**
                ({membership['custom_member_id']}) -
                {membership['membership_type_name']} expires in {days_left} days
            </div>
            """, unsafe_allow_html=True)

        if len(expiring_soon) > 10:
            st.info(f"... and {len(expiring_soon) - 10} more memberships expiring soon.")
    else:
        st.success("✅ No memberships expiring in the next 30 days!")