"""
admin_panel.py
Admin dashboard rendered inside Streamlit.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

import database as db
import auth
import security as sec


# Design tokens matching app.py
C = {
    "bg":       "#0a0a0f",
    "surface":  "#12121a",
    "surface2": "#1a1a2e",
    "border":   "#2a2a3e",
    "text":     "#e2e8f0",
    "muted":    "#94a3b8",
    "primary":  "#6366f1",
    "emerald":  "#10b981",
    "amber":    "#f59e0b",
    "rose":     "#f43f5e",
}


def render_admin_panel():
    """Render the full admin dashboard."""

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{C['primary']}22,{C['surface2']});
                border:1px solid {C['border']};border-radius:14px;
                padding:1.5rem;margin-bottom:1.5rem;">
        <h2 style="color:{C['text']};margin:0 0 .3rem 0;">Admin Dashboard</h2>
        <p style="color:{C['muted']};margin:0;font-size:.85rem;">
            Manage users, monitor AI usage, and view platform analytics</p>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI Cards ─────────────────────────────────
    stats = db.get_admin_stats()

    cols = st.columns(6)
    kpi_data = [
        ("Total Users", stats["total_users"], C["primary"]),
        ("Active Users", stats["active_users"], C["emerald"]),
        ("Datasets", stats["total_datasets"], C["amber"]),
        ("AI Requests", stats["total_ai_requests"], C["primary"]),
        ("AI Today", stats["ai_requests_today"], C["emerald"]),
        ("Logins Today", stats["logins_today"], C["amber"]),
    ]

    for col, (label, value, color) in zip(cols, kpi_data):
        col.markdown(f"""
        <div style="background:{C['surface2']};border:1px solid {C['border']};
                    border-radius:10px;padding:.8rem;text-align:center;">
            <div style="font-size:1.6rem;font-weight:700;color:{color}">{value:,}</div>
            <div style="font-size:.7rem;color:{C['muted']};margin-top:.2rem">{label}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────
    tab_users, tab_datasets, tab_ai, tab_create, tab_security = st.tabs([
        "User Management", "Datasets", "AI Usage", "Create User", "Security"
    ])

    # ── User Management Tab ───────────────────────
    with tab_users:
        users = db.get_all_users()
        if not users:
            st.info("No users found.")
        else:
            df = pd.DataFrame(users)
            df["is_active"] = df["is_active"].map({1: "Active", 0: "Inactive"})
            df = df.rename(columns={
                "id": "ID", "username": "Username", "email": "Email",
                "role": "Role", "is_active": "Status",
                "created_at": "Created", "last_login": "Last Login"
            })

            st.dataframe(
                df[["ID", "Username", "Email", "Role", "Status", "Created", "Last Login"]],
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("---")
            st.markdown(f"**Manage User**")

            col1, col2, col3 = st.columns(3)

            with col1:
                user_options = {f"{u['username']} (ID:{u['id']})": u['id'] for u in users}
                selected = st.selectbox("Select User", list(user_options.keys()), key="admin_user_select")
                selected_id = user_options[selected] if selected else None

            with col2:
                new_role = st.selectbox("Change Role", ["user", "admin"], key="admin_role_select")
                if st.button("Update Role", key="admin_update_role"):
                    if selected_id:
                        db.update_user_role(selected_id, new_role)
                        st.success(f"Role updated to {new_role}")
                        st.rerun()

            with col3:
                selected_user = db.get_user_by_id(selected_id) if selected_id else None
                is_active = selected_user["is_active"] if selected_user else 1

                if is_active:
                    if st.button("Deactivate User", key="admin_deactivate", type="secondary"):
                        if selected_id:
                            db.toggle_user_active(selected_id, False)
                            st.warning("User deactivated")
                            st.rerun()
                else:
                    if st.button("Activate User", key="admin_activate"):
                        if selected_id:
                            db.toggle_user_active(selected_id, True)
                            st.success("User activated")
                            st.rerun()

                if st.button("Delete User", key="admin_delete", type="primary"):
                    if selected_id and selected_id != st.session_state.get("user", {}).get("id"):
                        db.delete_user(selected_id)
                        st.success("User deleted")
                        st.rerun()
                    else:
                        st.error("Cannot delete your own account.")

    # ── Datasets Tab ──────────────────────────────
    with tab_datasets:
        datasets = db.get_all_datasets()
        if not datasets:
            st.info("No datasets uploaded yet.")
        else:
            df = pd.DataFrame(datasets)
            df["file_size"] = df["file_size"].apply(lambda x: f"{x / 1024:.1f} KB")
            df = df.rename(columns={
                "id": "ID", "username": "User", "filename": "File",
                "row_count": "Rows", "file_size": "Size", "uploaded_at": "Uploaded"
            })
            st.dataframe(
                df[["ID", "User", "File", "Rows", "Size", "Uploaded"]],
                use_container_width=True,
                hide_index=True,
            )

    # ── AI Usage Tab ──────────────────────────────
    with tab_ai:
        requests = db.get_all_ai_requests(limit=100)
        if not requests:
            st.info("No AI requests yet.")
        else:
            df = pd.DataFrame(requests)
            df["question"] = df["question"].str[:80] + "..."
            df = df.rename(columns={
                "id": "ID", "username": "User", "provider": "Provider",
                "question": "Question", "created_at": "Time"
            })
            st.dataframe(
                df[["ID", "User", "Provider", "Question", "Time"]],
                use_container_width=True,
                hide_index=True,
            )

    # ── Create User Tab ───────────────────────────
    with tab_create:
        st.markdown("**Create New User**")
        with st.form("admin_create_user"):
            new_username = st.text_input("Username")
            new_email = st.text_input("Email")
            new_password = st.text_input("Password", type="password")
            new_user_role = st.selectbox("Role", ["user", "admin"])
            submitted = st.form_submit_button("Create Account")

            if submitted:
                success, msg = auth.register(new_username, new_email, new_password, new_user_role)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

    # ── Security Tab ─────────────────────────────
    with tab_security:
        _render_security_tab()


def _render_security_tab():
    """Render security management for admins."""

    # Locked Accounts Section
    st.markdown("### Locked Accounts")

    locked_users = db.get_locked_users()

    if not locked_users:
        st.markdown(f"""
        <div style="background:{C['emerald']}22;border:1px solid {C['emerald']};
                    border-radius:8px;padding:1rem;text-align:center;">
            <span style="color:{C['emerald']};font-weight:600;">No accounts are currently locked</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning(f"{len(locked_users)} account(s) currently locked")

        for user in locked_users:
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.markdown(f"**{user['username']}** ({user['email']})")
            with col2:
                st.markdown(f"Failed attempts: {user['failed_login_attempts']}")
            with col3:
                if st.button("Unlock", key=f"unlock_{user['id']}"):
                    admin_id = st.session_state.get("user", {}).get("id")
                    db.unlock_account(user["id"], admin_id)
                    st.success(f"Unlocked {user['username']}")
                    st.rerun()

    st.markdown("---")

    # Users with 2FA Section
    st.markdown("### Users with 2FA Enabled")

    users_2fa = db.get_users_with_2fa()

    if not users_2fa:
        st.info("No users have 2FA enabled.")
    else:
        st.markdown(f"**{len(users_2fa)}** user(s) with 2FA enabled")

        for user in users_2fa:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{user['username']}** ({user['email']})")
                st.caption(f"Enabled since: {user['created_at']}")
            with col2:
                if st.button("Disable 2FA", key=f"disable_2fa_{user['id']}", type="secondary"):
                    admin_id = st.session_state.get("user", {}).get("id")
                    success, msg = auth.disable_2fa_for_user(user["id"], admin_id)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    st.markdown("---")

    # Security Settings Display
    st.markdown("### Security Configuration")

    st.markdown(f"""
    <div style="background:{C['surface2']};border:1px solid {C['border']};
                border-radius:10px;padding:1rem;">
        <table style="width:100%;color:{C['text']};font-size:.85rem;">
            <tr>
                <td style="padding:.4rem 0;color:{C['muted']};">Max Failed Login Attempts</td>
                <td style="padding:.4rem 0;text-align:right;font-weight:600;">{sec.MAX_FAILED_ATTEMPTS}</td>
            </tr>
            <tr>
                <td style="padding:.4rem 0;color:{C['muted']};">Account Lockout Duration</td>
                <td style="padding:.4rem 0;text-align:right;font-weight:600;">{sec.LOCKOUT_DURATION_MINUTES} minutes</td>
            </tr>
            <tr>
                <td style="padding:.4rem 0;color:{C['muted']};">Password Reset Token Expiry</td>
                <td style="padding:.4rem 0;text-align:right;font-weight:600;">{sec.RESET_TOKEN_EXPIRY_HOURS} hour(s)</td>
            </tr>
        </table>
        <p style="color:{C['muted']};font-size:.75rem;margin:.8rem 0 0 0;text-align:center;">
            Configure these values in your <code>.env</code> file
        </p>
    </div>
    """, unsafe_allow_html=True)

