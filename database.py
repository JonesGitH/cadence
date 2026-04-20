import sqlite3
import os
import calendar
from config import load as _load_config

DB_PATH = _load_config()['db_path']


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS clients (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            initials        TEXT NOT NULL,
            email           TEXT,
            phone           TEXT,
            school          TEXT,
            grade           TEXT,
            birthday        TEXT,
            diagnosis       TEXT,
            services        TEXT,
            services_other  TEXT,
            start_date      TEXT,
            end_date        TEXT,
            test_date       TEXT,
            parent1_name    TEXT,
            parent2_name    TEXT,
            parent_address  TEXT,
            parent_city     TEXT,
            parent_state    TEXT,
            parent_zip      TEXT,
            intake_complete INTEGER DEFAULT 0,
            roi_complete    INTEGER DEFAULT 0,
            active          INTEGER DEFAULT 1,
            hourly_rate     REAL,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS calendars (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            outlook_name TEXT NOT NULL UNIQUE,
            graph_id     TEXT,
            enabled      INTEGER DEFAULT 1,
            is_default   INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT NOT NULL UNIQUE,
            client_id      INTEGER NOT NULL,
            month          INTEGER NOT NULL,
            year           INTEGER NOT NULL,
            total_hours    REAL NOT NULL,
            total_amount   REAL NOT NULL,
            hourly_rate    REAL NOT NULL,
            pdf_path       TEXT,
            paid           INTEGER DEFAULT 0,
            paid_at        TEXT,
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS invoice_lines (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id     INTEGER NOT NULL,
            session_date   TEXT NOT NULL,
            start_time     TEXT NOT NULL,
            end_time       TEXT NOT NULL,
            duration_hours REAL NOT NULL,
            rate           REAL NOT NULL,
            line_total     REAL NOT NULL,
            line_type      TEXT NOT NULL DEFAULT 'session',
            note           TEXT,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        );
    ''')

    # Migrate existing DBs — add columns that may not exist yet
    client_migrations = [
        ('school',          'TEXT'),
        ('grade',           'TEXT'),
        ('birthday',        'TEXT'),
        ('diagnosis',       'TEXT'),
        ('services',        'TEXT'),
        ('services_other',  'TEXT'),
        ('start_date',      'TEXT'),
        ('end_date',        'TEXT'),
        ('test_date',       'TEXT'),
        ('parent1_name',    'TEXT'),
        ('parent2_name',    'TEXT'),
        ('parent_address',  'TEXT'),
        ('parent_city',     'TEXT'),
        ('parent_state',    'TEXT'),
        ('parent_zip',      'TEXT'),
        ('intake_complete', 'INTEGER DEFAULT 0'),
        ('roi_complete',    'INTEGER DEFAULT 0'),
        ('notes',           'TEXT'),
        ('active',          'INTEGER DEFAULT 1'),
        ('hourly_rate',     'REAL'),
    ]
    for col, defn in client_migrations:
        try:
            conn.execute(f'ALTER TABLE clients ADD COLUMN {col} {defn}')
        except Exception:
            pass

    for col, defn in [('graph_id', 'TEXT')]:
        try:
            conn.execute(f'ALTER TABLE calendars ADD COLUMN {col} {defn}')
        except Exception:
            pass

    for col, defn in [('paid', 'INTEGER DEFAULT 0'), ('paid_at', 'TEXT')]:
        try:
            conn.execute(f'ALTER TABLE invoices ADD COLUMN {col} {defn}')
        except Exception:
            pass

    for col, defn in [("line_type", "TEXT NOT NULL DEFAULT 'session'"), ("note", "TEXT")]:
        try:
            conn.execute(f"ALTER TABLE invoice_lines ADD COLUMN {col} {defn}")
        except Exception:
            pass

    defaults = [
        ('hourly_rate',      '0'),
        ('business_name',    'Your Name'),
        ('business_title',   ''),
        ('business_email',   'your@email.com'),
        ('business_phone',   '(555) 555-5555'),
        ('business_address', ''),
        ('business_city',    ''),
        ('business_state',   ''),
        ('business_zip',     ''),
        ('venmo_handle',     '@YourVenmoName'),
        ('invoice_counter',  '0'),
    ]
    for key, value in defaults:
        conn.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()


# ── Settings ──────────────────────────────────────────────────────────────────

def get_setting(key, default=None):
    conn = get_db()
    row = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
    conn.close()
    return row['value'] if row else default


def get_settings_batch(keys):
    conn = get_db()
    rows = conn.execute(
        f"SELECT key, value FROM settings WHERE key IN ({','.join('?'*len(keys))})",
        tuple(keys)
    ).fetchall()
    conn.close()
    return {r['key']: r['value'] for r in rows}


def set_setting(key, value):
    conn = get_db()
    conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))
    conn.commit()
    conn.close()


_INVOICE_START = 5549  # first invoice will be 5550

def next_invoice_number(conn=None):
    own_conn = conn is None
    if own_conn:
        conn = get_db()
    row     = conn.execute("SELECT value FROM settings WHERE key = 'invoice_counter'").fetchone()
    current = int(row['value']) if row else 0
    counter = max(current, _INVOICE_START) + 1
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES ('invoice_counter', ?)",
        (str(counter),)
    )
    if own_conn:
        conn.commit()
        conn.close()
    return str(counter)


# ── Students (clients) ────────────────────────────────────────────────────────

def get_all_clients(active_only=False):
    conn = get_db()
    if active_only:
        rows = conn.execute('SELECT * FROM clients WHERE active = 1 ORDER BY name').fetchall()
    else:
        rows = conn.execute('SELECT * FROM clients ORDER BY active DESC, name').fetchall()
    conn.close()
    return rows


def get_client(client_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
    conn.close()
    return row


def get_clients_initials_map():
    conn = get_db()
    rows = conn.execute('SELECT initials, name FROM clients').fetchall()
    conn.close()
    return {r['initials'].upper(): r['name'] for r in rows}


# ── Calendars ─────────────────────────────────────────────────────────────────

def get_all_calendars():
    conn = get_db()
    rows = conn.execute('SELECT * FROM calendars ORDER BY outlook_name').fetchall()
    conn.close()
    return rows


def get_enabled_calendar_names():
    conn = get_db()
    rows = conn.execute('SELECT outlook_name FROM calendars WHERE enabled = 1').fetchall()
    conn.close()
    return [r['outlook_name'] for r in rows]


def upsert_calendars(calendars):
    """calendars: list of {name, id} dicts from Graph API."""
    conn = get_db()
    for cal in calendars:
        conn.execute(
            'INSERT OR IGNORE INTO calendars (outlook_name, graph_id, enabled, is_default) VALUES (?, ?, 1, 0)',
            (cal['name'], cal.get('id', ''))
        )
        conn.execute(
            'UPDATE calendars SET graph_id = ? WHERE outlook_name = ?',
            (cal.get('id', ''), cal['name'])
        )
    conn.commit()
    conn.close()


# ── Invoices ──────────────────────────────────────────────────────────────────

def get_all_invoices():
    conn = get_db()
    rows = conn.execute('''
        SELECT i.*, c.name AS client_name
        FROM invoices i
        JOIN clients c ON c.id = i.client_id
        ORDER BY i.year DESC, i.month DESC, i.created_at DESC
    ''').fetchall()
    conn.close()
    return rows


def get_invoice(invoice_id):
    conn = get_db()
    inv = conn.execute('''
        SELECT i.*, c.name AS client_name
        FROM invoices i
        JOIN clients c ON c.id = i.client_id
        WHERE i.id = ?
    ''', (invoice_id,)).fetchone()
    lines = conn.execute(
        'SELECT * FROM invoice_lines WHERE invoice_id = ? ORDER BY session_date',
        (invoice_id,)
    ).fetchall()
    conn.close()
    return inv, lines


def month_name(month_int, year_int):
    return f"{calendar.month_name[month_int]} {year_int}"


def toggle_invoice_paid(invoice_id):
    conn = get_db()
    row  = conn.execute('SELECT paid FROM invoices WHERE id=?', (invoice_id,)).fetchone()
    if not row:
        conn.close()
        return None
    new_paid   = 0 if row['paid'] else 1
    new_paid_at = _date_now() if new_paid else None
    conn.execute('UPDATE invoices SET paid=?, paid_at=? WHERE id=?', (new_paid, new_paid_at, invoice_id))
    conn.commit()
    conn.close()
    return new_paid


def _date_now():
    from datetime import datetime
    return datetime.now().strftime('%Y-%m-%d')


def get_invoice_years():
    conn  = get_db()
    rows  = conn.execute('SELECT DISTINCT year FROM invoices ORDER BY year DESC').fetchall()
    conn.close()
    return [r['year'] for r in rows]


def get_annual_summary(year):
    conn = get_db()
    by_month = conn.execute('''
        SELECT month,
               COUNT(*)                  AS invoice_count,
               SUM(total_hours)          AS total_hours,
               SUM(total_amount)         AS total_amount,
               SUM(CASE WHEN paid=1 THEN total_amount ELSE 0 END) AS paid_amount
        FROM invoices WHERE year=?
        GROUP BY month ORDER BY month
    ''', (year,)).fetchall()
    by_student = conn.execute('''
        SELECT c.name,
               COUNT(i.id)               AS invoice_count,
               SUM(i.total_hours)        AS total_hours,
               SUM(i.total_amount)       AS total_amount,
               SUM(CASE WHEN i.paid=1 THEN i.total_amount ELSE 0 END) AS paid_amount
        FROM invoices i JOIN clients c ON c.id = i.client_id
        WHERE i.year=?
        GROUP BY i.client_id ORDER BY total_amount DESC
    ''', (year,)).fetchall()
    totals = conn.execute('''
        SELECT COUNT(*)                  AS invoice_count,
               COALESCE(SUM(total_hours),  0) AS total_hours,
               COALESCE(SUM(total_amount), 0) AS total_amount,
               COALESCE(SUM(CASE WHEN paid=1 THEN total_amount ELSE 0 END), 0) AS paid_amount
        FROM invoices WHERE year=?
    ''', (year,)).fetchone()
    conn.close()
    return {'by_month': by_month, 'by_student': by_student, 'totals': totals}


def backup_database():
    import shutil
    from datetime import datetime
    ts          = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = DB_PATH.rsplit('.', 1)[0] + f'_backup_{ts}.db'
    shutil.copy2(DB_PATH, backup_path)
    return backup_path
