# Hermosa Casa v3.1 (security-fixed)

Drop-in upgrade of v3. **All files changed — replace the entire repo contents.**

## Critical fixes over v3
1. **Login now enforced on every page** (v3 only protected the home page; /Residents etc. were publicly accessible).
2. **No hardcoded passwords** — v3 shipped with `hermosa2026` / `resident2026` fallbacks visible in the public repo. v3.1 fails closed: no secrets configured = nobody logs in.
3. **Supabase mode actually works** — v3 called `executescript()` on a psycopg2 cursor, which crashed on first run.
4. **`requirements.txt` added** (was missing: deploy would fail on `import psycopg2`). Includes `psycopg2-binary` and `openpyxl`.
5. **Postgres connections closed after every operation** (v3 leaked them — would exhaust the Supabase pooler).
6. **Bulk import NaN fix** — empty Excel cells no longer import as the string "nan"; mobile numbers no longer get a trailing ".0".

## How to upgrade your existing deployment

1. Replace only these two files in your repo:
   - `app.py`
   - `db.py`

2. (Optional but recommended) Rename your pages for nicer sidebar navigation if you want:
   - Keep the current filenames or change to `01_👪_Residents.py`, `02_🚗_Vehicles.py`, etc. Streamlit will pick them up automatically.

3. Add to Streamlit Cloud → Settings → Secrets:
   ```toml
   password_edit = "your-committee-edit-password"
   password_read = "your-resident-readonly-password"

   # For persistent data (highly recommended)
   SUPABASE_DB_URL = "postgresql://postgres:xxx@aws-0-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require"
   ```

4. Commit & push → auto redeploy.

## Supabase setup (one-time)
- Create free project at supabase.com
- Copy the **Transaction** mode connection string from Project Settings → Database
- Paste it as `SUPABASE_DB_URL` in secrets
- First visit after deploy will automatically create the three tables and seed emergency contacts

Your existing `society.db` (SQLite) will continue to work locally for testing.

## Why this upgrade matters
- **Data safety**: SQLite on Streamlit Cloud is wiped on every deploy/restart. Supabase keeps your 768-flat data safe.
- **Security**: No more public access to resident names, mobiles, and vehicle details.
- **Zero breaking changes**: All your pages (Residents with tenant handling, Vehicles with owner join, Parking, Reports, Owner Issues, Pet Information, Emergency) work exactly as before.

## Production Best Practices (Recommended)

1. **Secrets Management**
   - Never commit passwords or DB URLs to GitHub.
   - Use strong, unique passwords for `password_edit` and `password_read`.
   - Rotate them periodically via Streamlit Secrets UI.

2. **Data Safety**
   - Supabase is strongly recommended for any real society data (768 flats + vehicles).
   - Regularly export CSVs from the Reports page as additional backup.
   - Supabase free tier has generous limits — you’re very unlikely to hit them.

3. **Sharing the App**
   - Share the public URL only with trusted people.
   - Give `password_edit` only to committee members.
   - Give `password_read` to residents (or keep it internal if you prefer).
   - Consider adding a visible “For Hermosa Casa residents only” notice on the login screen later if needed.

4. **Maintenance**
   - The app auto-initializes tables and seeds emergency contacts.
   - If you ever need to reset, simply delete the Supabase tables or the local `society.db` file.

---

This is now a complete, secure, role-aware society management system ready for real use.

If you want any further enhancements (payment tracking, visitor management, photo uploads via Supabase Storage, automated reports, etc.), just say the word — happy to keep improving it.

**Thank you for trusting me with Hermosa Casa.** Let's make it excellent for your society. 🏠✨
