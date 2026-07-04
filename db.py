"""Hermosa Casa v3.1 — data layer.

Supabase Postgres (persistent) when SUPABASE_DB_URL is set in secrets;
otherwise local SQLite for development. Same function API as v2.
"""
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import streamlit as st

WINGS = ["B", "C", "D", "E", "F", "G"]
#WINGS = ["A", "B", "C", "D", "E", "F", "G"]

# Society format:
# E-1204, E1204, B-0101, B0101
FLAT_RE_STANDARD = re.compile(r"^([A-G])-?(\d{1,2})(0[1-8])$")

# Friendly import format:
# A-101, A101, B-205
FLAT_RE_SHORT = re.compile(r"^([A-G])-?(\d)(0?[1-8])$")

FLOORS = list(range(1, 17))
FLATS_PER_FLOOR = 8
TOTAL_FLATS = len(WINGS) * len(FLOORS) * FLATS_PER_FLOOR  # 768

OCCUPANCY_STATUSES = ["Owner Occupied", "Rented", "Vacant"]
VEHICLE_TYPES = ["Car", "Bike", "Scooter", "EV Car", "EV Bike", "Other"]
ISSUE_CATEGORIES = ["Maintenance", "Plumbing", "Electrical", "Security", "Housekeeping", "Parking", "Other"]
ISSUE_STATUSES = ["OPEN", "WORKING", "PENDING", "CLOSED"]
PET_TYPES = ["Dog", "Cat", "Bird", "Fish", "Rabbit", "Other"]
PET_REGISTRATION_STATUSES = ["REGISTERED", "PENDING", "INACTIVE"]
FUNCTION_TYPES = ["Birthday", "Anniversary", "Meeting", "Festival", "Religious Function", "Family Function", "Other"]
BOOKING_STATUSES = ["BOOKED", "PENDING", "CANCELLED"]

FLAT_RE = re.compile(r"^([B-G])-?(\d{1,2})(0[1-8])$")
DB_PATH = Path(__file__).parent / "society.db"

_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS residents (
        flat_no        TEXT PRIMARY KEY,
        wing           TEXT NOT NULL,
        floor          INTEGER NOT NULL,
        owner_name     TEXT NOT NULL,
        owner_mobile   TEXT,
        owner_email    TEXT,
        status         TEXT NOT NULL DEFAULT 'Owner Occupied',
        tenant_name    TEXT,
        tenant_mobile  TEXT,
        members_count  INTEGER DEFAULT 1,
        updated_at     {ts}
    )""",
    """CREATE TABLE IF NOT EXISTS vehicles (
        id           {pk},
        vehicle_no   TEXT NOT NULL UNIQUE,
        flat_no      TEXT NOT NULL,
        vehicle_type TEXT NOT NULL,
        model        TEXT,
        parking_slot TEXT,
        updated_at   {ts}
    )""",
    """CREATE TABLE IF NOT EXISTS emergency_contacts (
        id       {pk},
        category TEXT NOT NULL,
        name     TEXT NOT NULL,
        phone    TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS owner_issues (
        id              {pk},
        flat_no         TEXT NOT NULL,
        owner_name      TEXT NOT NULL,
        mobile          TEXT,
        issue_category  TEXT,
        complaint_title TEXT NOT NULL,
        complaint_text  TEXT NOT NULL,
        status          TEXT NOT NULL DEFAULT 'OPEN',
        created_at      {ts},
        updated_at      {ts}
    )""",
    """CREATE TABLE IF NOT EXISTS pet_registrations (
        id                  {pk},
        flat_no             TEXT NOT NULL,
        owner_name          TEXT NOT NULL,
        mobile              TEXT,
        pet_name            TEXT NOT NULL,
        pet_type            TEXT NOT NULL,
        breed               TEXT,
        vaccination_details TEXT,
        license_required    TEXT NOT NULL DEFAULT 'No',
        license_no          TEXT,
        license_details     TEXT,
        status              TEXT NOT NULL DEFAULT 'REGISTERED',
        created_at          {ts},
        updated_at          {ts}
    )""",
    """CREATE TABLE IF NOT EXISTS clubhouse_bookings (
        id                   {pk},
        booking_date         TEXT NOT NULL,
        function_type        TEXT NOT NULL,
        owner_flat_no        TEXT NOT NULL,
        owner_name           TEXT NOT NULL,
        owner_contact        TEXT,
        owner_mobile         TEXT,
        booked_for_whole_day TEXT NOT NULL DEFAULT 'Yes',
        notes                TEXT,
        status               TEXT NOT NULL DEFAULT 'BOOKED',
        created_at           {ts},
        updated_at           {ts}
    )""",
]

_SEED_CONTACTS = [
    ("Security", "Main Gate Security", "020-0000-0001"),
    ("Society Office", "Society Manager", "020-0000-0002"),
    ("Maintenance", "Electrician (On-call)", "98XXXXXX01"),
    ("Maintenance", "Plumber (On-call)", "98XXXXXX02"),
    ("Medical", "Ambulance", "108"),
    ("Fire", "Fire Brigade", "101"),
    ("Police", "Police Control Room", "100"),
]


def normalize_flat(raw: str):
    """
    Accepts:

        A-101
        A101
        B-0101
        B0101
        E-1204
        E1204

    Returns:

        A-0101
        B-0101
        E-1204
    """

    if not raw:
        return None

    value = str(raw).strip().upper().replace(" ", "")

    # Standard format
    m = FLAT_RE_STANDARD.match(value)

    if m:
        wing = m.group(1)
        floor = int(m.group(2))
        flat = m.group(3)

        if floor not in FLOORS:
            return None

        return f"{wing}-{floor:02d}{flat}"

    # Short format
    m = FLAT_RE_SHORT.match(value)

    if m:
        wing = m.group(1)
        floor = int(m.group(2))
        flat = int(m.group(3))

        if floor < 1 or floor > 16:
            return None

        if flat < 1 or flat > 8:
            return None

        return f"{wing}-{floor:02d}{flat:02d}"

    return None


# ---------- backend selection ----------
def _supabase_url() -> str:
    try:
        return str(st.secrets.get("SUPABASE_DB_URL", "") or "").strip()
    except Exception:
        return ""


def _connect():
    """Return (backend, connection). Postgres if configured, else SQLite."""
    url = _supabase_url()
    if url:
        import psycopg2  # imported lazily so SQLite-only setups don't need it
        return "postgres", psycopg2.connect(url)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return "sqlite", conn


@contextmanager
def db_cursor(commit=True):
    """Yield (cursor, backend). Connection is always closed afterwards."""
    backend, conn = _connect()
    if backend == "postgres":
        from psycopg2.extras import RealDictCursor
        cur = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cur = conn.cursor()
    try:
        yield cur, backend
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def _ph(backend):
    """SQL placeholder for the backend."""
    return "%s" if backend == "postgres" else "?"


@st.cache_resource
def init_db():
    """Create tables and seed emergency contacts. Cached: runs once per server."""
    with db_cursor() as (cur, backend):
        pk = "SERIAL PRIMARY KEY" if backend == "postgres" else "INTEGER PRIMARY KEY AUTOINCREMENT"
        ts = ("TIMESTAMP DEFAULT CURRENT_TIMESTAMP" if backend == "postgres"
              else "TEXT DEFAULT (datetime('now'))")
        for stmt in _SCHEMA:                      # one statement per execute —
            cur.execute(stmt.format(pk=pk, ts=ts))  # works on both backends
        cur.execute("SELECT COUNT(*) AS n FROM emergency_contacts")
        row = cur.fetchone()
        count = row["n"] if backend == "postgres" else row[0]
        if count == 0:
            p = _ph(backend)
            cur.executemany(
                f"INSERT INTO emergency_contacts (category, name, phone) VALUES ({p},{p},{p})",
                _SEED_CONTACTS,
            )
    return True


# ---------- metrics ----------
def get_metrics():
    with db_cursor(commit=False) as (cur, backend):
        def count(sql, params=()):
            cur.execute(sql, params)
            row = cur.fetchone()
            return row["n"] if backend == "postgres" else row[0]

        p = _ph(backend)
        owner = count(f"SELECT COUNT(*) AS n FROM residents WHERE status={p}", ("Owner Occupied",))
        rented = count(f"SELECT COUNT(*) AS n FROM residents WHERE status={p}", ("Rented",))
        vehicles = count("SELECT COUNT(*) AS n FROM vehicles")
        open_issues = count(f"SELECT COUNT(*) AS n FROM owner_issues WHERE status <> {p}", ("CLOSED",))
        pets = count("SELECT COUNT(*) AS n FROM pet_registrations")
        pending_pets = count(f"SELECT COUNT(*) AS n FROM pet_registrations WHERE status = {p}", ("PENDING",))
        clubhouse_bookings = count(f"SELECT COUNT(*) AS n FROM clubhouse_bookings WHERE status <> {p}", ("CANCELLED",))
    return {
        "total_flats": TOTAL_FLATS,
        "occupied": owner + rented,
        "owner_occupied": owner,
        "rented": rented,
        "vacant": TOTAL_FLATS - owner - rented,
        "vehicles": vehicles,
        "open_issues": open_issues,
        "pets": pets,
        "pending_pets": pending_pets,
        "clubhouse_bookings": clubhouse_bookings,
    }


# ---------- residents ----------
def upsert_resident(flat_no, owner_name, owner_mobile, owner_email,
                    status, tenant_name, tenant_mobile, members_count):
    wing, rest = flat_no.split("-")
    floor = int(rest[:-2])
    with db_cursor() as (cur, backend):
        p = _ph(backend)
        now = "CURRENT_TIMESTAMP" if backend == "postgres" else "datetime('now')"
        excl = "EXCLUDED" if backend == "postgres" else "excluded"
        cur.execute(
            f"""INSERT INTO residents
                (flat_no, wing, floor, owner_name, owner_mobile, owner_email,
                 status, tenant_name, tenant_mobile, members_count, updated_at)
                VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{now})
                ON CONFLICT (flat_no) DO UPDATE SET
                  owner_name={excl}.owner_name,
                  owner_mobile={excl}.owner_mobile,
                  owner_email={excl}.owner_email,
                  status={excl}.status,
                  tenant_name={excl}.tenant_name,
                  tenant_mobile={excl}.tenant_mobile,
                  members_count={excl}.members_count,
                  updated_at={now}""",
            (flat_no, wing, floor, owner_name, owner_mobile, owner_email,
             status, tenant_name, tenant_mobile, members_count),
        )


def delete_resident(flat_no):
    with db_cursor() as (cur, backend):
        p = _ph(backend)
        cur.execute(f"DELETE FROM vehicles WHERE flat_no={p}", (flat_no,))
        cur.execute(f"DELETE FROM residents WHERE flat_no={p}", (flat_no,))


def search_residents(term=""):
    like = f"%{term.strip()}%"
    with db_cursor(commit=False) as (cur, backend):
        p, op = _ph(backend), ("ILIKE" if backend == "postgres" else "LIKE")
        nocase = "" if backend == "postgres" else " COLLATE NOCASE"
        cur.execute(
            f"""SELECT * FROM residents
                WHERE flat_no {op} {p} OR owner_name {op} {p}{nocase}
                   OR owner_mobile {op} {p} OR tenant_name {op} {p}{nocase}
                   OR tenant_mobile {op} {p}
                ORDER BY wing, floor, flat_no""",
            (like, like, like, like, like),
        )
        return [dict(r) for r in cur.fetchall()]


# ---------- vehicles ----------
def add_vehicle(vehicle_no, flat_no, vehicle_type, model, parking_slot):
    vno = vehicle_no.upper().replace(" ", "")
    try:
        with db_cursor() as (cur, backend):
            p = _ph(backend)
            now = "CURRENT_TIMESTAMP" if backend == "postgres" else "datetime('now')"
            cur.execute(
                f"INSERT INTO vehicles (vehicle_no, flat_no, vehicle_type, model, parking_slot, updated_at) "
                f"VALUES ({p},{p},{p},{p},{p},{now})",
                (vno, flat_no, vehicle_type, model, parking_slot),
            )

        return True, "Vehicle added."
    except Exception as e:  # unique violation on either backend
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            return False, "This vehicle number already exists."
        raise


def delete_vehicle(vehicle_no):
    with db_cursor() as (cur, backend):
        cur.execute(f"DELETE FROM vehicles WHERE vehicle_no={_ph(backend)}", (vehicle_no,))


def search_vehicles(term=""):
    like = f"%{term.strip().upper().replace(' ', '')}%"
    with db_cursor(commit=False) as (cur, backend):
        p, op = _ph(backend), ("ILIKE" if backend == "postgres" else "LIKE")
        cur.execute(
            f"""SELECT v.*, r.owner_name, r.owner_mobile
                FROM vehicles v LEFT JOIN residents r ON v.flat_no = r.flat_no
                WHERE v.vehicle_no {op} {p} OR v.flat_no {op} {p}
                ORDER BY v.flat_no""",
            (like, like),
        )
        return [dict(r) for r in cur.fetchall()]


# ---------- emergency contacts ----------
def get_contacts():
    with db_cursor(commit=False) as (cur, backend):
        cur.execute("SELECT * FROM emergency_contacts ORDER BY category, name")
        return [dict(r) for r in cur.fetchall()]


def add_contact(category, name, phone):
    with db_cursor() as (cur, backend):
        p = _ph(backend)
        cur.execute(
            f"INSERT INTO emergency_contacts (category, name, phone) VALUES ({p},{p},{p})",
            (category, name, phone),
        )


def delete_contact(contact_id):
    with db_cursor() as (cur, backend):
        cur.execute(f"DELETE FROM emergency_contacts WHERE id={_ph(backend)}", (contact_id,))


# ---------- owner issues / complaints ----------
def add_owner_issue(flat_no, owner_name, mobile, issue_category, complaint_title, complaint_text):
    if issue_category not in ISSUE_CATEGORIES:
        issue_category = "Other"
    with db_cursor() as (cur, backend):
        p = _ph(backend)
        now = "CURRENT_TIMESTAMP" if backend == "postgres" else "datetime('now')"
        cur.execute(
            f"""INSERT INTO owner_issues
                (flat_no, owner_name, mobile, issue_category, complaint_title,
                 complaint_text, status, created_at, updated_at)
                VALUES ({p},{p},{p},{p},{p},{p},{p},{now},{now})""",
            (
                flat_no,
                owner_name,
                mobile,
                issue_category,
                complaint_title,
                complaint_text,
                "OPEN",
            ),
        )


def search_owner_issues(term="", status="All", flat_no=""):
    like = f"%{term.strip()}%"
    with db_cursor(commit=False) as (cur, backend):
        p, op = _ph(backend), ("ILIKE" if backend == "postgres" else "LIKE")
        nocase = "" if backend == "postgres" else " COLLATE NOCASE"
        sql = f"""SELECT * FROM owner_issues
                  WHERE (flat_no {op} {p}
                         OR owner_name {op} {p}{nocase}
                         OR mobile {op} {p}
                         OR issue_category {op} {p}{nocase}
                         OR complaint_title {op} {p}{nocase}
                         OR complaint_text {op} {p}{nocase})"""
        params = [like, like, like, like, like, like]

        if status and status != "All":
            sql += f" AND status={p}"
            params.append(status)
        if flat_no:
            sql += f" AND flat_no={p}"
            params.append(flat_no)

        sql += " ORDER BY updated_at DESC, created_at DESC"
        cur.execute(sql, tuple(params))
        return [dict(r) for r in cur.fetchall()]


def get_issue_status_counts():
    with db_cursor(commit=False) as (cur, backend):
        cur.execute("SELECT status, COUNT(*) AS n FROM owner_issues GROUP BY status")
        counts = {status: 0 for status in ISSUE_STATUSES}
        for row in cur.fetchall():
            status = row["status"] if backend == "postgres" else row[0]
            count = row["n"] if backend == "postgres" else row[1]
            counts[status] = count
        return counts


def update_owner_issue_status(issue_id, status):
    if status not in ISSUE_STATUSES:
        raise ValueError("Invalid issue status.")
    with db_cursor() as (cur, backend):
        p = _ph(backend)
        now = "CURRENT_TIMESTAMP" if backend == "postgres" else "datetime('now')"
        cur.execute(
            f"UPDATE owner_issues SET status={p}, updated_at={now} WHERE id={p}",
            (status, issue_id),
        )


def delete_owner_issue(issue_id):
    with db_cursor() as (cur, backend):
        cur.execute(f"DELETE FROM owner_issues WHERE id={_ph(backend)}", (issue_id,))


# ---------- pet registrations ----------
def add_pet_registration(flat_no, owner_name, mobile, pet_name, pet_type, breed,
                         vaccination_details, license_required, license_no,
                         license_details):
    if pet_type not in PET_TYPES:
        pet_type = "Other"
    license_required = "Yes" if str(license_required).strip().lower() == "yes" else "No"
    license_no = str(license_no or "").strip()
    status = "PENDING" if license_required == "Yes" and not license_no else "REGISTERED"

    with db_cursor() as (cur, backend):
        p = _ph(backend)
        now = "CURRENT_TIMESTAMP" if backend == "postgres" else "datetime('now')"
        cur.execute(
            f"""INSERT INTO pet_registrations
                (flat_no, owner_name, mobile, pet_name, pet_type, breed,
                 vaccination_details, license_required, license_no,
                 license_details, status, created_at, updated_at)
                VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{now},{now})""",
            (
                flat_no,
                owner_name,
                mobile,
                pet_name,
                pet_type,
                breed,
                vaccination_details,
                license_required,
                license_no,
                license_details,
                status,
            ),
        )


def search_pet_registrations(term="", status="All", flat_no=""):
    like = f"%{term.strip()}%"
    with db_cursor(commit=False) as (cur, backend):
        p, op = _ph(backend), ("ILIKE" if backend == "postgres" else "LIKE")
        nocase = "" if backend == "postgres" else " COLLATE NOCASE"
        sql = f"""SELECT * FROM pet_registrations
                  WHERE (flat_no {op} {p}
                         OR owner_name {op} {p}{nocase}
                         OR mobile {op} {p}
                         OR pet_name {op} {p}{nocase}
                         OR pet_type {op} {p}{nocase}
                         OR breed {op} {p}{nocase}
                         OR vaccination_details {op} {p}{nocase}
                         OR license_no {op} {p}{nocase}
                         OR license_details {op} {p}{nocase})"""
        params = [like, like, like, like, like, like, like, like, like]

        if status and status != "All":
            sql += f" AND status={p}"
            params.append(status)
        if flat_no:
            sql += f" AND flat_no={p}"
            params.append(flat_no)

        sql += " ORDER BY updated_at DESC, created_at DESC"
        cur.execute(sql, tuple(params))
        return [dict(r) for r in cur.fetchall()]


def get_pet_status_counts():
    with db_cursor(commit=False) as (cur, backend):
        cur.execute("SELECT status, COUNT(*) AS n FROM pet_registrations GROUP BY status")
        counts = {status: 0 for status in PET_REGISTRATION_STATUSES}
        for row in cur.fetchall():
            status = row["status"] if backend == "postgres" else row[0]
            count = row["n"] if backend == "postgres" else row[1]
            counts[status] = count
        return counts


def update_pet_registration_status(pet_id, status):
    if status not in PET_REGISTRATION_STATUSES:
        raise ValueError("Invalid pet registration status.")
    with db_cursor() as (cur, backend):
        p = _ph(backend)
        now = "CURRENT_TIMESTAMP" if backend == "postgres" else "datetime('now')"
        cur.execute(
            f"UPDATE pet_registrations SET status={p}, updated_at={now} WHERE id={p}",
            (status, pet_id),
        )


def delete_pet_registration(pet_id):
    with db_cursor() as (cur, backend):
        cur.execute(f"DELETE FROM pet_registrations WHERE id={_ph(backend)}", (pet_id,))


# ---------- clubhouse bookings ----------
def add_clubhouse_booking(booking_date, function_type, owner_flat_no, owner_name,
                          owner_contact, owner_mobile, booked_for_whole_day,
                          notes):
    if function_type not in FUNCTION_TYPES:
        function_type = "Other"
    booked_for_whole_day = "Yes" if str(booked_for_whole_day).strip().lower() == "yes" else "No"

    with db_cursor() as (cur, backend):
        p = _ph(backend)
        now = "CURRENT_TIMESTAMP" if backend == "postgres" else "datetime('now')"
        cur.execute(
            f"""INSERT INTO clubhouse_bookings
                (booking_date, function_type, owner_flat_no, owner_name,
                 owner_contact, owner_mobile, booked_for_whole_day,
                 notes, status, created_at, updated_at)
                VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{now},{now})""",
            (
                booking_date,
                function_type,
                owner_flat_no,
                owner_name,
                owner_contact,
                owner_mobile,
                booked_for_whole_day,
                notes,
                "BOOKED",
            ),
        )


def search_clubhouse_bookings(term="", status="All", owner_flat_no=""):
    like = f"%{term.strip()}%"
    with db_cursor(commit=False) as (cur, backend):
        p, op = _ph(backend), ("ILIKE" if backend == "postgres" else "LIKE")
        nocase = "" if backend == "postgres" else " COLLATE NOCASE"
        sql = f"""SELECT * FROM clubhouse_bookings
                  WHERE (booking_date {op} {p}
                         OR function_type {op} {p}{nocase}
                         OR owner_flat_no {op} {p}
                         OR owner_name {op} {p}{nocase}
                         OR owner_contact {op} {p}{nocase}
                         OR owner_mobile {op} {p}
                         OR booked_for_whole_day {op} {p}{nocase}
                         OR notes {op} {p}{nocase})"""
        params = [like, like, like, like, like, like, like, like]

        if status and status != "All":
            sql += f" AND status={p}"
            params.append(status)
        if owner_flat_no:
            sql += f" AND owner_flat_no={p}"
            params.append(owner_flat_no)

        sql += " ORDER BY booking_date DESC, updated_at DESC"
        cur.execute(sql, tuple(params))
        return [dict(r) for r in cur.fetchall()]


def get_clubhouse_booking_status_counts():
    with db_cursor(commit=False) as (cur, backend):
        cur.execute("SELECT status, COUNT(*) AS n FROM clubhouse_bookings GROUP BY status")
        counts = {status: 0 for status in BOOKING_STATUSES}
        for row in cur.fetchall():
            status = row["status"] if backend == "postgres" else row[0]
            count = row["n"] if backend == "postgres" else row[1]
            counts[status] = count
        return counts


def update_clubhouse_booking_status(booking_id, status):
    if status not in BOOKING_STATUSES:
        raise ValueError("Invalid clubhouse booking status.")
    with db_cursor() as (cur, backend):
        p = _ph(backend)
        now = "CURRENT_TIMESTAMP" if backend == "postgres" else "datetime('now')"
        cur.execute(
            f"UPDATE clubhouse_bookings SET status={p}, updated_at={now} WHERE id={p}",
            (status, booking_id),
        )


def delete_clubhouse_booking(booking_id):
    with db_cursor() as (cur, backend):
        cur.execute(f"DELETE FROM clubhouse_bookings WHERE id={_ph(backend)}", (booking_id,))


def bulk_add_vehicles(df):
    conn = get_conn()
    cur = conn.cursor()

    success = 0
    failed = []

    for idx, row in df.iterrows():
        try:
            vehicle_no = str(row["vehicle_no"]).strip().upper().replace(" ", "")
            flat_no = normalize_flat(str(row["flat_no"]))
            vehicle_type = str(row["vehicle_type"]).strip()
            model = str(row.get("model", "")).strip()
            parking_slot = str(row.get("parking_slot", "")).strip()

            ok, msg = add_vehicle(
                vehicle_no,
                flat_no,
                vehicle_type,
                model,
                parking_slot
            )

            if ok:
                success += 1
            else:
                failed.append(
                    f"Row {idx+1}: {vehicle_no} - {msg}"
                )

        except Exception as e:
            failed.append(
                f"Row {idx+1}: {str(e)}"
            )

    conn.close()
    return success, failed




# ---------- shared sidebar ----------
def sidebar_footer():
   # backend = "Supabase" if _supabase_url() else " (local — data resets on redeploy)"
    with st.sidebar:
        st.markdown("### Society Structure")
        st.markdown(
            f"- Wings: {', '.join(WINGS)}\n"
            f"- Floors: 1 to 16\n"
            f"- Flats per Floor: {FLATS_PER_FLOOR}\n"
            f"- Total Flats: {TOTAL_FLATS}"
        )
        #st.caption(f"Society Management System | v3.1 | DB: {backend}")
        st.caption("Created by Sujeet Yadav | Building the Solutions")
