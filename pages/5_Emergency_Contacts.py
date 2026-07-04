import streamlit as st
import db
import auth

st.set_page_config(page_title="Emergency Contacts | Hermosa Casa", page_icon="📞", layout="wide")
auth.require_login()
db.init_db()
db.sidebar_footer()

st.title("📞 Emergency Contacts")

is_edit = auth.is_edit()

if not is_edit:
    st.info("🔒 Read-only mode: You can view all emergency contacts. Adding or deleting is restricted to committee members.")

contacts = db.get_contacts()
categories = sorted({c["category"] for c in contacts})
for cat in categories:
    st.subheader(cat)
    for c in [x for x in contacts if x["category"] == cat]:
        col1, col2 = st.columns([3, 1])
        col1.markdown(f"**{c['name']}**  \n📱 [{c['phone']}](tel:{c['phone']})")
        if col2.button("🗑️", key=f"del_{c['id']}", help="Delete contact"):
            db.delete_contact(c["id"])
            st.rerun()

st.divider()
if is_edit:
    with st.expander("➕ Add a Contact"):
        with st.form("contact_form", clear_on_submit=True):
            category = st.text_input("Category *", placeholder="Security / Medical / Maintenance")
            name = st.text_input("Name *")
            phone = st.text_input("Phone *")
            if st.form_submit_button("Save Contact", use_container_width=True):
                if category.strip() and name.strip() and phone.strip():
                    db.add_contact(category.strip(), name.strip(), phone.strip())
                    st.success("Contact added.")
                    st.rerun()
                else:
                    st.error("All fields are required.")
else:
    st.caption("Adding new contacts is disabled in read-only mode.")