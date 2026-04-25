import sqlite3
import os
import json
import calendar
from datetime import datetime, timedelta
from config import load as _load_config
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = _load_config()['db_path']


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _clear_wal(db_path):
    for ext in ('-wal', '-shm', '-journal'):
        try:
            os.remove(db_path + ext)
        except OSError:
            pass


def init_db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    try:
        conn = get_db()
    except sqlite3.OperationalError:
        # Stale WAL/journal files from a previous session can block SQLite
        # from opening the database (common after uninstall-keep-files +
        # reinstall). Clear them and retry once.
        _clear_wal(DB_PATH)
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
            parent2_address TEXT,
            parent2_city    TEXT,
            parent2_state   TEXT,
            parent2_zip     TEXT,
            bill_to_parent       TEXT DEFAULT '1',
            bill_to_custom_name  TEXT,
            bill_to_custom_addr  TEXT,
            bill_to_custom_city  TEXT,
            bill_to_custom_state TEXT,
            bill_to_custom_zip   TEXT,
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

        CREATE INDEX IF NOT EXISTS idx_invoices_client_id     ON invoices(client_id);
        CREATE INDEX IF NOT EXISTS idx_invoices_year_month    ON invoices(year, month);
        CREATE INDEX IF NOT EXISTS idx_invoices_paid          ON invoices(paid);
        CREATE INDEX IF NOT EXISTS idx_invoice_lines_invoice  ON invoice_lines(invoice_id);
        CREATE INDEX IF NOT EXISTS idx_clients_active         ON clients(active);
        CREATE INDEX IF NOT EXISTS idx_calendars_enabled      ON calendars(enabled);
    ''')

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
        ('parent2_address', 'TEXT'),
        ('parent2_city',    'TEXT'),
        ('parent2_state',   'TEXT'),
        ('parent2_zip',     'TEXT'),
        ('bill_to_parent',       "TEXT DEFAULT '1'"),
        ('bill_to_custom_name',  'TEXT'),
        ('bill_to_custom_addr',  'TEXT'),
        ('bill_to_custom_city',  'TEXT'),
        ('bill_to_custom_state', 'TEXT'),
        ('bill_to_custom_zip',   'TEXT'),
        ('intake_complete', 'INTEGER DEFAULT 0'),
        ('roi_complete',    'INTEGER DEFAULT 0'),
        ('notes',           'TEXT'),
        ('active',          'INTEGER DEFAULT 1'),
        ('hourly_rate',     'REAL'),
    ]
    import logging as _logging
    _mig_log = _logging.getLogger(__name__)

    def _add_columns(table, columns):
        for col, defn in columns:
            try:
                conn.execute(f'ALTER TABLE {table} ADD COLUMN {col} {defn}')
            except sqlite3.OperationalError as e:
                if 'already exists' not in str(e):
                    _mig_log.warning('Migration failed adding %s.%s: %s', table, col, e)

    _add_columns('clients', client_migrations)
    _add_columns('calendars', [('graph_id', 'TEXT')])
    _add_columns('invoices', [('paid', 'INTEGER DEFAULT 0'), ('paid_at', 'TEXT')])
    _add_columns('invoice_lines', [("line_type", "TEXT NOT NULL DEFAULT 'session'"), ("note", "TEXT")])

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
    if not keys:
        return {}
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


# ── Flask secret key (persisted so sessions survive app restarts) ─────────────

def get_or_create_secret_key() -> str:
    key = get_setting('flask_secret_key')
    if not key:
        import secrets
        key = secrets.token_hex(32)
        set_setting('flask_secret_key', key)
    return key


# ── Password security ─────────────────────────────────────────────────────────

def password_is_set() -> bool:
    return bool(get_setting('security_password_hash'))


def verify_password(password: str) -> bool:
    h = get_setting('security_password_hash')
    if not h:
        return True  # no password configured
    return check_password_hash(h, password)


def password_in_history(password: str) -> bool:
    """Return True if *password* matches the current or any historical hash."""
    current = get_setting('security_password_hash')
    if current and check_password_hash(current, password):
        return True
    try:
        history = json.loads(get_setting('security_password_history') or '[]')
    except (TypeError, ValueError):
        history = []
    return any(check_password_hash(h, password) for h in history)


def set_new_password(new_password: str) -> None:
    """Hash *new_password*, archive the current hash, record changed timestamp."""
    current = get_setting('security_password_hash')
    if current:
        try:
            history = json.loads(get_setting('security_password_history') or '[]')
        except (TypeError, ValueError):
            history = []
        history.append(current)
        set_setting('security_password_history', json.dumps(history))
    set_setting('security_password_hash',       generate_password_hash(new_password))
    set_setting('security_password_changed_at', datetime.now().isoformat())


def remove_password() -> None:
    """Disable password protection (archives current hash into history)."""
    current = get_setting('security_password_hash')
    if current:
        try:
            history = json.loads(get_setting('security_password_history') or '[]')
        except (TypeError, ValueError):
            history = []
        history.append(current)
        set_setting('security_password_history', json.dumps(history))
    set_setting('security_password_hash',       '')
    set_setting('security_password_changed_at', '')


def password_expires_in_days() -> int | None:
    """Days until password expires (negative = already overdue). None if no password."""
    changed_str = get_setting('security_password_changed_at')
    if not changed_str:
        return None
    try:
        changed = datetime.fromisoformat(changed_str)
        # Normalise to naive UTC so subtraction with datetime.now() always works
        if changed.tzinfo is not None:
            changed = changed.replace(tzinfo=None)
        return (changed + timedelta(days=180) - datetime.now()).days
    except (TypeError, ValueError):
        return None


def is_password_expired() -> bool:
    days = password_expires_in_days()
    return days is not None and days < 0


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


def get_enabled_calendars():
    """Return [(name, graph_id)] for all enabled calendars.
    graph_id may be '' for calendars discovered before IDs were stored.
    """
    conn = get_db()
    rows = conn.execute(
        'SELECT outlook_name, graph_id FROM calendars WHERE enabled = 1'
    ).fetchall()
    conn.close()
    return [(r['outlook_name'], r['graph_id'] or '') for r in rows]


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
