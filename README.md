# Cadence — Invoice & Scheduling App

> Your consulting rhythm. Generate professional invoices from your Microsoft 365 calendar sessions automatically.

---

## Table of Contents

1. [What It Does](#what-it-does)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Azure App Registration](#azure-app-registration-one-time-setup)
5. [First Time Configuration](#first-time-configuration)
6. [Using Two PCs with OneDrive](#using-two-pcs-with-onedrive)
7. [Adding Students](#adding-students)
8. [Creating an Invoice](#creating-an-invoice)
9. [Managing Invoices](#managing-invoices)
10. [Annual Summary & CSV Export](#annual-summary--csv-export)
11. [Settings Reference](#settings-reference)
12. [Database Backup](#database-backup)
13. [Troubleshooting](#troubleshooting)
14. [File Overview](#file-overview)

---

## What It Does

Cadence is a local desktop app built for Educational Therapists and other solo practitioners. It:

- **Reads your Microsoft 365 calendar** via the Microsoft Graph API — Outlook does not need to be open
- **Finds student sessions** by matching appointment titles against each student's initials
- **Generates professional PDF invoices** with every session listed as a line item at your configured rate
- **Sends invoices by email** directly through your Microsoft 365 account, saved to your Sent Items
- **Tracks payment status** and gives you a full annual income summary for tax reporting

Everything runs entirely on your own PC. No subscription, no cloud service, no data leaves your machine.

---

## Requirements

| Requirement | Details |
|---|---|
| **Operating System** | Windows 10 or Windows 11 |
| **Python** | 3.10 or later — [Download here](https://www.python.org/downloads/) |
| **Microsoft 365 account** | Any personal or organizational account with Outlook calendar access |
| **Azure app registration** | Free, one-time setup — instructions below |

> **Python installation tip:** When the Python installer opens, check **"Add Python to PATH"** before clicking Install. If you missed this, uninstall Python and reinstall with that option checked.

---

## Installation

### Option A — Standalone App (Recommended)

Builds a self-contained `Cadence.exe` with no command window and a system tray icon. Run the build once; after that just double-click the `.exe`.

**Step 1 — Copy the cadence folder to your PC**

Place the `cadence` folder somewhere permanent, for example:
```
C:\cadence\
```
Avoid putting it in a temporary location — the database and PDF files will be stored here.

**Step 2 — Install Python dependencies**

Double-click **`setup.bat`**. A window opens briefly, downloads packages, and closes. This only needs to run once (or again if you reinstall Python).

**Step 3 — Build the executable**

Double-click **`build.bat`**. This takes approximately 60 seconds and requires an internet connection. When finished you will see:
```
dist\Cadence\
    Cadence.exe
    (supporting files)
```

**Step 4 — Launch Cadence**

Open `dist\Cadence\` and double-click **`Cadence.exe`**. On first launch:
- Your browser opens automatically to the Cadence interface
- A blue diamond icon appears in your **Windows system tray** (bottom-right corner of the taskbar)

**From now on**, just double-click `Cadence.exe` to start the app. No command window ever appears.

> **Tip:** Create a shortcut to `Cadence.exe` on your Desktop for quick access. You can also copy the entire `dist\Cadence\` folder to OneDrive or a USB drive — the database and settings travel with it.

**Using the tray icon:**

Right-click the blue diamond in the system tray to:
- **Open Cadence** — opens the browser interface
- **Stop Cadence** — shuts the app down completely

---

### Option B — Developer Mode

Run directly from source without building an `.exe`. Requires Python to be installed.

Double-click **`launch.bat`**:
- Browser opens automatically at `http://127.0.0.1:5000`
- Tray icon appears in the system tray
- No command window is visible

Use this option if you are making changes to the code or prefer not to build.

---

## Azure App Registration (One-Time Setup)

Cadence connects to your Microsoft 365 calendar and email using the **Microsoft Graph API**. This requires a free app registration in the Azure portal. You only do this once.

### Step 1 — Create the registration

1. Open [portal.azure.com](https://portal.azure.com) and sign in with your Microsoft 365 account
2. In the search bar at the top, type **App registrations** and click it
3. Click **+ New registration**
4. Fill in the form:
   - **Name:** `Cadence` (or anything you like)
   - **Supported account types:** Select **"Accounts in any organizational directory and personal Microsoft accounts"**
   - **Redirect URI:** Leave blank
5. Click **Register**

### Step 2 — Enable public client flows

1. In your new app registration, click **Authentication** in the left menu
2. Scroll down to **Advanced settings**
3. Under **Allow public client flows**, toggle to **Yes**
4. Click **Save**

### Step 3 — Add API permissions

1. Click **API permissions** in the left menu
2. Click **+ Add a permission**
3. Click **Microsoft Graph** → **Delegated permissions**
4. Search for and check **`Calendars.ReadWrite`**
5. Click **Add a permission** again → **Microsoft Graph** → **Delegated permissions**
6. Search for and check **`Mail.Send`**
7. Click **Add permissions**

> You do **not** need to click "Grant admin consent" — delegated permissions work without it for personal accounts.

### Step 4 — Copy your Client ID

1. Click **Overview** in the left menu
2. Copy the **Application (client) ID** — it looks like: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

You will paste this into Cadence in the next section.

---

## First Time Configuration

Open Cadence and go to **Settings** in the sidebar. Complete these sections in order.

### 1. Business Information & Rate

| Field | What to enter |
|---|---|
| **Your Name** | Your full name as it should appear on invoices |
| **Title / Credentials** | e.g. `Educational Therapist, M.Ed.` — printed below your name |
| **Email** | Your business email address |
| **Phone** | Your phone number |
| **Street Address** | Printed in the invoice header and payment instructions |
| **City / State / Zip** | Your business location |
| **Per-Session Rate ($)** | Your standard flat rate per session (e.g. `150.00`) |
| **Venmo Handle** | e.g. `@Your-Name` — printed in payment instructions on invoices |
| **Idle Timeout** | How long Cadence waits before auto-closing when inactive (see [Idle Timeout](#idle-timeout)) |

Click **Save Settings** when done.

### 2. Microsoft 365

1. Paste your **Azure App Client ID** (from the registration above) into the field
2. Select your **Timezone** from the dropdown (e.g. *Central (CT)*)
3. Click **Save**
4. Click **Connect Microsoft 365**
   - A browser tab opens with a Microsoft sign-in page
   - A code appears in Cadence — enter it when prompted
   - Sign in with your Microsoft 365 account
   - Cadence detects the sign-in automatically and shows **"Connected"**

> If the connection tab closes before you finish, click **Connect Microsoft 365** again to get a fresh code.

### 3. Calendars

1. Click **Refresh from Outlook** — Cadence scans your Microsoft 365 account and lists all your calendars
2. Toggle **Scan** on for each calendar that contains student appointments
   - You can enable multiple calendars — Cadence checks all enabled ones when searching for sessions
3. Optionally mark one calendar as **Default** — this pre-selects it in certain views
4. Click **Save Calendar Preferences**

### 4. Storage Paths

Configure where Cadence saves files:

| Field | Default | Notes |
|---|---|---|
| **Database File (.db)** | `cadence\cadence.db` | Stores all students, invoices, and settings |
| **Invoice PDF Folder** | `C:\invoice` | PDFs are saved here in subfolders by month (e.g. `April 2026\`) |

> **OneDrive tip:** Point both paths to a shared OneDrive folder so your data stays in sync across two PCs. See [Using Two PCs with OneDrive](#using-two-pcs-with-onedrive) for full instructions.

Click **Save Storage Paths**. If you change the database path, your existing data is automatically copied to the new location. Restart Cadence after saving.

---

## Using Two PCs with OneDrive

If you work from two computers (e.g. home and office), you can share a single Cadence database between them using OneDrive.

### Setup

1. On your primary PC, go to **Settings → Storage Paths**
2. Set the **Database File** path to a folder inside OneDrive, for example:
   ```
   C:\Users\You\OneDrive\Cadence\cadence.db
   ```
3. Set the **Invoice PDF Folder** to another OneDrive folder:
   ```
   C:\Users\You\OneDrive\Invoices
   ```
4. Click **Save Storage Paths** — Cadence copies the database to the new location
5. Repeat steps 1–4 on your second PC using the same OneDrive paths

### Important: Only run Cadence on one PC at a time

Cadence uses a SQLite database, which is not designed for simultaneous access from multiple machines. If both PCs run Cadence at the same time and both try to save data, you may get errors or data may not save correctly.

**Best practice:** Use the **Idle Timeout** setting (Settings → Business Information → Idle Timeout) so Cadence automatically shuts down after a period of inactivity. This ensures the first PC closes before you open the app on the second.

### Idle Timeout

The Idle Timeout setting automatically closes Cadence after a set period of inactivity:

| Option | Best for |
|---|---|
| **Never** | Single PC only |
| **15 minutes** | Frequent PC switching |
| **30 minutes** | Recommended for two-PC setups |
| **1 hour** | Occasional PC switching |
| **2 hours** | Long work sessions |

When Cadence auto-closes, it shuts down cleanly — the same as clicking **Stop Cadence** from the tray icon. The next time you open it on either PC, the latest data from OneDrive will load automatically.

---

## Adding Students

Go to **Students** in the sidebar and click **Add Student**.

### Student Fields

| Field | Description |
|---|---|
| **Full Name** | Used on invoices and for naming saved PDF files |
| **Initials** | **Exactly** as they appear in your Microsoft 365 calendar appointment titles — spacing and punctuation matter (`AJ` vs `A.J.` are different) |
| **Grade / School** | For your records only — not printed on invoices |
| **Parent / Guardian 1 & 2** | Names printed in the "Bill To" block on invoices |
| **Parent Address** | Street, city, state, zip — printed on invoices |
| **Email** | Used when sending invoices via Microsoft 365 — required to enable the Send button |
| **Per-Session Rate ($)** | Leave blank to use the global rate; enter a value to override for this student only |
| **Services** | Check all applicable service areas — for your records, not printed on invoices |
| **Diagnosis** | Clinical notes — not printed on invoices |
| **Service Start / End Date** | For your records |
| **Test Date** | For your records |
| **Intake Complete / ROI Complete** | Administrative checkboxes |

Click **Save Student**.

### Tips

- **Initials are case-sensitive.** Open a calendar appointment and check exactly how the student's initials appear in the title (e.g. `AJ` not `Aj`).
- **Archiving vs. deleting:** When a student is no longer active, use **Archive** rather than Delete. Archived students are hidden from active lists but their invoice history is preserved.
- **Per-student rate:** If a student has a different rate than your default, set it here. It will be used automatically when generating invoices for that student.

---

## Creating an Invoice

### Step 1 — Select the student and period

1. Click **New Invoice** in the sidebar
2. Choose the **Student** from the dropdown
3. Select the **Month** and **Year**
4. Click **Find Sessions in Outlook**

Cadence scans all your enabled Microsoft 365 calendars for appointments whose title contains that student's initials. Results appear within a few seconds.

### Step 2 — Review sessions

Each matching appointment appears as a row with:
- **Date** of the session
- **Time** (start and end)
- **Duration** in hours
- **Rate** (the student's rate, or global rate if no override)
- **Session Total**

**Uncheck any sessions you do not want to bill** — for example, a cancelled session that was rescheduled.

A running **total** updates at the bottom as you check and uncheck rows.

### Step 3 — Add adjustments (optional)

**Late Fee:** Click **Add Late Fee**, enter the dollar amount and a description (e.g. *Late payment fee*). It appears as a separate line item on the invoice.

**Credit:** Click **Add Credit**, enter the amount and description (e.g. *Prepaid session credit*). It is subtracted from the invoice total and shown in green.

### Step 4 — Generate

Click **Generate Invoice & Save PDF**.

Cadence:
1. Assigns the next sequential invoice number
2. Saves the invoice to the database
3. Generates a PDF and saves it to your configured PDF folder under a subfolder named for the month (e.g. `April 2026\Alex Jones.pdf`)
4. Takes you directly to the Invoice Detail page

> **Duplicate warning:** If an invoice already exists for that student and month, Cadence warns you before creating a second one.

---

## Managing Invoices

### Invoice History

Go to **Invoice History** in the sidebar to see all invoices.

**Filters:** Use the dropdowns at the top to filter by student, year, or status (Paid / Unpaid). The filter bar stays visible as you scroll. Click **Clear** to reset all filters.

### Invoice Detail Page

Click **View** on any invoice to open its detail page.

| Button | What It Does |
|---|---|
| **Mark as Paid** | Marks the invoice as paid and records today's date. Click again to toggle back to unpaid. |
| **Send via Email** | Attaches the PDF and sends it to the student's parent email via Microsoft 365. The email is saved to your Sent Items. Disabled if no email is on file for the student. |
| **Save PDF** | Opens the saved PDF in your default PDF viewer. |
| **Open Folder** | Opens the folder in Windows Explorer where the PDF is saved. |
| **Delete** | Removes the invoice record from Cadence. Does **not** delete the PDF file from disk. |

### Invoice Numbers

Invoices are numbered sequentially starting at **5550** (e.g. 5550, 5551, 5552…). The counter never resets, even if you delete invoices.

---

## Annual Summary & CSV Export

Go to **Summary** in the sidebar for a full-year income overview.

Use the **year dropdown** at the top-right to switch between years.

### What you see

**Stat cards:**
- **Total Billed** — sum of all invoice totals for the year
- **Collected** — total from paid invoices (shown in green)
- **Outstanding** — unpaid balance remaining (shown in amber)

**Monthly Breakdown table:**
Shows invoices, hours, billed, collected, and outstanding for each month — useful for spotting slow-pay clients or planning cash flow.

**By Student table:**
The same breakdown per student — useful for understanding which clients make up the bulk of your income.

### Exporting for taxes

Click **Export CSV** to download a spreadsheet-compatible file with all invoice data for the year. Open it in Excel or Google Sheets for tax preparation.

---

## Settings Reference

All settings are accessed via **Settings** in the sidebar.

### Business Information & Rate

Printed on every invoice. Keep this accurate — changes take effect on the next invoice generated.

### Microsoft 365

| Field | Description |
|---|---|
| **Azure App Client ID** | The GUID from your Azure app registration |
| **Timezone** | Used to display calendar event times correctly |
| **Connect / Disconnect** | Authenticates your Microsoft 365 account via a browser sign-in |

Re-authenticate any time by clicking **Connect Microsoft 365** again. Your token is refreshed automatically during normal use.

### Storage Paths

| Field | Description |
|---|---|
| **Database File (.db)** | Full path to `cadence.db`. Changing this copies your data to the new location automatically. Restart required. |
| **Invoice PDF Folder** | Root folder for saved PDFs. Cadence creates month subfolders automatically (e.g. `April 2026\`). |

### Database Backup

Click **Back Up Now** to create a timestamped copy of your database in the same folder:
```
cadence_backup_20260419_143022.db
```
Do this before any major changes (updating the app, moving files, etc.).

### Outlook Calendars

| Control | Description |
|---|---|
| **Refresh from Outlook** | Re-scans your Microsoft 365 account for calendars |
| **Scan toggle** | Enable/disable each calendar for session searches |
| **Default radio** | Pre-selects one calendar in certain views |

---

## Database Backup

Regular backups protect against accidental data loss.

**To back up:**
1. Go to **Settings → Database Backup**
2. Click **Back Up Now**
3. A file named `cadence_backup_YYYYMMDD_HHMMSS.db` is saved beside your database

**To restore from a backup:**
1. Close Cadence (right-click tray icon → Stop Cadence)
2. In File Explorer, rename your current `cadence.db` to `cadence_old.db`
3. Rename the backup file to `cadence.db`
4. Reopen Cadence

**Recommended schedule:** Back up once a week, or immediately after generating a batch of invoices.

---

## Troubleshooting

### "Microsoft 365 is not configured"
You haven't connected to Microsoft 365 yet, or the Azure App Client ID is missing.
- Go to **Settings → Microsoft 365**
- Enter your Azure App Client ID and click **Save**
- Click **Connect Microsoft 365** and complete the sign-in

### "Could not reach Microsoft 365" / sessions not loading
Your Microsoft 365 token may have expired.
- Go to **Settings → Microsoft 365** — check whether the status shows Connected
- If disconnected, click **Connect Microsoft 365** to re-authenticate
- Make sure your PC has an active internet connection

### "No sessions found"
Cadence searched your calendars but found no matching appointments.
- Check that the student's **Initials** in Cadence match **exactly** what appears in your calendar appointment titles (including capitalization and punctuation)
- Confirm the correct calendars have **Scan** toggled on in **Settings → Calendars**
- Verify the appointments fall within the selected month and year — not the week before or after

### "Send via Email" button is greyed out
The student has no email address saved.
- Go to **Students**, find the student, click **Edit**
- Add the parent email address and click **Save Student**

### Browser does not open automatically
- Open your browser manually and go to: `http://127.0.0.1:5000`
- Check that the Cadence tray icon is visible in the Windows system tray (bottom-right of taskbar)
- If the tray icon is gone, reopen `Cadence.exe`

### App won't start
- Double-click **`setup.bat`** again to reinstall Python packages
- Confirm Python was installed with **"Add to PATH"** checked — if not, uninstall and reinstall Python with that option enabled
- Try right-clicking `Cadence.exe` → **Run as administrator**

### Cadence closed on its own
If the Idle Timeout is set (Settings → Business Information → Idle Timeout), Cadence automatically shuts down after the configured period of inactivity. This is normal behavior. Simply reopen `Cadence.exe`.

### Database is locked / save errors
This happens when Cadence is running on two PCs simultaneously against the same OneDrive database.
- Close Cadence on one PC before opening it on the other
- Set an **Idle Timeout** (30 minutes recommended) so Cadence auto-closes when inactive

---

## File Overview

```
cadence/
├── launch.bat          ← Double-click to start (developer mode)
├── build.bat           ← Run once to build the standalone .exe
├── setup.bat           ← Run once during first-time setup
├── main.py             ← Entry point: starts Flask + system tray icon
├── app.py              ← Main application and all page routes
├── database.py         ← Local SQLite database logic
├── config.py           ← Paths and settings loader
├── graph_auth.py       ← Microsoft 365 OAuth authentication
├── outlook.py          ← Calendar and email via Microsoft Graph API
├── pdf_generator.py    ← PDF invoice builder
├── create_icon.py      ← Generates the app icon
├── cadence.spec        ← PyInstaller build spec (used by build.bat)
├── requirements.txt    ← Python package list (used by setup.bat)
├── cadence.db          ← Created automatically on first launch
├── templates/          ← HTML pages
└── static/             ← CSS styles and JavaScript
```

---

*Cadence runs entirely on your local machine. Your data is never sent to any third party.*
