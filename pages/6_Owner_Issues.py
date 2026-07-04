import pandas as pd
import streamlit as st

import auth
import db

st.set_page_config(page_title="Owner Issues | Hermosa Casa", page_icon="!", layout="wide")
auth.require_login()
db.init_db()
db.sidebar_footer()

st.title("Owner Issues / Complaints")

is_edit = auth.is_edit()

if is_edit:
    st.info("Committee mode: you can add complaints, update status, and delete records.")
else:
    st.info("Resident mode: you can submit a complaint and track complaint status.")

tab_add, tab_view = st.tabs(["Add Complaint", "View / Track"])

with tab_add:
    with st.form("owner_issue_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        flat_raw = col1.text_input("Flat Number *", placeholder="E-1104")
        mobile = col2.text_input("Mobile", placeholder="9876543210")

        owner_name = st.text_input("Owner Name *")
        category = st.selectbox("Category", db.ISSUE_CATEGORIES)
        title = st.text_input("Complaint Title *", placeholder="Short summary")
        details = st.text_area(
            "Complaint Details *",
            height=140,
            placeholder="Describe the issue, location, and any useful details.",
        )

        submitted = st.form_submit_button("Submit Complaint", type="primary", use_container_width=True)

    if submitted:
        flat_no = db.normalize_flat(flat_raw)
        owner = owner_name.strip()

        if flat_no and not owner:
            matches = [r for r in db.search_residents(flat_no) if r["flat_no"] == flat_no]
            if matches:
                owner = matches[0]["owner_name"]

        if not flat_no:
            st.error("Invalid flat number. Expected format like E-1104.")
        elif not owner:
            st.error("Owner name is required.")
        elif not title.strip():
            st.error("Complaint title is required.")
        elif not details.strip():
            st.error("Complaint details are required.")
        else:
            db.add_owner_issue(
                flat_no,
                owner,
                mobile.strip(),
                category,
                title.strip(),
                details.strip(),
            )
            st.success("Complaint submitted with status OPEN.")
            st.rerun()

with tab_view:
    counts = db.get_issue_status_counts()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("OPEN", counts["OPEN"])
    c2.metric("WORKING", counts["WORKING"])
    c3.metric("PENDING", counts["PENDING"])
    c4.metric("CLOSED", counts["CLOSED"])

    st.divider()
    f1, f2, f3 = st.columns(3)
    term = f1.text_input("Search", placeholder="Flat / owner / mobile / text")
    status_filter = f2.selectbox("Status", ["All"] + db.ISSUE_STATUSES)
    flat_filter_raw = f3.text_input("Flat Filter", placeholder="Optional exact flat")
    flat_filter = db.normalize_flat(flat_filter_raw) if flat_filter_raw.strip() else ""

    rows = db.search_owner_issues(term, status_filter, flat_filter)
    st.caption(f"{len(rows)} complaint(s)")

    if rows:
        df = pd.DataFrame(rows)[
            [
                "id",
                "flat_no",
                "owner_name",
                "mobile",
                "issue_category",
                "complaint_title",
                "status",
                "created_at",
                "updated_at",
            ]
        ]
        df.columns = ["ID", "Flat", "Owner", "Mobile", "Category", "Title", "Status", "Created", "Updated"]
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.download_button(
            "Download CSV",
            df.to_csv(index=False).encode(),
            "owner_issues.csv",
            "text/csv",
            use_container_width=True,
        )

        for issue in rows:
            with st.expander(f"#{issue['id']} | {issue['flat_no']} | {issue['complaint_title']} | {issue['status']}"):
                st.write(f"**Owner:** {issue['owner_name']}")
                st.write(f"**Mobile:** {issue['mobile'] or '-'}")
                st.write(f"**Category:** {issue['issue_category'] or '-'}")
                st.write(f"**Created:** {issue['created_at']}  \n**Updated:** {issue['updated_at']}")
                st.write(issue["complaint_text"])

                if is_edit:
                    col_status, col_delete = st.columns([3, 1])
                    current_index = (
                        db.ISSUE_STATUSES.index(issue["status"])
                        if issue["status"] in db.ISSUE_STATUSES
                        else 0
                    )
                    new_status = col_status.selectbox(
                        "Update Status",
                        db.ISSUE_STATUSES,
                        index=current_index,
                        key=f"status_{issue['id']}",
                    )
                    if col_status.button("Save Status", key=f"save_{issue['id']}", use_container_width=True):
                        db.update_owner_issue_status(issue["id"], new_status)
                        st.success("Status updated.")
                        st.rerun()
                    if col_delete.button("Delete", key=f"delete_{issue['id']}", use_container_width=True):
                        db.delete_owner_issue(issue["id"])
                        st.success("Complaint deleted.")
                        st.rerun()
    else:
        st.info("No complaints found.")
