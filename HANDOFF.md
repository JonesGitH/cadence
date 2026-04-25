# Handoff: Cadence — Student/Parent Features + Calendar Colors + Build

**Generated**: 2026-04-24  
**Branch**: master  
**Status**: In Progress — all features working, Cadence.exe built, installer pending (Inno Setup not installed)

**Version:** 1.0.0  
**Stack:** Python 3.12 · Flask · SQLite · Waitress · ReportLab · MSAL · pystray  
**Platform:** Windows 10/11 (64-bit only)

---

## Goal

Cadence is a desktop tutoring-practice management app for a solo practitioner. This session added parent address flexibility, invoice bill-to selection, and calendar event color differentiation. A new `Cadence.exe` was built but the Inno Setup installer was not created (Inno Setup not installed).

---

## Completed

- [x] **Parent 2 separate address** — "Different address for Parent 2" checkbox on student form; reveals `parent2_address/city/state/zip` fields; unchecking clears them
- [x] **Bill-To parent selector** — "Bill Invoices To" radio group (Parent 1 / Parent 2 / Other) always visible in Parent/Guardian card; selecting Other reveals custom name + full address block
- [x] **Invoice PDF uses correct bill-to** — `routes/invoices.py` branches on `bill_to_parent` (`'1'`, `'2'`, `'custom'`); default `'1'` uses combined "Parent1 & Parent2" name with shared address (existing behavior)
- [x] **Calendar event colors** — Student sessions = blue, Other appointments = gray, All-day events = light yellow; legend updated with all three; `isAllDay` added to Graph API `$select`
- [x] **`Cadence.exe` built** — `dist\Cadence\Cadence.exe` (7.3 MB portable folder) built successfully with PyInstaller

---

## Not Yet Done

- [ ] **Create installer** — Inno Setup 6 is not installed; once installed at `D:\Users\Alex\AppData\Local\Programs\Inno Setup 6\`, run:
  ```
  "D:\Users\Alex\AppData\Local\Programs\Inno Setup 6\ISCC.exe" /DAppVersion=1.0.0 "E:\Code\cadence\cadence.iss"
  ```
  Output: `dist\Cadence_Setup_1.0.0.exe`
- [ ] Commit the entire working tree to git (large uncommitted refactor + all new features)
- [ ] Consider splitting `routes/invoices.py` (350+ lines) further if it grows
- [ ] `design-system/cadence` (untracked) — verify if intentional work or scratch directory

---

## Failed Approaches (Don't Repeat These)

- **Monkeypatching `database.get_db` per-test**: Route modules do `from database import get_db` at import time, capturing the reference. Per-test monkeypatching only replaced it in the `database` module namespace. Fixed with the stable `_GetDbProxy` pattern in `tests/conftest.py` — a single callable object installed once, whose underlying connection is swapped between tests.
- **Bill-to radios inside parent2-addr div**: Originally placed the "Bill Invoices To" radio group inside the `#parent2-addr` collapsible block. This meant the free-form "Other" option was only accessible when Parent 2 had a different address. Moved to its own always-visible section.
- **Flask template caching**: When editing templates while the preview server was running, changes didn't appear. Required a full server restart — not just a page reload — to pick up template changes.
- **Running `build.bat` via Bash tool**: `build.bat` ends with `pause` which hangs in a non-interactive shell. Ran the 5 build steps individually instead.
- **ISCC.exe path in HANDOFF.md was stale**: The old HANDOFF said Inno Setup was at `D:\Users\Alex\AppData\Local\Programs\Inno Setup 6\ISCC.exe`. That directory exists but is empty — Inno Setup is not installed.
- **Claude Code's shell cannot access `D:\Users\Alex\AppData\Local\Programs\Inno Setup 6\`**: The shell runs under a different security context than the Alex user account. `Get-ChildItem`, `Test-Path`, `where /r`, and `cmd /c dir` all fail silently or return "not found" for that path, even though the files exist and are accessible from a normal Command Prompt. `Get-PSDrive` confirms D: is mounted, but per-user AppData subdirectories on D: are ACL-restricted to the Alex account. **Workaround**: write a `.bat` file to `E:\Code\cadence\` and have the user run it from their own Command Prompt. The bat file ran successfully: `"D:\Users\Alex\AppData\Local\Programs\Inno Setup 6\ISCC.exe" /DAppVersion=1.0.0 cadence.iss`

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| `bill_to_parent` stores `'1'`, `'2'`, or `'custom'` (not boolean) | Extensible; default `'1'` is backwards-compatible with all existing records |
| All-day events take priority over student-match in chip coloring | All-day events (holidays, no-school) are never tutoring sessions; yellow makes them visually distinct at a glance |
| Bill-to section always visible regardless of Parent 2 checkbox | The "Other" free-form option is useful even when parents share an address (e.g., billing a grandparent or company) |
| Unchecking "Different address for Parent 2" resets bill-to to Parent 1 | Prevents stale `bill_to_parent='2'` with no address data |

---

## Architecture

```
main.py          Entry point. Starts Waitress in a thread, shows tray icon,
                 handles idle-timeout shutdown.
app.py           Flask factory. Wires secret key, auth gate, activity tracking,
                 imports all route modules.
database.py      All SQLite operations. Single connection-per-call pattern.
helpers.py       Shared constants (SERVICES, GRADES) and form-parsing utilities.
                 No Flask imports — safe to use in tests.
version.py       Single source of truth: __version__ = "1.0.0"
config.py        Reads/writes config.txt (db_path, pdf_folder).
graph_auth.py    MSAL device-code OAuth flow. Token cached in cadence_token.bin.
outlook.py       Microsoft Graph API — calendar discovery, event fetching,
                 email sending with PDF attachment.
pdf_generator.py ReportLab invoice builder.
generate_version_info.py  Writes file_version_info.txt from version.py (used by build).

routes/
  auth.py        /unlock, /change-password
  dashboard.py   Today's sessions view
  calendar.py    Month/day calendar view, event annotation
  clients.py     Student list, add, edit, archive, restore, delete
  invoices.py    Invoice creation, PDF save, email, payment toggle, CSV export
  settings.py    All settings tabs, Graph auth endpoints, storage, backup

tests/
  conftest.py    Pytest fixtures — _GetDbProxy pattern
  test_auth.py   Auth gate, unlock, open-redirect blocking, password expiry
  test_invoices.py  Invoice total calc, duplicate detection, force override
  test_pdf.py    PDF build smoke test
```

---

## Database

SQLite at `cadence.db`. New columns added this session (all auto-migrated via `init_db()`):

| Column | Table | Purpose |
|--------|-------|---------|
| `parent2_address` | `clients` | Parent 2 street address (when different from Parent 1) |
| `parent2_city` | `clients` | |
| `parent2_state` | `clients` | |
| `parent2_zip` | `clients` | |
| `bill_to_parent` | `clients` | `'1'` (default), `'2'`, or `'custom'` |
| `bill_to_custom_name` | `clients` | Free-form bill-to name |
| `bill_to_custom_addr` | `clients` | Free-form bill-to street |
| `bill_to_custom_city` | `clients` | |
| `bill_to_custom_state` | `clients` | |
| `bill_to_custom_zip` | `clients` | |

Pre-existing address columns: `parent_address`, `parent_city`, `parent_state`, `parent_zip` = Parent 1's address (shared address when Parent 2 checkbox is unchecked).

---

## Key Interfaces

**Invoice bill-to logic (`routes/invoices.py`):**
```python
_bill_to = client['bill_to_parent'] or '1'
if _bill_to == 'custom':
    parent = { 'name': client['bill_to_custom_name'], 'address': ..., ... }
elif _bill_to == '2' and client['parent2_name']:
    parent = { 'name': client['parent2_name'], 'address': client['parent2_address'], ... }
else:  # '1' default — combined name, shared address
    parent = { 'name': _parent_bill_name(dict(client)), 'address': client['parent_address'], ... }
```

**`_parent_bill_name()` (`helpers.py:75`):**
```python
def _parent_bill_name(client):
    p1 = (client.get('parent1_name') or '').strip()
    p2 = (client.get('parent2_name') or '').strip()
    if p1 and p2:
        return f'{p1} & {p2}'
    return p1 or p2 or client['name']
```
When both parents share an address, bill-to name is automatically "Jane & John Jones".

**Calendar event shape (`outlook.py`):**
```python
{
    'entry_id':   str,
    'date':       'YYYY-MM-DD',
    'day':        int,
    'start_time': '4:10 PM',
    'end_time':   '5:10 PM',
    'start_24':   'HH:MM',
    'end_24':     'HH:MM',
    'subject':    str,
    'calendar':   str,   # calendar display name
    'is_all_day': bool,  # new — from Graph API isAllDay field
    'student':    str | None,  # matched student name (set in calendar route)
}
```

**Calendar chip class priority (`templates/calendar.html`):**
```jinja2
class="cal-chip {% if item.is_all_day %}cal-chip-allday{% elif item.student %}cal-chip-matched{% endif %}"
```
All-day → yellow; student session → blue; other → gray.

---

## Files to Know

| File | Why It Matters |
|------|----------------|
| `database.py` | Schema + migrations. All new columns go here in both `CREATE TABLE` and `client_migrations` list |
| `helpers.py` | `_parse_student_form()` must include every field saved to `clients` table |
| `routes/clients.py` | INSERT/UPDATE SQL must stay in sync with `_parse_student_form()` |
| `routes/invoices.py` | Bill-to logic at lines ~194–210; touches `parent` dict passed to `build_pdf()` |
| `templates/student_form.html` | Parent/Guardian card + bill-to section + JS toggles at bottom |
| `static/css/style.css` | Calendar chip colors: `.cal-chip` (gray), `.cal-chip-matched` (blue), `.cal-chip-allday` (yellow) |
| `outlook.py` | `_fetch_events()` — `$select` must include `isAllDay`; `get_all_calendar_items()` transform must pass `is_all_day` |
| `cadence.spec` | PyInstaller spec — add new route modules to `hiddenimports` if new route files are created |
| `version.py` | Only place to bump version — build.bat, cadence.iss, file_version_info.txt all read from it |

---

## Build Pipeline

**Prerequisites:** Python 3.12, PyInstaller (installed), Inno Setup 6 (installed at `D:\Users\Alex\AppData\Local\Programs\Inno Setup 6\`)

Run steps individually (don't use `build.bat` in non-interactive shells — it ends with `pause`):

```bash
cd E:\Code\cadence
pip install --quiet --upgrade pyinstaller pystray Pillow openpyxl flask reportlab msal requests waitress werkzeug
python create_icon.py
python generate_version_info.py
pyinstaller cadence.spec --clean --noconfirm
```

**Installer step — Claude Code's shell cannot run ISCC.exe directly** (see Failed Approaches). Write this bat file and have the user run it from their own Command Prompt:

```bat
"D:\Users\Alex\AppData\Local\Programs\Inno Setup 6\ISCC.exe" /DAppVersion=1.0.0 "E:\Code\cadence\cadence.iss"
```

Or write `build_installer.bat` to `E:\Code\cadence\` and tell the user to run it. Output: `dist\Cadence_Setup_1.0.0.exe`

To bump the version: edit `version.py` only — everything else reads from it.

---

## Current State

**Working**: All features functional. Parent 2 address + bill-to selector + free-form bill-to fully wired through DB → form → invoice PDF. Calendar event colors distinguish student/other/all-day. `dist\Cadence\Cadence.exe` built and ready.

**Broken**: Nothing known.

**Uncommitted Changes**: Entire working tree is uncommitted. Large set includes the original routes/ refactor plus all features from this session. Key untracked files: `routes/`, `helpers.py`, `version.py`, `tests/`, `generate_version_info.py`, `templates/change_password.html`, `templates/unlock.html`.

---

## Resume Instructions

1. Run `python main.py` — browser opens at `http://127.0.0.1:5000`
2. Run `pytest tests/ -v` to verify all tests pass
3. To create the installer: install Inno Setup 6, then run the command in **Not Yet Done** above
4. To commit: `git add -A` then review with `git diff --cached --stat` before committing

---

## Warnings

- The `routes/` directory is imported by `app.py` at the bottom via explicit `import routes.*` statements — if you add a new route file, register it there.
- `routes/__init__.py` is empty; side-effects happen because `app.py` imports each module by name.
- Do not import `app` inside route modules at the top level before the Flask `app` object exists — all route files already do `from app import app` correctly.
- The `_NoCloseConn` wrapper in `tests/conftest.py` makes `close()` a no-op. If tests leak DB state, check that `really_close()` is called in teardown.
- Schema migrations are inline `ALTER TABLE ADD COLUMN` in `init_db()` wrapped in try/except — safe to run on existing DBs on every startup.
- `6.0` / `=6.0` files in repo root are untracked pip artifacts — safe to delete.
- `design-system/cadence` directory is untracked — verify intent before committing.

---

## Known Issues / Watch Points

| Area | Note |
|------|------|
| Invoice initials matching | Uses `re.search` with word-boundary on calendar event subject. If a student's initials appear inside a word in the event title, it may false-match. See `helpers._match_initials()`. |
| Graph token expiry | If `cadence_token.bin` is stale, refresh may silently fail. User needs to disconnect and reconnect in Settings → MS365. |
| All-day events in calendar | `isAllDay` field newly added to Graph `$select`. Existing event objects returned before this change won't have `is_all_day` — only affects server-side event cache if any; a page reload always fetches fresh. |
| PDF folder | If `pdf_folder` in `config.txt` is blank, PDFs are saved beside the exe. Defaults to Documents folder on fresh install. |
