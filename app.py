"""Hermosa Casa v3.1 — Home / Dashboard (login required)."""
import streamlit as st
import db
import auth

st.set_page_config(
    page_title="Hermosa Casa Society",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

auth.require_login()
db.init_db()
db.sidebar_footer()

# ---------- top bar ----------
col1, col2 = st.columns([5, 1])
with col1:
    role_label = "Committee (Full Edit)" if auth.is_edit() else "Resident (Read-only)"
    st.caption(f"📱 Optimized for Mobile & Desktop  •  Logged in as **{role_label}**")
with col2:
    auth.logout_button()

st.title("🏢 Hermosa Casa Society Management System")
st.write("Welcome! Use the sidebar pages or the quick tools below.")

if auth.is_edit():
    st.success("✅ Full edit access: Residents (incl. bulk import), Vehicles, Parking, Contacts.")
else:
    st.info("👀 Read-only mode: explore the dashboard, search, reports and emergency contacts.")

# ---------- live dashboard ----------
st.divider()
st.subheader("📊 Live Dashboard")
m = db.get_metrics()
c1, c2, c3 = st.columns(3)
c1.metric("🏠 Total Flats", m["total_flats"])
c2.metric("👨‍👩‍👧 Occupied", m["occupied"])
c3.metric("🏚️ Vacant", m["vacant"])
c4, c5, c6 = st.columns(3)
c4.metric("👨 Owner Occupied", m["owner_occupied"])
c5.metric("🏡 Rented", m["rented"])
c6.metric("🚗 Vehicles", m["vehicles"])
c7, c8, c9 = st.columns(3)
c7.metric("Open Complaints", m["open_issues"])
c8.metric("Registered Pets", m["pets"])
c9.metric("Clubhouse Bookings", m["clubhouse_bookings"])

if m["occupied"] == 0:
    st.info("No resident records yet. Add flats from the **Residents** page and metrics update live.")

# ---------- quick resident search ----------
st.divider()
st.subheader("🔍 Quick Search Residents")
q = st.text_input("Flat / Owner Name / Mobile", placeholder="E-1204 or Sujeet or 98765...", key="quick_res")
if q:
    results = db.search_residents(q)
    if results:
        st.success(f"{len(results)} record(s) found")
        for r in results:
            with st.expander(f"🏠 {r['flat_no']} — {r['owner_name']} ({r['status']})"):
                st.write(f"**Owner:** {r['owner_name']}  \n**Mobile:** {r['owner_mobile'] or '—'}  \n**Email:** {r['owner_email'] or '—'}")
                if r["status"] == "Rented":
                    st.write(f"**Tenant:** {r['tenant_name'] or '—'}  \n**Tenant Mobile:** {r['tenant_mobile'] or '—'}")
                st.write(f"**Members in flat:** {r['members_count']}")
    else:
        st.warning("No matching resident found.")

# ---------- quick vehicle search ----------
st.divider()
st.subheader("🚗 Quick Vehicle Search")
vq = st.text_input("Vehicle Number", placeholder="MH12AB1234", key="quick_veh")
if vq:
    vehicles = db.search_vehicles(vq)
    if vehicles:
        for v in vehicles:
            with st.expander(f"🚗 {v['vehicle_no']} — Flat {v['flat_no']}"):
                st.write(
                    f"**Type:** {v['vehicle_type']}  \n**Model:** {v['model'] or '—'}  \n"
                    f"**Parking Slot:** {v['parking_slot'] or '—'}  \n"
                    f"**Owner:** {v['owner_name'] or 'Not linked to a resident'}  \n"
                    f"**Owner Mobile:** {v['owner_mobile'] or '—'}"
                )
    else:
        st.warning("No matching vehicle found.")

# ---------- quick pet search ----------
st.divider()
st.subheader("Quick Pet Search")
pq = st.text_input("Pet / Flat / Owner / Mobile", placeholder="Bruno or E-1104", key="quick_pet")
if pq:
    pets = db.search_pet_registrations(pq)
    if pets:
        for pet in pets:
            with st.expander(f"{pet['pet_name']} - Flat {pet['flat_no']} ({pet['status']})"):
                st.write(
                    f"**Pet:** {pet['pet_type']}  \n"
                    f"**Breed:** {pet['breed'] or '-'}  \n"
                    f"**Owner:** {pet['owner_name']}  \n"
                    f"**Mobile:** {pet['mobile'] or '-'}  \n"
                    f"**Licence Required:** {pet['license_required']}  \n"
                    f"**Licence No:** {pet['license_no'] or '-'}"
                )
    else:
        st.warning("No matching pet record found.")

# ---------- quick clubhouse booking search ----------
st.divider()
st.subheader("Quick Clubhouse Booking Search")
bq = st.text_input("Date / Function / Flat / Owner / Mobile", placeholder="Birthday or E-1204", key="quick_booking")
if bq:
    bookings = db.search_clubhouse_bookings(bq)
    if bookings:
        for booking in bookings:
            with st.expander(
                f"{booking['booking_date']} - {booking['function_type']} "
                f"({booking['status']})"
            ):
                st.write(
                    f"**Flat:** {booking['owner_flat_no']}  \n"
                    f"**Owner:** {booking['owner_name']}  \n"
                    f"**Owner Mobile:** {booking['owner_mobile'] or '-'}  \n"
                    f"**Owner Contact:** {booking['owner_contact'] or '-'}  \n"
                    f"**Whole Day:** {booking['booked_for_whole_day']}"
                )
    else:
        st.warning("No matching clubhouse booking found.")

st.divider()
st.caption("Full management tools: sidebar -> Residents, Vehicles, Parking, Reports, Owner Issues, Pet Information, Clubhouse Booking, Emergency Contacts.")
