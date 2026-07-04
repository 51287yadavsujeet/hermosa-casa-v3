import re
import pandas as pd
import streamlit as st
import db
import auth

st.set_page_config(page_title="Vehicles | Hermosa Casa", page_icon="🚗", layout="wide")
auth.require_login()
db.init_db()
db.sidebar_footer()

st.title("🚗 Vehicles")

is_edit = auth.is_edit()

if not is_edit:
    st.info("🔒 Read-only mode: You can search and view all vehicles (with owner details), but cannot register or remove vehicles.")

VEHICLE_RE = re.compile(r"^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{3,4}$")

tab_view, tab_add = st.tabs(["📋 View / Search", "➕ Register Vehicle"])

with tab_add:
    if not is_edit:
        st.warning("Read-only mode: Vehicle registration is disabled.")
    else:
        with st.form("vehicle_form"):
            vehicle_no = st.text_input("Vehicle Number *", placeholder="MH12AB1234")
            flat_raw = st.text_input("Flat Number *", placeholder="E-1104")
            vtype = st.selectbox("Vehicle Type *", db.VEHICLE_TYPES)
            model = st.text_input("Make / Model", placeholder="Hyundai Creta")
            slot = st.text_input("Parking Slot", placeholder="B-P1-23")
            submitted = st.form_submit_button("💾 Register Vehicle", use_container_width=True)

        if submitted:
            vno = vehicle_no.strip().upper().replace(" ", "")
            flat_no = db.normalize_flat(flat_raw)
            if not VEHICLE_RE.match(vno):
                st.error("Invalid vehicle number. Expected format like **MH12AB1234**.")
            elif not flat_no:
                st.error("Invalid flat number. Expected format like **E-1204**.")
            else:
                ok, msg = db.add_vehicle(vno, flat_no, vtype, model.strip(), slot.strip())
                (st.success if ok else st.error)(msg)

with tab_view:
    term = st.text_input("Search", placeholder="Vehicle number or flat")
    rows = db.search_vehicles(term)
    st.caption(f"{len(rows)} vehicle(s)")
    if rows:
        df = pd.DataFrame(rows)[["vehicle_no", "flat_no", "vehicle_type", "model", "parking_slot", "owner_name"]]
        df.columns = ["Vehicle No", "Flat", "Type", "Model", "Slot", "Owner"]
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.download_button("⬇️ Download CSV", df.to_csv(index=False).encode(),
                           "vehicles.csv", "text/csv", use_container_width=True)

        if is_edit:
            with st.expander("🗑️ Remove a vehicle"):
                v_del = st.selectbox("Select vehicle", [r["vehicle_no"] for r in rows])
                if st.button("Remove permanently", type="primary"):
                    db.delete_vehicle(v_del)
                    st.success(f"Removed {v_del}.")
                    st.rerun()
        else:
            st.caption("Remove vehicle is disabled in read-only mode.")
    else:
        st.info("No vehicles registered yet.")