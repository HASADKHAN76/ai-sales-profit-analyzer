"""
profile_page.py
User profile settings: password change, 2FA setup.
"""

import streamlit as st
import auth
import database as db

# Reuse design tokens
C = {
    "bg":       "#080d1a",
    "surface":  "#0d1526",
    "surface2": "#111d35",
    "border":   "#1a2d50",
    "indigo":   "#6366f1",
    "emerald":  "#10b981",
    "amber":    "#f59e0b",
    "text":     "#e2e8f0",
    "muted":    "#64748b",
    "rose":     "#f43f5e",
}


def render_profile_page(user: dict):
    """Render user profile and security settings."""

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{C['indigo']}22,{C['surface2']});
                border:1px solid {C['border']};border-radius:14px;
                padding:1.5rem;margin-bottom:1.5rem;">
        <h2 style="color:{C['text']};margin:0 0 .3rem 0;">Account Settings</h2>
        <p style="color:{C['muted']};margin:0;font-size:.85rem;">
            Manage your password and security settings</p>
    </div>
    """, unsafe_allow_html=True)

    tab_password, tab_2fa = st.tabs(["Change Password", "Two-Factor Authentication"])

    with tab_password:
        _render_change_password(user)

    with tab_2fa:
        _render_2fa_settings(user)


def _render_change_password(user: dict):
    """Render password change form."""
    st.markdown("### Change Password")

    with st.form("change_password_form"):
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Update Password", use_container_width=True, type="primary")

        if submitted:
            if new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                success, message = auth.change_password(user["id"], current_password, new_password)
                if success:
                    st.success(message)
                else:
                    st.error(message)

    # Password strength indicator (real-time using callback)
    st.markdown("---")
    st.markdown("**Password Strength Guide**")
    st.markdown(f"""
    <div style="background:{C['surface2']};border:1px solid {C['border']};
                border-radius:8px;padding:1rem;font-size:.85rem;color:{C['muted']};">
        <p style="margin:0 0 .5rem 0;">A strong password should include:</p>
        <ul style="margin:0;padding-left:1.2rem;">
            <li>At least 8 characters</li>
            <li>Uppercase and lowercase letters</li>
            <li>Numbers</li>
            <li>Special characters (!@#$%^&*)</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)


def _render_2fa_settings(user: dict):
    """Render 2FA setup/management."""
    user_2fa = db.get_user_2fa(user["id"])

    if user_2fa and user_2fa["is_enabled"]:
        # 2FA is enabled - show status and disable option
        st.markdown(f"""
        <div style="background:{C['emerald']}22;border:1px solid {C['emerald']};
                    border-radius:10px;padding:1rem;margin-bottom:1rem;">
            <div style="display:flex;align-items:center;gap:.5rem;">
                <span style="font-size:1.2rem;">🔐</span>
                <span style="color:{C['emerald']};font-weight:700;">
                    Two-Factor Authentication is enabled
                </span>
            </div>
            <p style="color:{C['muted']};font-size:.85rem;margin:.5rem 0 0 0;">
                Your account is protected with an additional layer of security.
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Disable Two-Factor Authentication")
        st.warning("Disabling 2FA will make your account less secure.")

        if st.session_state.get("confirm_disable_2fa"):
            st.error("Are you sure you want to disable 2FA?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, Disable 2FA", type="primary", use_container_width=True):
                    success, msg = auth.disable_2fa_for_user(user["id"])
                    if success:
                        st.success(msg)
                        st.session_state.pop("confirm_disable_2fa", None)
                        st.rerun()
                    else:
                        st.error(msg)
            with col2:
                if st.button("Cancel", use_container_width=True):
                    st.session_state.pop("confirm_disable_2fa", None)
                    st.rerun()
        else:
            if st.button("Disable 2FA", type="secondary"):
                st.session_state["confirm_disable_2fa"] = True
                st.rerun()

    else:
        # 2FA not enabled - show setup
        st.markdown("### Enable Two-Factor Authentication")
        st.markdown(f"""
        <div style="background:{C['surface2']};border:1px solid {C['border']};
                    border-radius:10px;padding:1rem;margin-bottom:1rem;">
            <p style="color:{C['text']};margin:0 0 .5rem 0;font-weight:600;">
                Why enable 2FA?
            </p>
            <ul style="color:{C['muted']};font-size:.85rem;margin:0;padding-left:1.2rem;">
                <li>Adds an extra layer of security to your account</li>
                <li>Protects against password theft</li>
                <li>Required for sensitive operations</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.get("2fa_setup_active"):
            _render_2fa_setup(user)
        else:
            if st.button("Set Up 2FA", type="primary", use_container_width=True):
                try:
                    qr_base64, secret, backup_codes = auth.setup_2fa(user["id"])
                    st.session_state["2fa_setup_active"] = True
                    st.session_state["2fa_qr"] = qr_base64
                    st.session_state["2fa_secret"] = secret
                    st.session_state["2fa_backup_codes"] = backup_codes
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to initialize 2FA: {str(e)}")


def _render_2fa_setup(user: dict):
    """Render 2FA setup wizard."""

    # Step 1: QR Code
    st.markdown("#### Step 1: Scan QR Code")
    st.markdown("Scan this QR code with your authenticator app (Google Authenticator, Authy, Microsoft Authenticator, etc.)")

    qr_base64 = st.session_state.get("2fa_qr")
    secret = st.session_state.get("2fa_secret")

    if qr_base64:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"""
            <div style="text-align:center;padding:1rem;background:white;
                        border-radius:10px;display:inline-block;margin:1rem auto;">
                <img src="data:image/png;base64,{qr_base64}" width="200">
            </div>
            """, unsafe_allow_html=True)

        with st.expander("Can't scan? Enter code manually"):
            st.code(secret, language=None)
            st.caption("Enter this code manually in your authenticator app")

    # Step 2: Backup Codes
    st.markdown("---")
    st.markdown("#### Step 2: Save Backup Codes")
    st.warning("Save these backup codes in a secure place. Each code can only be used once if you lose access to your authenticator app.")

    backup_codes = st.session_state.get("2fa_backup_codes", [])
    if backup_codes:
        codes_grid = "  |  ".join([f"`{code}`" for code in backup_codes[:4]])
        codes_grid2 = "  |  ".join([f"`{code}`" for code in backup_codes[4:]])
        st.markdown(codes_grid)
        st.markdown(codes_grid2)

        # Copy button
        all_codes = "\n".join(backup_codes)
        st.code(all_codes, language=None)
        st.caption("Copy and save these codes securely")

    # Step 3: Verify
    st.markdown("---")
    st.markdown("#### Step 3: Verify Setup")
    st.markdown("Enter the 6-digit code from your authenticator app to complete setup.")

    with st.form("verify_2fa_form"):
        code = st.text_input("Verification Code", max_chars=6, placeholder="Enter 6-digit code")
        submitted = st.form_submit_button("Verify & Enable 2FA", use_container_width=True, type="primary")

        if submitted:
            if not code or len(code) != 6:
                st.error("Please enter a valid 6-digit code.")
            else:
                success, message = auth.verify_and_enable_2fa(user["id"], code)
                if success:
                    st.success(message)
                    # Clean up session
                    for key in ["2fa_setup_active", "2fa_qr", "2fa_secret", "2fa_backup_codes"]:
                        st.session_state.pop(key, None)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(message)

    # Cancel button
    if st.button("Cancel Setup", use_container_width=True):
        for key in ["2fa_setup_active", "2fa_qr", "2fa_secret", "2fa_backup_codes"]:
            st.session_state.pop(key, None)
        st.rerun()
