# Cadence — Claude Instructions

## Project Overview

Cadence is a Windows desktop invoicing app for educational tutors. It reads Outlook/Microsoft 365 calendar events, matches them to students by initials, and generates PDF invoices. It runs as a Flask web app served by Waitress, wrapped in a Windows system-tray icon via pystray. The user accesses it through a browser at `http://127.0.0.1:5000`.

Working directory: `E:\Code\cadence`

## Build & Run

```
# Dev server (no tray icon, opens browser automatically)
python app.py

# Full desktop app with tray icon
python main.py

# Production build — creates dist\Cadence\Cadence.exe + optional Inno Setup installer
build.bat
```

Build pipeline (`build.bat`) runs:
1. `python create_icon.py` — generates `static\icon.ico`
2. `python generate_version_info.py` — writes `file_version_info.txt` from `version.py`
3. `pyinstaller cadence.spec --clean --noconfirm` — one-folder build in `dist\Cadence\`

Version string lives in `version.py` only — `build.bat`, `cadence.iss`, and `file_version_info.txt` all read from it.

## Architecture

Flask app factory pattern — all routes register against a single shared `app` object:

```
main.py           — entry point: Waitress server + pystray tray icon + idle-timeout watcher
app.py            — Flask app object, auth gate, activity tracking, template filter
database.py       — SQLite helpers, schema creation, migrations, all DB queries
helpers.py        — pure Python utilities shared across routes (no Flask imports)
config.py         — reads/writes config.txt (db_path, pdf_folder); lru_cache'd
graph_auth.py     — MSAL device-code flow for Microsoft 365
outlook.py        — Microsoft Graph API calls (calendar fetch, send email)
pdf_generator.py  — ReportLab PDF invoice generation
routes/
  auth.py         — login, change password, lock screen
  dashboard.py    — home page, today's appointments, stats
  calendar.py     — month-view and week-view calendar
  clients.py      — student CRUD (add, edit, archive, restore, delete)
  invoices.py     — invoice creation, detail, PDF open/send, annual summary
  settings.py     — business info, storage paths, Graph auth, calendar config, Excel import
```

## Database

SQLite, default path: `cadence.db` beside the executable (configurable in Settings → Storage).

**Schema is managed in `database.py`:**
- `init_db()` runs `CREATE TABLE IF NOT EXISTS` for all tables on startup.
- `client_migrations` list in `init_db()` handles `ALTER TABLE ADD COLUMN` for new client columns — add new columns there, not in the schema block, so existing databases are updated automatically.
- No migration versioning — columns are added idempotently (`try/except OperationalError`).

**Key tables:**
| Table | Purpose |
|---|---|
| `clients` | Students — includes per-parent contact info, billing target, services |
| `invoices` | Invoice header — number, client, month/year, totals, pdf_path |
| `invoice_lines` | Line items — sessions, late fees, credits |
| `calendars` | Outlook calendar subscriptions (synced from Graph) |
| `settings` | Key/value store for all app settings |
| `password_history` | Hashed password history for reuse prevention |

**Important invariants:**
- `initials` must be unique among active clients (enforced in `add_client()` and `edit_client()` via `UPPER(initials)` check).
- Invoice creation is a single transaction: INSERT invoice + lines, then generate PDF, then `conn.commit()`. On PDF failure, `conn.rollback()` removes the rows — no orphaned invoice records.
- `conn.row_factory = sqlite3.Row` on every connection — rows support both index and column-name access.

## Two Directories When Frozen

When running as a PyInstaller bundle:
- `CADENCE_BUNDLE_DIR` (`sys._MEIPASS`) — read-only resources: `templates/`, `static/`
- `CADENCE_DATA_DIR` (beside the `.exe`) — writable: `cadence.db`, `config.txt`, `cadence.log`, PDF output

When running from source both directories are the same (`E:\Code\cadence`).

`config.py` and `database.py` both read `CADENCE_DATA_DIR` from `os.environ`.

## Settings System

All settings are stored in the `settings` table as key/value strings.

| Key | Description |
|---|---|
| `hourly_rate` | Default per-session rate (float, validated before save) |
| `business_name`, `business_title`, `business_email`, `business_phone`, `business_address`, `business_city`, `business_state`, `business_zip` | Printed on invoices |
| `venmo_handle` | Shown on invoice footer |
| `idle_timeout_minutes` | Auto-close after inactivity (int, 0 = disabled) |
| `graph_client_id` | Azure app registration client ID |
| `graph_timezone` | IANA/Windows timezone for calendar queries |
| `pdf_folder` | Stored in `config.txt`, not `settings` table |

`get_settings_batch(keys)` fetches multiple keys in one query.

## Microsoft 365 / Outlook Integration

- Auth uses MSAL device-code flow — user visits a URL, enters a code.
- Token is stored in the `settings` table (`ms_token_cache` key) as JSON.
- `outlook.py` calls Graph API to fetch calendar events for enabled calendars.
- Calendar events are matched to students by initials using `_match_initials()` in `helpers.py`.
- Dashboard catches `RuntimeError` from `get_today_items()` (auth expired) and shows a reconnect banner. Other exceptions are logged as warnings.
- Email is sent via Graph API `sendMail` endpoint using the resolved billing contact's email.

## Billing / Invoice Logic

**Bill-to resolution** (`_resolve_bill_to(client)` in `routes/invoices.py`):
- `bill_to_parent = '1'` → Parent 1 name + `client.email` + `client.parent_address`
- `bill_to_parent = '2'` → Parent 2 name + `client.parent2_email` + `client.parent2_address`
- `bill_to_parent = 'custom'` → Custom name/address fields

Parent 1's contact fields in the DB are `email`, `phone` (the original columns). Parent 2 adds `parent2_phone` and `parent2_email`. This means the existing `email` column is Parent 1's email — no data migration was needed.

**Invoice number** is sequential, zero-padded to 4 digits (`next_invoice_number()` in `database.py`).

**Rate precedence:** student-level `hourly_rate` overrides the global `hourly_rate` setting.

## Key Helpers (`helpers.py`)

| Function | Purpose |
|---|---|
| `_parse_student_form()` | Reads all student form fields from `request.form`; raises `ValueError` if `hourly_rate` is non-numeric |
| `_parse_rate(raw)` | Returns `float` or `None`; raises `ValueError` on bad input |
| `_enrich_student(row)` | Adds `age`, `services_list`, `services_display` to a DB row dict |
| `_match_initials(subject, initials_map)` | Finds student initials in a calendar event subject |
| `_calculate_age(birthday_str)` | Returns age in years from ISO date string |
| `_parse_services(services_str)` | Parses JSON services list from DB |
| `_parent_bill_name(client)` | Returns "Parent1 & Parent2" or just "Parent1" |

## Auth / Security

- Optional password protection — if no password set, app is open.
- Passwords are bcrypt-hashed via `werkzeug.security`.
- Password expiry: 180 days, with 14-day warning banner. Expired password forces change on next login.
- Password history: reuse prevention, all previous hashes stored.
- Session flag `force_change` redirects all routes to change-password page.
- Auth-exempt endpoints: `unlock`, `change_password`, `static`.

## Calendar Month Normalization

`routes/calendar.py` normalizes arbitrary `?month=` URL values using divmod:
```python
month -= 1
year  += month // 12
month  = month % 12 + 1
```
This correctly handles negative months and multi-month overflows.

## Frontend

- Jinja2 templates in `templates/`; base layout in `templates/base.html`
- CSS in `static/css/style.css` — uses CSS custom properties (`--primary`, `--danger`, `--warning`, etc.)
- JS in `static/js/main.js` — no build step, plain ES5
- Tabs use `data-tab-target` attributes; tab state is persisted in `location.hash` so the correct tab survives form-submit redirects
- Delete confirmation modal is in `base.html` (`#delete-confirm-modal`) and wired globally in `main.js` via `confirmDelete()`
- Invoice filter (history page) is client-side in `main.js`; empty-state message names the active filters

## What NOT to Do

- Do not add a version number to `cadence.iss`, `file_version_info.txt`, or `build.bat` — they read `version.py`.
- Do not `conn.commit()` before PDF generation in `generate_invoice()` — the transaction must be atomic (commit only on success, rollback on PDF failure).
- Do not add new client columns only to the `CREATE TABLE` block — also add them to `client_migrations` so existing databases get the column.
- Do not use hardcoded hex colors in templates — use CSS variables (`var(--danger)`, `var(--warning)`, etc.).
- Do not store `pdf_folder` or `db_path` in the `settings` table — they live in `config.txt` via `config.py`.
- Do not use `requests.packages.urllib3` as a hidden import in the spec — it is a deprecated alias and causes a non-fatal warning; leave it as-is.

## Running Tests

```
pytest tests/
```

Test files: `tests/test_auth.py`, `tests/test_invoices.py`, `tests/test_pdf.py`
Fixtures are in `tests/conftest.py`.
