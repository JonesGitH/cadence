# New Features — Cadence

## Multi-Provider Calendar Support (Google Calendar + Microsoft 365)

Add the ability to connect Google Calendar as an alternative (or addition) to Microsoft 365.

### Areas of Work

**1. Google OAuth** (`google_auth.py` — new file)
Google doesn't support device-code flow like Microsoft does. For a desktop app it needs a loopback redirect: temporarily spin up a local HTTP server on a free port, send the user to `accounts.google.com`, and catch the auth code on redirect back. The `google-auth-oauthlib` library handles most of this.

**2. Google Calendar API** (`google_calendar.py` — new file)
Mirrors what `outlook.py` does today: discover calendars, fetch events in a date range, map color IDs to hex. Google uses `colorId` 1–11 (different palette from Outlook's presets), and events can also inherit a calendar-level color. The returned dict shape must match what `routes/calendar.py` already expects.

**3. Database migration** (`database.py`)
The `calendars` table has a `graph_id` column. Needs a `provider` column (`'microsoft'` / `'google'`) and the column renamed to something generic like `remote_id`. Requires a migration step on startup since SQLite `ALTER TABLE` is limited.

**4. Route dispatch** (`routes/calendar.py`)
Currently calls `get_calendar_items_range()` from `outlook.py` directly. Needs a thin dispatch — check the enabled calendars' provider, call the right backend, merge results. Event editing (save-to-Outlook modal) also needs a provider-aware path.

**5. Settings UI** (`routes/settings.py` + template)
New "Google Calendar" section alongside the Microsoft 365 section — Connect/Disconnect button and calendar refresh. Google requires both a Client ID and Client Secret (Microsoft only needs a Client ID for public apps), so there's an extra credential to store.

### Recommended Approach

Use a simple `if provider == 'google'` dispatch rather than a formal `CalendarProvider` protocol. Keeps the change self-contained and reviewable without adding abstraction overhead for just two providers.
