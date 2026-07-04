import pandas as pd
import streamlit as st
import db
import auth

st.set_page_config(page_title="Parking | Hermosa Casa", page_icon="🅿️", layout="wide")
auth.require_login()
db.init_db()
db.sidebar_footer()

st.title("🅿️ Parking")

is_edit = auth.is_edit()

if not is_edit:
    st.info("🔒 Read-only mode: You can view current parking allocations. Updating slots is restricted to committee members.")

vehicles = db.search_vehicles("")
allotted = [v for v in vehicles if v["parking_slot"]]
unallotted = [v for v in vehicles if not v["parking_slot"]]

c1, c2, c3 = st.columns(3)
c1.metric("Registered Vehicles", len(vehicles))
c2.metric("Slots Allotted", len(allotted))
c3.metric("Pending Allotment", len(unallotted))

st.divider()
st.subheader("Allotted Slots")
if allotted:
    df = pd.DataFrame(allotted)[["parking_slot", "vehicle_no", "flat_no", "vehicle_type", "owner_name"]]
    df.columns = ["Slot", "Vehicle No", "Flat", "Type", "Owner"]
    st.dataframe(df.sort_values("Slot"), use_container_width=True, hide_index=True)
else:
    st.info("No parking slots allotted yet. Assign a slot while registering a vehicle on the **Vehicles** page.")

if unallotted:
    st.subheader("⚠️ Vehicles Without a Slot")
    df2 = pd.DataFrame(unallotted)[["vehicle_no", "flat_no", "vehicle_type", "owner_name"]]
    df2.columns = ["Vehicle No", "Flat", "Type", "Owner"]
    st.dataframe(df2, use_container_width=True, hide_index=True)