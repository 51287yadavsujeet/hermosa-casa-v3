import pandas as pd
import streamlit as st
import db
import auth

st.set_page_config(page_title="Residents | Hermosa Casa", page_icon="👪", layout="wide")
auth.require_login()
db.init_db()
db.sidebar_footer()

st.title("👪 Residents")

is_edit = auth.is_edit()

if not is_edit:
    st.info("🔒 You are in **Read-only** mode. You can view and search all data, but cannot add, edit, or delete records. Contact the committee for changes.")

tab_view, tab_add, tab_bulk = st.tabs(["📋 View / Search", "➕ Add / Update Single Flat", "📥 Bulk Import from Excel/CSV"])

with tab_add:
    if not is_edit:
        st.warning("Read-only mode: Single record editing is disabled.")
    else:
        with st.form("resident_form", clear_on_submit=False):
            flat_raw = st.text_input("Flat Number *", placeholder="E-1204 (Wing B–G, Floor 1–16, Flat 01–08)")
            owner_name = st.text_input("Owner Name *")
            col1, col2 = st.columns(2)
            owner_mobile = col1.text_input("Owner Mobile")
            owner_email = col2.text_input("Owner Email")
            status = st.selectbox("Occupancy Status *", db.OCCUPANCY_STATUSES)
            tenant_name = st.text_input("Tenant Name (if rented)")
            tenant_mobile = st.text_input("Tenant Mobile (if rented)")
            members = st.number_input("Members in Flat", min_value=0, max_value=20, value=1)
            submitted = st.form_submit_button("💾 Save Flat Record", use_container_width=True)

        if submitted:
            flat_no = db.normalize_flat(flat_raw)
            if not flat_no:
                st.error("Invalid flat number. Expected format like **E-1204**: Wing B–G, Floor 1–16, Flat 01–08.")
            elif not owner_name.strip():
                st.error("Owner name is required.")
            elif status == "Rented" and not tenant_name.strip():
                st.error("Tenant name is required for rented flats.")
            else:
                db.upsert_resident(flat_no, owner_name.strip(), owner_mobile.strip(),
                                   owner_email.strip(), status, tenant_name.strip(),
                                   tenant_mobile.strip(), int(members))
                st.success(f"Saved record for {flat_no}.")

with tab_view:
    colf1, colf2, colf3 = st.columns(3)
    wing_f = colf1.selectbox("Wing", ["All"] + db.WINGS)
    status_f = colf2.selectbox("Status", ["All"] + db.OCCUPANCY_STATUSES)
    term = colf3.text_input("Search", placeholder="Flat / name / mobile")

    rows = db.search_residents(term)
    if wing_f != "All":
        rows = [r for r in rows if r["wing"] == wing_f]
    if status_f != "All":
        rows = [r for r in rows if r["status"] == status_f]

    st.caption(f"{len(rows)} record(s)")
    if rows:
        df = pd.DataFrame(rows)[["flat_no", "owner_name", "owner_mobile", "status",
                                 "tenant_name", "tenant_mobile", "members_count"]]
        df.columns = ["Flat", "Owner", "Mobile", "Status", "Tenant", "Tenant Mobile", "Members"]
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.download_button("⬇️ Download CSV", df.to_csv(index=False).encode(),
                           "residents.csv", "text/csv", use_container_width=True)

        if is_edit:
            with st.expander("🗑️ Delete a record"):
                flat_del = st.selectbox("Select flat to delete", [r["flat_no"] for r in rows])
                if st.button("Delete permanently", type="primary"):
                    db.delete_resident(flat_del)
                    st.success(f"Deleted {flat_del}.")
                    st.rerun()
        else:
            st.caption("Delete is disabled in read-only mode.")
    else:
        st.info("No resident records yet. Use the **Add / Update Single Flat** tab (committee only) to create the first one.")

# ============================================================
# BULK IMPORT TAB (Committee only)
# ============================================================
with tab_bulk:
    if not is_edit:
        st.warning("🔒 Bulk import is only available to committee members with edit access.")
    else:
        st.subheader("📥 Bulk Import Residents from Excel or CSV")
        st.markdown("""
        Upload a file with columns:  
        `flat_no`, `owner_name` (required), `owner_mobile`, `owner_email`, `status`, `tenant_name`, `tenant_mobile`, `members_count`

        - `flat_no` can be in any accepted format (E1204, B-0101, etc.)
        - `status` must be one of: Owner Occupied, Rented, Vacant
        - Rows with invalid flats or missing owner_name will be skipped with errors shown.
        """)

        # Download template
        template_cols = ["flat_no", "owner_name", "owner_mobile", "owner_email", "status", "tenant_name", "tenant_mobile", "members_count"]
        template_df = pd.DataFrame([
            ["E-1204", "Rahul Sharma", "9876543210", "rahul@email.com", "Owner Occupied", "", "", 4],
            ["B-0101", "Priya Patel", "9876543211", "", "Rented", "Amit Patel", "9876543212", 3],
        ], columns=template_cols)

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                "⬇️ Download CSV Template",
                template_df.to_csv(index=False).encode(),
                "resident_import_template.csv",
                "text/csv",
                use_container_width=True
            )
        with col_dl2:
            # Also offer Excel template
            import io
            buffer = io.BytesIO()
            template_df.to_excel(buffer, index=False, sheet_name="Residents")
            buffer.seek(0)
            st.download_button(
                "⬇️ Download Excel Template",
                buffer,
                "resident_import_template.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        uploaded = st.file_uploader("Upload Excel (.xlsx) or CSV file", type=["xlsx", "csv"], key="bulk_residents")

        if uploaded:
            try:
                if uploaded.name.lower().endswith(".csv"):
                    df = pd.read_csv(uploaded)
                else:
                    df = pd.read_excel(uploaded, engine="openpyxl")

                # Normalize column names
                df.columns = (
                    df.columns
                    .str.strip()
                    .str.lower()
                    .str.replace(" ", "_")
                )

                required_cols = [
                    "flat_no",
                    "owner_name"
                ]

                missing = [
                    c for c in required_cols
                    if c not in df.columns
                ]

                if missing:
                    st.error(
                        f"Missing required columns: {', '.join(missing)}"
                    )
                    st.stop()

                st.success(f"File loaded: {len(df)} rows detected")
                st.dataframe(df.head(10), use_container_width=True)

                if st.button("🚀 Import Valid Rows", type="primary", use_container_width=True):
                    success_count = 0
                    error_rows = []

                    import math

                    def _clean(val):
                        """NaN -> '', floats like 9876543210.0 -> '9876543210'."""
                        if val is None or (isinstance(val, float) and math.isnan(val)):
                            return ""
                        if isinstance(val, float) and val.is_integer():
                            return str(int(val))
                        return str(val).strip()

                    for idx, row in df.iterrows():
                        flat_raw = _clean(row.get("flat_no"))
                        owner_name = _clean(row.get("owner_name"))
                        status = _clean(row.get("status")) or "Owner Occupied"

                        flat_no = db.normalize_flat(flat_raw)
                        if not flat_no or not owner_name:
                            error_rows.append(f"Row {idx+2}: Invalid flat or missing owner_name → skipped")
                            continue
                        if status not in db.OCCUPANCY_STATUSES:
                            status = "Owner Occupied"

                        try:
                            db.upsert_resident(
                                flat_no,
                                owner_name,
                                _clean(row.get("owner_mobile")),
                                _clean(row.get("owner_email")),
                                status,
                                _clean(row.get("tenant_name")),
                                _clean(row.get("tenant_mobile")),
                                int(float(_clean(row.get("members_count")) or 1))
                            )
                            success_count += 1
                        except Exception as e:
                            error_rows.append(f"Row {idx+2}: {str(e)}")

                   # st.success(f"✅ Successfully imported/updated {success_count} record(s)")
                    st.success(
                        f"✅ Successfully imported/updated {success_count} record(s)"
                    )

                    st.info(
                        f"Skipped rows: {len(error_rows)}"
                    )
                    if error_rows:
                        st.warning("Some rows had issues:")
                        for err in error_rows[:10]:
                            st.text(err)
                        if len(error_rows) > 10:
                            st.text(f"... and {len(error_rows)-10} more")
                    st.rerun()

            except Exception as e:
                st.error(f"Failed to read file: {e}")