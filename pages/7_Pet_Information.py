import pandas as pd
import streamlit as st

import auth
import db

st.set_page_config(page_title="Pet Information | Hermosa Casa", page_icon="P", layout="wide")
auth.require_login()
db.init_db()
db.sidebar_footer()

st.title("Pet Information / Registration")

is_edit = auth.is_edit()

if is_edit:
    st.info("Committee mode: you can add pet records, update registration status, and delete records.")
else:
    st.info("Resident mode: you can submit pet information and track registration status.")

tab_add, tab_view = st.tabs(["Register Pet", "View / Track"])

with tab_add:
    with st.form("pet_registration_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        flat_raw = col1.text_input("Owner Flat Number *", placeholder="E-1204")
        mobile = col2.text_input("Mobile Number", placeholder="9876543210")

        owner_name = st.text_input("Owner Name *")

        col3, col4 = st.columns(2)
        pet_name = col3.text_input("Pet Name *", placeholder="Bruno")
        pet_type = col4.selectbox("Pet *", db.PET_TYPES)

        breed = st.text_input("Breed", placeholder="Labrador / Persian / Other")
        vaccination_details = st.text_area(
            "Vaccination Detail",
            height=120,
            placeholder="Mention vaccine names, dates, next due date, or vet details.",
        )

        license_required = st.radio(
            "Pet licence required?",
            ["No", "Yes"],
            horizontal=True,
            help="Select Yes if your society or local authority requires a pet licence.",
        )
        col5, col6 = st.columns(2)
        license_no = col5.text_input("Licence / Registration Number")
        license_details = col6.text_input("Licence Detail", placeholder="Issuing authority / expiry date")

        submitted = st.form_submit_button("Submit Pet Registration", type="primary", use_container_width=True)

    if submitted:
        flat_no = db.normalize_flat(flat_raw)
        owner = owner_name.strip()

        if flat_no and not owner:
            matches = [r for r in db.search_residents(flat_no) if r["flat_no"] == flat_no]
            if matches:
                owner = matches[0]["owner_name"]

        if not flat_no:
            st.error("Invalid flat number. Expected format like E-1204.")
        elif not owner:
            st.error("Owner name is required.")
        elif not pet_name.strip():
            st.error("Pet name is required.")
        elif license_required == "Yes" and not license_no.strip():
            st.error("Licence / registration number is required when licence is marked required.")
        else:
            db.add_pet_registration(
                flat_no,
                owner,
                mobile.strip(),
                pet_name.strip(),
                pet_type,
                breed.strip(),
                vaccination_details.strip(),
                license_required,
                license_no.strip(),
                license_details.strip(),
            )
            st.success("Pet information submitted.")
            st.rerun()

with tab_view:
    counts = db.get_pet_status_counts()
    c1, c2, c3 = st.columns(3)
    c1.metric("REGISTERED", counts["REGISTERED"])
    c2.metric("PENDING", counts["PENDING"])
    c3.metric("INACTIVE", counts["INACTIVE"])

    st.divider()
    f1, f2, f3 = st.columns(3)
    term = f1.text_input("Search", placeholder="Flat / owner / mobile / pet / licence")
    status_filter = f2.selectbox("Status", ["All"] + db.PET_REGISTRATION_STATUSES)
    flat_filter_raw = f3.text_input("Flat Filter", placeholder="Optional exact flat")
    flat_filter = db.normalize_flat(flat_filter_raw) if flat_filter_raw.strip() else ""

    rows = db.search_pet_registrations(term, status_filter, flat_filter)
    st.caption(f"{len(rows)} pet record(s)")

    if rows:
        df = pd.DataFrame(rows)[
            [
                "id",
                "flat_no",
                "owner_name",
                "mobile",
                "pet_name",
                "pet_type",
                "breed",
                "vaccination_details",
                "license_required",
                "license_no",
                "status",
                "created_at",
                "updated_at",
            ]
        ]
        df.columns = [
            "ID",
            "Flat",
            "Owner",
            "Mobile",
            "Pet Name",
            "Pet",
            "Breed",
            "Vaccination Detail",
            "Licence Required",
            "Licence No",
            "Status",
            "Created",
            "Updated",
        ]
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.download_button(
            "Download CSV",
            df.to_csv(index=False).encode(),
            "pet_registrations.csv",
            "text/csv",
            use_container_width=True,
        )

        for pet in rows:
            with st.expander(f"#{pet['id']} | {pet['flat_no']} | {pet['pet_name']} | {pet['status']}"):
                st.write(f"**Owner:** {pet['owner_name']}")
                st.write(f"**Mobile:** {pet['mobile'] or '-'}")
                st.write(f"**Pet:** {pet['pet_type']}  \n**Breed:** {pet['breed'] or '-'}")
                st.write(f"**Vaccination Detail:** {pet['vaccination_details'] or '-'}")
                st.write(
                    f"**Licence Required:** {pet['license_required']}  \n"
                    f"**Licence / Registration Number:** {pet['license_no'] or '-'}  \n"
                    f"**Licence Detail:** {pet['license_details'] or '-'}"
                )
                st.write(f"**Created:** {pet['created_at']}  \n**Updated:** {pet['updated_at']}")

                if is_edit:
                    col_status, col_delete = st.columns([3, 1])
                    current_index = (
                        db.PET_REGISTRATION_STATUSES.index(pet["status"])
                        if pet["status"] in db.PET_REGISTRATION_STATUSES
                        else 0
                    )
                    new_status = col_status.selectbox(
                        "Update Status",
                        db.PET_REGISTRATION_STATUSES,
                        index=current_index,
                        key=f"pet_status_{pet['id']}",
                    )
                    if col_status.button("Save Status", key=f"pet_save_{pet['id']}", use_container_width=True):
                        db.update_pet_registration_status(pet["id"], new_status)
                        st.success("Pet registration status updated.")
                        st.rerun()
                    if col_delete.button("Delete", key=f"pet_delete_{pet['id']}", use_container_width=True):
                        db.delete_pet_registration(pet["id"])
                        st.success("Pet record deleted.")
                        st.rerun()
    else:
        st.info("No pet records found.")
