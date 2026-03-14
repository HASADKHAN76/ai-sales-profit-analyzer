"""
auth_page.py
Streamlit login and registration page with professional UI.
Includes forgot password and 2FA support.
"""

import streamlit as st
import auth
import business_management as bm

# Design tokens
C = {
    "bg":       "#080d1a",
    "surface":  "#0d1526",
    "surface2": "#111d35",
    "border":   "#1a2d50",
    "indigo":   "#6366f1",
    "emerald":  "#10b981",
    "text":     "#e2e8f0",
    "muted":    "#64748b",
    "rose":     "#f43f5e",
    "cyan":     "#06b6d4",
}

AUTH_CSS = f"""
<style>
    [data-testid="stAppViewContainer"] {{
        background: {C["bg"]};
    }}
    .auth-container {{
        max-width: 420px;
        margin: 4rem auto;
        padding: 2.5rem;
        background: {C["surface"]};
        border: 1px solid {C["border"]};
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0,0,0,.4);
    }}
    .auth-title {{
        text-align: center;
        color: {C["text"]};
        font-size: 1.8rem;
        font-weight: 800;
        margin-bottom: .3rem;
    }}
    .auth-subtitle {{
        text-align: center;
        color: {C["muted"]};
        font-size: .85rem;
        margin-bottom: 2rem;
    }}
    .auth-logo {{
        text-align: center;
        font-size: 2.5rem;
        margin-bottom: 1rem;
    }}
    .auth-footer {{
        text-align: center;
        color: {C["muted"]};
        font-size: .75rem;
        margin-top: 1.5rem;
    }}
</style>
"""


def render_auth_page():
    """Show login/register forms. Returns True if user is authenticated."""

    st.markdown(AUTH_CSS, unsafe_allow_html=True)

    # Check for password reset token in URL
    reset_token = st.query_params.get("reset_token")
    if reset_token:
        _render_password_reset(reset_token)
        return False

    # Check if already authenticated
    if "auth_token" in st.session_state and st.session_state["auth_token"]:
        user = auth.get_current_user(st.session_state["auth_token"])
        if user:
            st.session_state["user"] = user
            return True
        else:
            # Token expired or invalid
            st.session_state.pop("auth_token", None)
            st.session_state.pop("user", None)

    # Check if showing forgot password form
    if st.session_state.get("show_forgot_password"):
        _render_forgot_password()
        return False

    # Show login/register
    st.markdown('<div class="auth-logo">🧠</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">RetailBrain AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-subtitle">Retail & E-commerce Intelligence Platform</div>', unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["Login", "Create Account"])

    with tab_login:
        _render_login()

    with tab_register:
        _render_register()

    st.markdown("""
    <div class="auth-footer">
        Secured with bcrypt + JWT + 2FA
    </div>
    """, unsafe_allow_html=True)

    return False


def _render_login():
    # Check if waiting for 2FA
    if st.session_state.get("awaiting_2fa"):
        _render_2fa_input()
        return

    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

        if submitted:
            success, message, token, requires_2fa = auth.login(username, password)

            if requires_2fa:
                # Store credentials temporarily and show 2FA input
                st.session_state["awaiting_2fa"] = True
                st.session_state["pending_username"] = username
                st.session_state["pending_password"] = password
                st.rerun()
            elif success and token:
                st.session_state["auth_token"] = token
                user = auth.get_current_user(token)
                st.session_state["user"] = user
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    # Forgot password button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Forgot Password?", use_container_width=True, type="secondary"):
            st.session_state["show_forgot_password"] = True
            st.rerun()


def _render_2fa_input():
    """Render 2FA code input form."""
    st.markdown(f"""
    <div style="background:{C['indigo']}22;border:1px solid {C['indigo']};
                border-radius:10px;padding:1rem;margin-bottom:1rem;text-align:center;">
        <span style="color:{C['indigo']};font-weight:600;">
            Two-Factor Authentication Required
        </span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("Enter the 6-digit code from your authenticator app, or use a backup code.")

    with st.form("2fa_form"):
        totp_code = st.text_input(
            "Authentication Code",
            placeholder="Enter 6-digit code or backup code",
            max_chars=20
        )
        submitted = st.form_submit_button("Verify", use_container_width=True, type="primary")

        if submitted:
            username = st.session_state.get("pending_username")
            password = st.session_state.get("pending_password")

            success, message, token, _ = auth.login(username, password, totp_code)

            if success and token:
                # Clear 2FA state
                st.session_state.pop("awaiting_2fa", None)
                st.session_state.pop("pending_username", None)
                st.session_state.pop("pending_password", None)

                st.session_state["auth_token"] = token
                user = auth.get_current_user(token)
                st.session_state["user"] = user
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    if st.button("Back to Login", use_container_width=True):
        st.session_state.pop("awaiting_2fa", None)
        st.session_state.pop("pending_username", None)
        st.session_state.pop("pending_password", None)
        st.rerun()


def _render_forgot_password():
    """Render forgot password form."""
    st.markdown('<div class="auth-logo">🔑</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">Reset Password</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-subtitle">Enter your email to receive reset instructions</div>', unsafe_allow_html=True)

    with st.form("forgot_password_form"):
        email = st.text_input("Email Address", placeholder="your@email.com")
        submitted = st.form_submit_button("Send Reset Link", use_container_width=True, type="primary")

        if submitted:
            if not email:
                st.error("Please enter your email address.")
            else:
                success, message = auth.request_password_reset(email)
                st.success(message)
                st.info("If email delivery is configured, reset instructions will be sent shortly.")

    if st.button("Back to Login", use_container_width=True):
        st.session_state.pop("show_forgot_password", None)
        st.rerun()


def _render_password_reset(token: str):
    """Render password reset form."""
    st.markdown('<div class="auth-logo">🔐</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">Set New Password</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-subtitle">Create a strong new password for your account</div>', unsafe_allow_html=True)

    with st.form("reset_password_form"):
        new_password = st.text_input("New Password", type="password", placeholder="Min 6 characters")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
        submitted = st.form_submit_button("Reset Password", use_container_width=True, type="primary")

        if submitted:
            if new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                success, message = auth.reset_password(token, new_password)
                if success:
                    st.success(message)
                    st.info("You can now login with your new password.")
                    # Clear token from URL
                    st.query_params.clear()
                else:
                    st.error(message)

    if st.button("Back to Login", use_container_width=True):
        st.query_params.clear()
        st.rerun()


def _render_register():
    with st.form("register_form"):
        username = st.text_input("Username", placeholder="Choose a username")
        email = st.text_input("Email", placeholder="your@email.com")
        password = st.text_input("Password", type="password", placeholder="Min 6 characters")
        password2 = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
        business_name = st.text_input("Business Name", placeholder="Acme Fitness")
        business_type = st.selectbox(
            "Business Type",
            options=list(bm.BUSINESS_TYPES.keys()),
            format_func=lambda x: bm.BUSINESS_TYPES[x]["name"],
        )
        submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")

        if submitted:
            if password != password2:
                st.error("Passwords do not match.")
                return
            if not business_name.strip():
                st.error("Business name is required.")
                return

            success, message = auth.register(
                username,
                email,
                password,
                business_name=business_name,
                business_type=business_type,
            )
            if success:
                st.success(message + " You can now sign in.")
            else:
                st.error(message)


def render_user_sidebar(user: dict):
    """Show user info and logout button in sidebar."""
    business_role = "staff"
    selected_business_id = st.session_state.get("selected_business_id")
    if selected_business_id:
        matched_role = bm.check_business_access(user["id"], selected_business_id)
        if matched_role:
            business_role = matched_role

    if user["role"] == "admin":
        role_color = C["emerald"]
        role_label = "ADMIN"
    elif business_role == "owner":
        role_color = C["indigo"]
        role_label = "BUSINESS OWNER"
    else:
        role_color = C["cyan"]
        role_label = "STAFF"

    # Add 2FA badge if enabled
    has_2fa = auth.has_2fa_enabled(user["id"])
    fa_badge = f'<span style="background:{C["emerald"]}22;color:{C["emerald"]};font-size:.55rem;font-weight:700;padding:1px 5px;border-radius:3px;margin-left:4px;">2FA</span>' if has_2fa else ""

    st.sidebar.markdown(f"""
    <div style="background:{C['surface2']};border:1px solid {C['border']};
                border-radius:10px;padding:.7rem .9rem;margin-bottom:.8rem;">
        <div style="font-size:.85rem;font-weight:700;color:{C['text']}">
            {user['username']}{fa_badge}
        </div>
        <div style="font-size:.65rem;color:{C['muted']}">{user['email']}</div>
        <div style="margin-top:.3rem">
            <span style="background:{role_color}22;color:{role_color};
                        font-size:.6rem;font-weight:700;padding:2px 8px;
                        border-radius:4px;text-transform:uppercase;">
                {role_label}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.pop("auth_token", None)
        st.session_state.pop("user", None)
        st.session_state.pop("df", None)
        st.session_state.pop("assistant", None)
        st.session_state.pop("awaiting_2fa", None)
        st.session_state.pop("pending_username", None)
        st.session_state.pop("pending_password", None)
        st.rerun()
