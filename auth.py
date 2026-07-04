"""Authentication for Hermosa Casa — call auth.require_login() at the top of EVERY page.

Fail-closed: if passwords are not configured in Streamlit Secrets, nobody can log in.
No default passwords exist in this code.
"""
import streamlit as st


def _get_secret(key: str) -> str:
    """Read a secret; tolerate missing secrets.toml during local dev."""
    try:
        return str(st.secrets.get(key, "") or "").strip()
    except Exception:
        return ""


def require_login():
    """Gate the current page. Shows login form and halts if not authenticated."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.role = None

    if st.session_state.authenticated:
        return

    st.title("🏢 Hermosa Casa Society")
    st.subheader("Secure Committee & Resident Portal")

    edit_pwd = _get_secret("password_edit")
    read_pwd = _get_secret("password_read")

    if not edit_pwd and not read_pwd:
        st.error(
            "⚠️ App not configured: no passwords set.\n\n"
            "Add `password_edit` and `password_read` in "
            "**Streamlit Cloud → App → Settings → Secrets** (or a local "
            "`.streamlit/secrets.toml`), then reload."
        )
        st.stop()

    with st.form("login"):
        pwd = st.text_input(
            "Enter Password", type="password",
            placeholder="Committee or Resident password",
            help="Committee members use the edit password. Residents use the read-only password.",
        )
        if st.form_submit_button("Login", use_container_width=True, type="primary"):
            if edit_pwd and pwd == edit_pwd:
                st.session_state.authenticated = True
                st.session_state.role = "edit"
                st.rerun()
            elif read_pwd and pwd == read_pwd:
                st.session_state.authenticated = True
                st.session_state.role = "read"
                st.rerun()
            else:
                st.error("❌ Incorrect password. Contact the Admin.")

    st.info(
        "🔒 **Two access levels**\n"
        "- **Committee (Edit)**: add, edit, delete records, bulk import\n"
        "- **Residents (Read-only)**: view dashboards, search, reports, emergency contacts"
    )
    st.stop()


def is_edit() -> bool:
    return st.session_state.get("role") == "edit"


def logout_button():
    if st.button("🔓 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.role = None
        st.rerun()
