from datetime import date

import pandas as pd
import streamlit as st

import auth
import db

st.set_page_config(page_title="Clubhouse Booking | Hermosa Casa", page_icon="C", layout="wide")
auth.require_login()
db.init_db()
db.sidebar_footer()

st.title("Clubhouse Booking")

is_edit = auth.is_edit()

if is_edit:
    st.info("Committee mode: you can add bookings, update booking status, and delete records.")
else:
    st.info("Resident mode: you can submit clubhouse booking details and track booking status.")

tab_add, tab_view = st.tabs(["Book Clubhouse", "View / Track"])

with tab_add:
    with st.form("clubhouse_booking_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        booking_date = col1.date_input("Booking Date *", value=date.today())
        function_type = col2.selectbox("Type of Function *", db.FUNCTION_TYPES)

        col3, col4 = st.columns(2)
        flat_raw = col3.text_input("Owner Flat Number *", placeholder="E-1204")
        owner_name = col4.text_input("Owner Name *")

        col5, col6 = st.columns(2)
        owner_contact = col5.text_input("Owner Contact", placeholder="Email / alternate contact")
        owner_mobile = col6.text_input("Owner Mobile Number *", placeholder="9876543210")

        booked_for_whole_day = st.radio(
            "Booked for whole day?",
            ["Yes", "No"],
            horizontal=True,
        )
        notes = st.text_area(
            "Booking Details",
            height=120,
            placeholder="Mention occasion details, expected guests, timing if not whole day, or special requirements.",
        )

        submitted = st.form_submit_button("Submit Booking", type="primary", use_container_width=True)

    if submitted:
        owner_flat_no = db.normalize_flat(flat_raw)
        owner = owner_name.strip()

        if owner_flat_no and not owner:
            matches = [r for r in db.search_residents(owner_flat_no) if r["flat_no"] == owner_flat_no]
            if matches:
                owner = matches[0]["owner_name"]

        if not owner_flat_no:
            st.error("Invalid flat number. Expected format like E-1204.")
        elif not owner:
            st.error("Owner name is required.")
        elif not owner_mobile.strip():
            st.error("Owner mobile number is required.")
        else:
            db.add_clubhouse_booking(
                booking_date.isoformat(),
                function_type,
                owner_flat_no,
                owner,
                owner_contact.strip(),
                owner_mobile.strip(),
                booked_for_whole_day,
                notes.strip(),
            )
            st.success("Clubhouse booking submitted.")
            st.rerun()

with tab_view:
    counts = db.get_clubhouse_booking_status_counts()
    c1, c2, c3 = st.columns(3)
    c1.metric("BOOKED", counts["BOOKED"])
    c2.metric("PENDING", counts["PENDING"])
    c3.metric("CANCELLED", counts["CANCELLED"])

    st.divider()
    f1, f2, f3 = st.columns(3)
    term = f1.text_input("Search", placeholder="Date / function / flat / owner / mobile")
    status_filter = f2.selectbox("Status", ["All"] + db.BOOKING_STATUSES)
    flat_filter_raw = f3.text_input("Flat Filter", placeholder="Optional exact flat")
    flat_filter = db.normalize_flat(flat_filter_raw) if flat_filter_raw.strip() else ""

    rows = db.search_clubhouse_bookings(term, status_filter, flat_filter)
    st.caption(f"{len(rows)} booking(s)")

    if rows:
        df = pd.DataFrame(rows)[
            [
                "id",
                "booking_date",
                "function_type",
                "owner_flat_no",
                "owner_name",
                "owner_contact",
                "owner_mobile",
                "booked_for_whole_day",
                "status",
                "created_at",
                "updated_at",
            ]
        ]
        df.columns = [
            "ID",
            "Booking Date",
            "Function Type",
            "Flat",
            "Owner",
            "Owner Contact",
            "Owner Mobile",
            "Whole Day",
            "Status",
            "Created",
            "Updated",
        ]
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.download_button(
            "Download CSV",
            df.to_csv(index=False).encode(),
            "clubhouse_bookings.csv",
            "text/csv",
            use_container_width=True,
        )

        for booking in rows:
            with st.expander(
                f"#{booking['id']} | {booking['booking_date']} | "
                f"{booking['function_type']} | {booking['status']}"
            ):
                st.write(f"**Flat:** {booking['owner_flat_no']}")
                st.write(f"**Owner:** {booking['owner_name']}")
                st.write(f"**Owner Contact:** {booking['owner_contact'] or '-'}")
                st.write(f"**Owner Mobile:** {booking['owner_mobile'] or '-'}")
                st.write(f"**Booked for Whole Day:** {booking['booked_for_whole_day']}")
                st.write(f"**Booking Details:** {booking['notes'] or '-'}")
                st.write(f"**Created:** {booking['created_at']}  \n**Updated:** {booking['updated_at']}")

                if is_edit:
                    col_status, col_delete = st.columns([3, 1])
                    current_index = (
                        db.BOOKING_STATUSES.index(booking["status"])
                        if booking["status"] in db.BOOKING_STATUSES
                        else 0
                    )
                    new_status = col_status.selectbox(
                        "Update Status",
                        db.BOOKING_STATUSES,
                        index=current_index,
                        key=f"booking_status_{booking['id']}",
                    )
                    if col_status.button("Save Status", key=f"booking_save_{booking['id']}", use_container_width=True):
                        db.update_clubhouse_booking_status(booking["id"], new_status)
                        st.success("Clubhouse booking status updated.")
                        st.rerun()
                    if col_delete.button("Delete", key=f"booking_delete_{booking['id']}", use_container_width=True):
                        db.delete_clubhouse_booking(booking["id"])
                        st.success("Clubhouse booking deleted.")
                        st.rerun()
    else:
        st.info("No clubhouse bookings found.")
