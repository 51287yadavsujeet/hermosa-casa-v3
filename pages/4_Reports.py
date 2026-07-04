import pandas as pd
import streamlit as st
import db
import auth

st.set_page_config(page_title="Reports | Hermosa Casa", page_icon="📋", layout="wide")
auth.require_login()
db.init_db()
db.sidebar_footer()

st.title("📋 Reports")

residents = db.search_residents("")
vehicles = db.search_vehicles("")
issues = db.search_owner_issues("")

if not residents and not vehicles and not issues:
    st.info("No data yet. Reports will populate once residents, vehicles, or complaints are added.")
    st.stop()

m = db.get_metrics()
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Occupied", m["occupied"])
c2.metric("Owner Occupied", m["owner_occupied"])
c3.metric("Rented", m["rented"])
c4.metric("Occupancy %", f"{m['occupied'] / m['total_flats'] * 100:.1f}%")
c5.metric("Open Complaints", m["open_issues"])

if residents:
    rdf = pd.DataFrame(residents)

    st.subheader("Occupancy by Wing")
    wing_counts = rdf.groupby(["wing", "status"]).size().unstack(fill_value=0)
    st.bar_chart(wing_counts)

    st.subheader("Records by Wing")
    st.bar_chart(rdf["wing"].value_counts().sort_index())

if vehicles:
    vdf = pd.DataFrame(vehicles)
    st.subheader("Vehicles by Type")
    st.bar_chart(vdf["vehicle_type"].value_counts())

if issues:
    idf = pd.DataFrame(issues)
    st.subheader("Complaints by Status")
    st.bar_chart(idf["status"].value_counts())

    st.subheader("Complaints by Category")
    st.bar_chart(idf["issue_category"].fillna("Other").value_counts())

st.divider()
st.subheader("⬇️ Exports")
col1, col2, col3 = st.columns(3)
if residents:
    col1.download_button("Residents CSV", pd.DataFrame(residents).to_csv(index=False).encode(),
                         "residents_report.csv", "text/csv", use_container_width=True)
if vehicles:
    col2.download_button("Vehicles CSV", pd.DataFrame(vehicles).to_csv(index=False).encode(),
                         "vehicles_report.csv", "text/csv", use_container_width=True)
if issues:
    col3.download_button("Complaints CSV", pd.DataFrame(issues).to_csv(index=False).encode(),
                         "owner_issues_report.csv", "text/csv", use_container_width=True)
