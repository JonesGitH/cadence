# Cadence — Invoice & Scheduling App

> **Your consulting rhythm.** Generate professional invoices from your Microsoft 365 calendar sessions automatically.

---

## Table of Contents

1. [What It Does](#what-it-does)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Azure App Registration](#azure-app-registration-one-time-setup)
5. [First Time Configuration](#first-time-configuration)
6. [Importing Students from Excel](#importing-students-from-excel)
7. [Adding Students Manually](#adding-students-manually)
8. [Creating an Invoice](#creating-an-invoice)
9. [Managing Invoices](#managing-invoices)
10. [Annual Summary & CSV Export](#annual-summary--csv-export)
11. [Using Two PCs with OneDrive](#using-two-pcs-with-onedrive)
12. [Settings Reference](#settings-reference)
13. [Database Backup](#database-backup)
14. [Troubleshooting](#troubleshooting)
15. [File Overview](#file-overview)

---

## What It Does

Cadence is a local desktop app built for Educational Therapists and other solo practitioners. It:

- **Reads your Microsoft 365 calendar** via the Microsoft Graph API — Outlook does not need to be open
- **Finds student sessions** by matching appointment titles against each student's initials
- **Displays a Monday–Friday calendar** in both week and month views — weekends are hidden by default
- **Generates professional PDF invoices** with every session listed as a line item at your configured rate
- **Sends invoices by email** directly through your Microsoft 365 account to the correct billing parent, saved to your Sent Items
- **Tracks payment status** and gives you a full annual income summary for tax reporting
- **Bulk-imports students** from a pre-formatted Excel spreadsheet

Everything runs entirely on your own PC. No subscription, no cloud service, no data leaves your machine.

---

## Requirements

| Requirement | Details |
|---|---|
| **Operating System** | Windows 10 or Windows 11 (64-bit) |
| **Microsoft 365 account** | Any personal or organizational account with Outlook calendar access |
| **Azure app registration** | Free, one-time setup — instructions below |

> **Developer / source mode only:** Python 3.10 or later is required to run from source. The installer includes everything — Python is **not** needed when using the installer.

---

## Installation

### Option A — One-Click Installer (Recommended)

The installer requires no Python, no command prompt, and no technical setup.

**Step 1 — Download the installer**

Get `Cadence_Setup_1.0.0.exe` from the releases page (or from whoever provided your copy).

**Step 2 — Run the installer**

Double-click `Cadence_Setup_1.0.0.exe`. The installer will:
- Ask where to install (default: `%LOCALAPPDATA%\Cadence` — no admin rights needed)
- Offer an optional Desktop shortcut
- Offer an optional "Launch Cadence when Windows starts" shortcut
- Complete in under 30 seconds

**Step 3 — Launch Cadence**

After installation, click **Launch Cadence now** on the final screen, or use the Start Menu shortcut.

On first launch:
- Your default browser opens automatically to the Cadence interface
- A **blue diamond icon** appears in the Windows system tray (bottom-right corner of your taskbar)

**Using the tray icon:**

Right-click the blue diamond at any time to:
- **Open Cadence** — re-opens the browser interface
- **Stop Cadence** — shuts the app down completely

> **From now on:** click the Start Menu shortcut (or Desktop shortcut if you created one) to start Cadence. No command window ever appears.

---

### Option B — Portable Build (Advanced)

Builds a self-contained `dist\Cadence\Cadence.exe` folder you can put anywhere — including OneDrive or a USB drive.

**Requirements:** Python 3.10+, Git (optional)

1. Copy the `cadence` source folder to your PC
2. Double-click **`setup.bat`** — installs Python dependencies (runs once)
3. Double-click **`build.bat`** — builds the `.exe` (~60–120 sec) and, if [Inno Setup 6](https://jrsoftware.org/isdl.php) is installed, also produces the full installer

Output:
```
dist\Cadence\Cadence.exe          ← portable, run directly
dist\Cadence_Setup_1.0.0.exe      ← installer (if Inno Setup is present)
```

---

### Option C — Developer Mode

Run directly from source without building anything. Requires Python 3.10+.

1. Run `setup.bat` to install packages
2. Double-click **`launch.bat`**

Browser opens at `http://127.0.0.1:5000`. Use this if you're making code changes.

---

## Azure App Registration (One-Time Setup)

Cadence connects to your Microsoft 365 calendar and email using the **Microsoft Graph API**. This requires a free app registration in the Azure portal. You only do this once.

### Step 1 — Create the registration

1. Open [portal.azure.com](https://portal.azure.com) and sign in with your Microsoft 365 account
2. Search for **App registrations** and click it
3. Click **+ New registration**
4. Fill in the form:
   - **Name:** `Cadence` (or any name you like)
   - **Supported account types:** Select **"Accounts in any organizational directory and personal Microsoft accounts"**
   - **Redirect URI:** Leave blank
5. Click **Register**

### Step 2 — Enable public client flows

1. Click **Authentication** in the left menu
2. Scroll to **Advanced settings**
3. Toggle **Allow public client flows** to **Yes**
4. Click **Save**

### Step 3 — Add API permissions

1. Click **API permissions** → **+ Add a permission** → **Microsoft Graph** → **Delegated permissions**
2. Search for and add **`Calendars.ReadWrite`**
3. Repeat and add **`Mail.Send`**
4. Click **Add permissions**

> You do **not** need "Grant admin consent" for personal accounts.

### Step 4 — Copy your Client ID

1. Click **Overview**
2. Copy the **Application (client) ID** (looks like `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

You'll paste this into Cadence → Settings → Microsoft 365.

---

## First Time Configuration

Open Cadence and click **Settings** in the sidebar. Work through the tabs in order.

### Business Tab

| Field | What to enter |
|---|---|
| **Your Name** | Your full name as it appears on invoices |
| **Title / Credentials** | e.g. `Educational Therapist, M.Ed.` — printed below your name |
| **Email** | Your business email |
| **Phone** | Your business phone |
| **Street Address / City / State / Zip** | Printed in the invoice header |
| **Per-Session Rate ($)** | Your standard flat rate per session (e.g. `150.00`) |
| **Venmo Handle** | e.g. `@Your-Name` — printed in payment instructions |
| **Idle Timeout** | Auto-close Cadence after inactivity (recommended: 30 min for two-PC setups) |

Click **Save Settings**.

### Microsoft 365 Tab

1. Paste your **Azure App Client ID**
2. Select your **Timezone**
3. Click **Save**
4. Click **Connect Microsoft 365**
   - A browser tab opens; a code appears in Cadence — enter it when prompted
   - Sign in with your Microsoft 365 account
   - Cadence detects the sign-in and shows **Connected**

### Calendars Tab

1. Click **Refresh from Outlook** — Cadence lists all your calendars
2. Toggle **Scan** on for calendars that contain student appointments
3. Optionally mark one as **Default**
4. Click **Save Calendar Preferences**

### Storage Tab

| Field | Notes |
|---|---|
| **Database File (.db)** | Where `cadence.db` is stored. Changing this copies your data automatically. Restart required. |
| **Invoice PDF Folder** | Where PDFs are saved. Cadence creates month subfolders (e.g. `April 2026\`) automatically. |

> **OneDrive tip:** Point both to a shared OneDrive folder to sync across two PCs. See [Using Two PCs with OneDrive](#using-two-pcs-with-onedrive).

### Backup Tab

Click **Back Up Now** to save a timestamped copy of your database. Do this before any major changes.

---

## Importing Students from Excel

If you have many students to add, the Excel import is the fastest way.

### Step 1 — Download the template

Go to **Settings → Import tab** and click **cadence_students_template.xlsx**.

Open the file in Excel. You'll see:
- **Row 1** — column headers (blue = required, dark = optional)
- **Row 2** — hints for each field
- **Row 3** — a sample student you can delete
- **Services Reference sheet** — lists all valid service key values

### Step 2 — Fill in your students

Start entering data from **row 3** (or row 4 if you keep the sample). Only **Name** and **Initials** are required.

**Important fields:**

| Column | Notes |
|---|---|
| **Name** | Full student name — must be unique |
| **Initials** | 2–3 letters matching exactly what appears in your calendar appointment titles |
| **Grade** | Use the dropdown: K, 1st–12th, College, Other |
| **Birthday** | Format: `YYYY-MM-DD` (e.g. `2015-03-22`) |
| **Services** | Comma-separated keys from the Services Reference sheet (e.g. `reading,spelling`) |
| **Phone / Email** | Parent 1 contact info (`phone`, `email` columns) |
| **Phone (P2) / Email (P2)** | Parent 2 contact info (`parent2_phone`, `parent2_email` columns) |
| **Intake Complete / ROI Complete** | Type `YES` or `NO` (use the dropdown) |
| **Per-Session Rate** | Leave blank to use your default rate from Settings |

### Step 3 — Upload the file

1. Back in **Settings → Import**, click **Choose File** and select your completed `.xlsx`
2. Click **Import Students**
3. A summary message confirms how many students were added, skipped (already exist), or had errors

---

## Adding Students Manually

Go to **Students** in the sidebar and click **+ Add Student**.

### Key Fields

| Field | Description |
|---|---|
| **Full Name** | Used on invoices and PDF filenames |
| **Initials** | Must match exactly what appears in your calendar appointment titles — case-sensitive |
| **Parent 1 Name / Parent 2 Name** | Displayed side-by-side at the top of the Parent / Guardian section |
| **Phone Number (Parent 1 & 2)** | Contact phone for each parent — stored separately |
| **Email Address (Parent 1 & 2)** | The billing parent's email is used for **Send via Email**. Parent 1 email is used by default unless Bill Invoices To is set to Parent 2. |
| **Different address for Parent 2** | Check this box (under Parent 2 Email) to expand a separate address block for Parent 2 |
| **Parent Address / City / State / Zip** | Parent 1 billing address — printed in the "Bill To" block on invoices |
| **Bill Invoices To** | Choose Parent 1, Parent 2, or Other. Controls whose name, address, and email appear on the invoice and email. |
| **Per-Session Rate ($)** | Leave blank to use the global rate from Settings |
| **Services** | Check all applicable areas — internal record only |

Click **Save Student**.

### Tips

- **Initials are case-sensitive.** Open a real calendar appointment to copy the initials exactly.
- **Archive, don't delete** inactive students — their invoice history is preserved. Students with invoices cannot be deleted.
- **Per-student rate** overrides the global rate only for that student.

---

## Creating an Invoice

### Step 1 — Select student and period

1. Click **New Invoice** in the sidebar
2. Choose the **Student**, **Month**, and **Year**
3. Click **Find Sessions in Outlook**

Cadence scans all enabled calendars for appointments whose title contains the student's initials.

### Step 2 — Review sessions

Each matching appointment shows date, time, duration, rate, and total. **Uncheck** any sessions you don't want to bill (e.g. a cancelled session).

### Step 3 — Adjustments (optional)

- **Add Late Fee** — adds a dollar amount as a separate line item
- **Add Credit** — subtracts an amount (shown in green on the invoice)

### Step 4 — Generate

Click **Generate Invoice & Save PDF**. Cadence:
1. Assigns the next sequential invoice number
2. Saves the invoice record to the database
3. Generates a PDF in your configured folder under a month subfolder (e.g. `April 2026\Alex Jones.pdf`)
4. Opens the Invoice Detail page

> **Duplicate warning:** If an invoice already exists for that student and month, Cadence asks before creating a second one.

---

## Managing Invoices

### Invoice History

Click **Invoice History** in the sidebar.

- **Filter** by student, year, or status using the dropdowns
- **Sort** any column by clicking the column header (↑/↓ arrows indicate sort direction)
- **Totals row** at the bottom shows aggregate hours and amount for visible invoices
- **⋯ menu** on each row — click to View, Open PDF, or Open Folder

### Invoice Detail Page

| Action | Description |
|---|---|
| **Mark as Paid / ✓ Paid** | Toggles paid status. Shows a confirmation toast. |
| **Send via Email** | Sends the PDF via Microsoft 365 to the billing parent's email (based on the **Bill Invoices To** setting on the student). Shows a success or error toast. |
| **Save PDF** | Opens the PDF in your default viewer. |
| **Open Folder** | Opens the folder in Windows Explorer. |
| **Delete** | Removes the invoice record. Does **not** delete the PDF from disk. |

### Invoice Numbers

Invoices are numbered sequentially starting at **5550** (e.g. 5550, 5551, 5552…). The counter never resets.

---

## Annual Summary & CSV Export

Click **Summary** in the sidebar.

**Stat cards:**
- **Total Billed** — all invoice totals for the year
- **Collected** — paid invoices (progress bar shows % of billed collected)
- **Outstanding** — unpaid balance

**Monthly Breakdown** and **By Student** tables show hours, billed, collected, and outstanding.

Use the **year dropdown** to switch years. Click **Export CSV** to download all invoice data for tax preparation.

---

## Using Two PCs with OneDrive

Share one database between a home PC and an office PC using OneDrive.

### Setup

1. **Settings → Storage tab** on PC 1 — set both paths to a OneDrive folder:
   ```
   Database:   C:\Users\You\OneDrive\Cadence\cadence.db
   PDF Folder: C:\Users\You\OneDrive\Invoices
   ```
2. Click **Save Storage Paths** — Cadence copies the database automatically
3. Repeat on PC 2 using the same paths

### Rules

- **Never run Cadence on both PCs at the same time** — SQLite isn't designed for concurrent multi-machine access
- Set **Idle Timeout** to 30 minutes so Cadence auto-closes when you walk away from one PC

| Idle Timeout | Best for |
|---|---|
| Never | Single PC only |
| 15 min | Frequent switching |
| 30 min | Recommended for two-PC |
| 1 hour | Occasional switching |
| 2 hours | Long sessions |

---

## Settings Reference

All settings live under **Settings** in the sidebar, organized into tabs.

| Tab | What's here |
|---|---|
| **Business** | Name, title, contact info, rate, Venmo, idle timeout |
| **Storage** | Database file path and PDF folder path |
| **Microsoft 365** | Azure Client ID, timezone, connect/disconnect |
| **Calendars** | Enable/disable calendars, set default |
| **Backup** | One-click database backup |
| **Import** | Download Excel template, upload student file |

---

## Database Backup

**To back up:**
1. **Settings → Backup tab** → click **Back Up Now**
2. A file named `cadence_backup_YYYYMMDD_HHMMSS.db` is saved next to your database

**To restore from backup:**
1. Right-click tray icon → **Stop Cadence**
2. In File Explorer, rename `cadence.db` → `cadence_old.db`
3. Rename the backup file → `cadence.db`
4. Reopen Cadence

**Recommended:** Back up weekly, or immediately after a batch of invoices.

---

## Troubleshooting

### "Microsoft 365 is not configured"
Go to **Settings → Microsoft 365 tab** → enter your Azure App Client ID → click Save → click **Connect Microsoft 365**.

### "Could not reach Microsoft 365" / sessions not loading
Your token may have expired. Go to **Settings → Microsoft 365** — if it shows Disconnected, click **Connect Microsoft 365** to re-authenticate.

### "No sessions found"
- Check the student's **Initials** match exactly what's in the calendar appointment title (case-sensitive, e.g. `AJ` ≠ `A.J.`)
- Confirm the correct calendars have **Scan** toggled on in **Settings → Calendars**
- Make sure the appointments fall within the selected month and year

### "Send via Email" is greyed out
The billing parent has no email address on file. Go to **Students → Edit** and add an email for whichever parent is selected under **Bill Invoices To** (Parent 1 Email, Parent 2 Email, or the custom contact's email).

### Cannot delete a student
Students with existing invoices are protected from deletion to preserve billing history. Use **Archive** instead — archived students are hidden from active lists but their invoices remain intact.

### Browser doesn't open automatically
Open your browser and go to `http://127.0.0.1:5000`. Check the tray icon is visible.

### App closes on its own
Normal behaviour when the Idle Timeout fires. Just reopen Cadence from the Start Menu or tray icon.

### Database locked / save errors
Cadence is running on two PCs simultaneously. Close it on one PC first. Enable Idle Timeout (30 min).

### Installer won't run
Try right-clicking `Cadence_Setup_1.0.0.exe` → **Run as administrator**. Alternatively use the portable build: copy `dist\Cadence\Cadence.exe` directly.

---

## File Overview

```
cadence/
├── Cadence_Setup_1.0.0.exe  ← One-click installer (produced by build.bat)
├── build.bat                ← Builds the .exe and installer
├── setup.bat                ← First-time dev setup (installs Python packages)
├── launch.bat               ← Developer mode (run from source)
├── cadence.spec             ← PyInstaller build configuration
├── cadence.iss              ← Inno Setup installer script
├── file_version_info.txt    ← Windows .exe version metadata
├── main.py                  ← Entry point: Flask + system tray
├── app.py                   ← All page routes and business logic
├── database.py              ← SQLite database layer
├── config.py                ← Paths and settings loader
├── graph_auth.py            ← Microsoft 365 OAuth (MSAL device flow)
├── outlook.py               ← Calendar and email via Microsoft Graph API
├── pdf_generator.py         ← ReportLab PDF invoice builder
├── create_icon.py           ← Generates static/icon.ico
├── requirements.txt         ← Python package list
├── cadence.db               ← Created automatically on first launch
├── templates/               ← Jinja2 HTML pages
└── static/                  ← CSS, JavaScript, icons
```

---

*Cadence runs entirely on your local machine. Your data is never sent to any third party.*
