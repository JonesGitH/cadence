import os
import re
import json
import subprocess
import calendar as cal_module
import threading
import time
from collections import defaultdict
from datetime import datetime, date as _date

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, jsonify
)

from database import (
    init_db, get_db, get_setting, set_setting, get_settings_batch, next_invoice_number,
    get_all_clients, get_client, get_clients_initials_map,
    get_all_calendars, get_enabled_calendar_names,
    upsert_calendars, get_all_invoices, get_invoice, month_name,
    toggle_invoice_paid, get_invoice_years, get_annual_summary, backup_database,
)
from outlook import discover_calendars, get_sessions, send_invoice_email, get_all_calendar_items, update_calendar_item, get_today_items
import graph_auth as _graph_auth
from pdf_generator import build_pdf
import config as _config

_res_dir = os.environ.get('CADENCE_BUNDLE_DIR', os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__,
            template_folder=os.path.join(_res_dir, 'templates'),
            static_folder=os.path.join(_res_dir, 'static'))
app.secret_key = 'cadence-2025-local'

_last_activity      = time.monotonic()
_last_activity_lock = threading.Lock()

def get_last_activity() -> float:
    with _last_activity_lock:
        return _last_activity

@app.after_request
def _touch_activity(response):
    if not request.path.startswith('/static/'):
        global _last_activity
        with _last_activity_lock:
            _last_activity = time.monotonic()
    return response

@app.template_filter('friendly_date')
def friendly_date_filter(value):
    try:
        dt = datetime.strptime(str(value)[:10], '%Y-%m-%d')
        return f"{dt.strftime('%b')} {dt.day}, {dt.year}"
    except ValueError:
        return value

SERVICES = [
    ('written_expression',   'Written Expression'),
    ('grammar',              'Grammar'),
    ('spelling',             'Spelling'),
    ('reading',              'Reading'),
    ('reading_comprehension','Reading Comprehension'),
    ('executive_functioning','Executive Functioning'),
    ('middle_school_math',   'Middle School Math'),
    ('elementary_math',      'Elementary Math'),
    ('algebra',              'Algebra'),
    ('geometry',             'Geometry'),
    ('algebra2',             'Algebra 2'),
    ('precal',               'PreCal'),
    ('trig',                 'Trig'),
    ('high_school_math',     'High School Math'),
    ('other',                'Other'),
]

GRADES = ['K', '1st', '2nd', '3rd', '4th', '5th', '6th', '7th',
          '8th', '9th', '10th', '11th', '12th', 'College', 'Other']

SERVICES_MAP = dict(SERVICES)


def current_year_month():
    now = datetime.now()
    return now.year, now.month


def next_year_month():
    now = datetime.now()
    if now.month == 12:
        return now.year + 1, 1
    return now.year, now.month + 1


def _calculate_age(birthday_str):
    if not birthday_str:
        return None
    try:
        bday = _date.fromisoformat(birthday_str)
        today = _date.today()
        return today.year - bday.year - ((today.month, today.day) < (bday.month, bday.day))
    except Exception:
        return None


def _parse_services(services_str):
    try:
        return json.loads(services_str or '[]')
    except (TypeError, ValueError):
        return []


def _enrich_student(row):
    if row is None:
        return None
    d = dict(row)
    d['services_list'] = _parse_services(d.get('services'))
    d['age'] = _calculate_age(d.get('birthday'))
    return d


def _parent_bill_name(client):
    p1 = (client.get('parent1_name') or '').strip()
    p2 = (client.get('parent2_name') or '').strip()
    if p1 and p2:
        return f"{p1} & {p2}"
    return p1 or p2 or client['name']


def _match_initials(subject, initials_map):
    subj = subject.upper()
    for ini, name in initials_map.items():
        if re.search(r'\b' + re.escape(ini) + r'\b', subj):
            return name
    return None


def _parse_student_form():
    services = request.form.getlist('services')
    return {
        'name':            request.form.get('name',           '').strip(),
        'initials':        request.form.get('initials',       '').strip().upper(),
        'email':           request.form.get('email',          '').strip(),
        'phone':           request.form.get('phone',          '').strip(),
        'school':          request.form.get('school',         '').strip(),
        'grade':           request.form.get('grade',          '').strip(),
        'birthday':        request.form.get('birthday',       '').strip(),
        'diagnosis':       request.form.get('diagnosis',      '').strip(),
        'services':        json.dumps(services),
        'services_other':  request.form.get('services_other', '').strip(),
        'start_date':      request.form.get('start_date',     '').strip(),
        'end_date':        request.form.get('end_date',       '').strip(),
        'test_date':       request.form.get('test_date',      '').strip(),
        'parent1_name':    request.form.get('parent1_name',   '').strip(),
        'parent2_name':    request.form.get('parent2_name',   '').strip(),
        'parent_address':  request.form.get('parent_address', '').strip(),
        'parent_city':     request.form.get('parent_city',    '').strip(),
        'parent_state':    request.form.get('parent_state',   '').strip(),
        'parent_zip':      request.form.get('parent_zip',     '').strip(),
        'intake_complete': 1 if request.form.get('intake_complete') else 0,
        'roi_complete':    1 if request.form.get('roi_complete')    else 0,
        'notes':           request.form.get('notes', '').strip(),
        'hourly_rate':     (float(request.form.get('hourly_rate')) if request.form.get('hourly_rate', '').strip() else None),
    }


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route('/')
def dashboard():
    conn = get_db()
    stats = conn.execute('''
        SELECT
            (SELECT COUNT(*) FROM clients)  AS total_clients,
            (SELECT COUNT(*) FROM invoices) AS total_invoices,
            (SELECT COALESCE(SUM(total_amount), 0) FROM invoices) AS total_billed
    ''').fetchone()
    recent = conn.execute('''
        SELECT i.*, c.name AS client_name
        FROM invoices i JOIN clients c ON c.id = i.client_id
        ORDER BY i.created_at DESC LIMIT 5
    ''').fetchall()
    all_students = [_enrich_student(r) for r in conn.execute('SELECT * FROM clients ORDER BY name').fetchall()]
    conn.close()

    initials_map = {s['initials'].upper(): s['name'] for s in all_students}
    try:
        raw_today = get_today_items(get_enabled_calendar_names())
    except Exception:
        raw_today = []
    now_hhmm = datetime.now().strftime('%H:%M')
    today_appointments = []
    for item in raw_today:
        matched = _match_initials(item['subject'], initials_map)
        today_appointments.append({
            'student':    matched or item['subject'],
            'start_time': item['start_time'],
            'end_time':   item['end_time'],
            'matched':    matched is not None,
            'overdue':    item.get('end_24', '99:99') < now_hhmm,
        })

    schools   = defaultdict(int)
    ages      = defaultdict(int)
    services  = defaultdict(int)
    for s in all_students:
        school = (s.get('school') or '').strip() or 'No School Listed'
        schools[school] += 1
        if s['age'] is not None:
            ages[s['age']] += 1
        for svc_key in s['services_list']:
            services[svc_key] += 1

    school_counts  = sorted(schools.items(),  key=lambda x: (x[0] == 'No School Listed', x[0].lower()))
    age_counts     = sorted(ages.items(),     key=lambda x: x[0])
    service_counts = sorted(services.items(), key=lambda x: -x[1])

    return render_template('dashboard.html',
        total_clients=stats['total_clients'],
        total_invoices=stats['total_invoices'],
        total_billed=stats['total_billed'],
        recent=recent,
        month_name=month_name,
        school_counts=school_counts,
        age_counts=age_counts,
        service_counts=service_counts,
        services_map=SERVICES_MAP,
        today_appointments=today_appointments,
    )


# ── Calendar ──────────────────────────────────────────────────────────────────

@app.route('/calendar')
def calendar_view():
    now   = datetime.now()
    try:
        month = int(request.args.get('month', now.month))
        year  = int(request.args.get('year',  now.year))
    except (ValueError, TypeError):
        month, year = now.month, now.year
    if month < 1:  month, year = 12, year - 1
    if month > 12: month, year = 1,  year + 1

    enabled      = get_enabled_calendar_names()
    initials_map = get_clients_initials_map()

    cal_items = []
    error     = None
    if enabled:
        try:
            cal_items = get_all_calendar_items(month, year, enabled)
            for item in cal_items:
                item['student'] = _match_initials(item['subject'], initials_map)
        except RuntimeError as e:
            error = str(e)

    by_day = defaultdict(list)
    for item in cal_items:
        by_day[item['day']].append(item)

    first_weekday, days_in_month = cal_module.monthrange(year, month)
    first_weekday = (first_weekday + 1) % 7  # convert Mon=0 → Sun=0

    prev_month = month - 1 if month > 1 else 12
    prev_year  = year      if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year  = year      if month < 12 else year + 1
    today_day  = now.day if (now.month == month and now.year == year) else None

    return render_template('calendar.html',
        month=month, year=year,
        month_name_str=cal_module.month_name[month],
        days_in_month=days_in_month,
        first_weekday=first_weekday,
        by_day=by_day,
        enabled=enabled,
        error=error,
        prev_month=prev_month, prev_year=prev_year,
        next_month=next_month, next_year=next_year,
        today_day=today_day,
    )


@app.route('/calendar/item/update', methods=['POST'])
def calendar_item_update():
    data     = request.get_json()
    entry_id = data.get('entry_id', '').strip()
    subject  = data.get('subject',  '').strip()
    date_str = data.get('date',     '').strip()
    start_t  = data.get('start',    '').strip()
    end_t    = data.get('end',      '').strip()

    if not entry_id or not subject or not date_str or not start_t or not end_t:
        return jsonify({'error': 'All fields are required.'}), 400

    try:
        new_start = datetime.strptime(f"{date_str} {start_t}", '%Y-%m-%d %H:%M')
        new_end   = datetime.strptime(f"{date_str} {end_t}",   '%Y-%m-%d %H:%M')
        if new_end <= new_start:
            return jsonify({'error': 'End time must be after start time.'}), 400
        update_calendar_item(entry_id, subject, new_start, new_end)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': f'Could not update Outlook: {e}'}), 500


# ── Students ──────────────────────────────────────────────────────────────────

@app.route('/clients')
def clients():
    all_students = [_enrich_student(r) for r in get_all_clients()]
    active   = [s for s in all_students if s['active']]
    inactive = [s for s in all_students if not s['active']]
    return render_template('clients.html', clients=active, archived=inactive)


@app.route('/clients/add', methods=['GET', 'POST'])
def add_client():
    if request.method == 'GET':
        return render_template('student_form.html',
            student=None, services=SERVICES, grades=GRADES)

    d = _parse_student_form()
    if not d['name'] or not d['initials']:
        flash('Name and initials are required.', 'error')
        return render_template('student_form.html',
            student=d, services=SERVICES, grades=GRADES)

    conn = get_db()
    conn.execute('''
        INSERT INTO clients
            (name, initials, email, phone, school, grade, birthday, diagnosis,
             services, services_other, start_date, end_date, test_date,
             parent1_name, parent2_name, parent_address, parent_city,
             parent_state, parent_zip, intake_complete, roi_complete, notes, hourly_rate)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (d['name'], d['initials'], d['email'], d['phone'],
          d['school'], d['grade'], d['birthday'], d['diagnosis'],
          d['services'], d['services_other'],
          d['start_date'], d['end_date'], d['test_date'],
          d['parent1_name'], d['parent2_name'], d['parent_address'],
          d['parent_city'], d['parent_state'], d['parent_zip'],
          d['intake_complete'], d['roi_complete'], d['notes'], d['hourly_rate']))
    conn.commit()
    conn.close()
    flash(f'Student "{d["name"]}" added.', 'success')
    return redirect(url_for('clients'))


@app.route('/clients/<int:client_id>/edit', methods=['GET', 'POST'])
def edit_client(client_id):
    if request.method == 'GET':
        student = _enrich_student(get_client(client_id))
        if not student:
            flash('Student not found.', 'error')
            return redirect(url_for('clients'))
        return render_template('student_form.html',
            student=student, services=SERVICES, grades=GRADES)

    d = _parse_student_form()
    if not d['name'] or not d['initials']:
        flash('Name and initials are required.', 'error')
        d['id'] = client_id
        d['services_list'] = _parse_services(d.get('services'))
        d['age'] = _calculate_age(d.get('birthday'))
        return render_template('student_form.html',
            student=d, services=SERVICES, grades=GRADES)

    conn = get_db()
    conn.execute('''
        UPDATE clients SET
            name=?, initials=?, email=?, phone=?, school=?, grade=?, birthday=?,
            diagnosis=?, services=?, services_other=?, start_date=?, end_date=?,
            test_date=?, parent1_name=?, parent2_name=?, parent_address=?,
            parent_city=?, parent_state=?, parent_zip=?,
            intake_complete=?, roi_complete=?, notes=?, hourly_rate=?
        WHERE id=?
    ''', (d['name'], d['initials'], d['email'], d['phone'],
          d['school'], d['grade'], d['birthday'], d['diagnosis'],
          d['services'], d['services_other'],
          d['start_date'], d['end_date'], d['test_date'],
          d['parent1_name'], d['parent2_name'], d['parent_address'],
          d['parent_city'], d['parent_state'], d['parent_zip'],
          d['intake_complete'], d['roi_complete'], d['notes'], d['hourly_rate'], client_id))
    conn.commit()
    conn.close()
    flash(f'Student "{d["name"]}" updated.', 'success')
    return redirect(url_for('clients'))


def _set_client_active(client_id, active, flash_template):
    conn = get_db()
    conn.execute('UPDATE clients SET active=? WHERE id=?', (active, client_id))
    conn.commit()
    name = conn.execute('SELECT name FROM clients WHERE id=?', (client_id,)).fetchone()
    conn.close()
    if name:
        flash(flash_template.format(name=name['name']), 'success')


@app.route('/clients/<int:client_id>/archive', methods=['POST'])
def archive_client(client_id):
    _set_client_active(client_id, 0, '"{name}" archived. Restore them from the Archived section.')
    return redirect(url_for('clients'))


@app.route('/clients/<int:client_id>/restore', methods=['POST'])
def restore_client(client_id):
    _set_client_active(client_id, 1, '"{name}" restored to active students.')
    return redirect(url_for('clients'))


@app.route('/clients/<int:client_id>/delete', methods=['POST'])
def delete_client(client_id):
    conn = get_db()
    client = conn.execute('SELECT name FROM clients WHERE id=?', (client_id,)).fetchone()
    if client:
        conn.execute('DELETE FROM clients WHERE id=?', (client_id,))
        conn.commit()
        flash(f'Student "{client["name"]}" deleted.', 'success')
    conn.close()
    return redirect(url_for('clients'))


# ── Invoices ──────────────────────────────────────────────────────────────────

@app.route('/invoices')
def invoices():
    all_inv = get_all_invoices()
    years   = sorted({i['year'] for i in all_inv}, reverse=True)
    clients = sorted({i['client_name'] for i in all_inv})
    return render_template('invoice_history.html', invoices=all_inv,
                           month_name=month_name, years=years, filter_clients=clients)


@app.route('/invoices/create')
def create_invoice():
    year, month = next_year_month()
    cur_year = current_year_month()[0]
    return render_template('create_invoice.html',
        clients=get_all_clients(active_only=True),
        months=[(i, cal_module.month_name[i]) for i in range(1, 13)],
        years=list(range(cur_year - 2, cur_year + 2)),
        current_month=month,
        current_year=year,
    )


@app.route('/invoices/fetch-sessions', methods=['POST'])
def fetch_sessions():
    data      = request.get_json() or {}
    client_id = data.get('client_id')
    try:
        month = int(data.get('month'))
        year  = int(data.get('year'))
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid month or year.'}), 400

    client = get_client(client_id)
    if not client:
        return jsonify({'error': 'Student not found.'}), 404

    enabled = get_enabled_calendar_names()
    if not enabled:
        return jsonify({'error': 'No calendars are enabled. Go to Settings > Calendars.'}), 400

    try:
        sessions = get_sessions(client['initials'], month, year, enabled)
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 500

    global_rate = float(get_setting('hourly_rate', '0'))
    rate = float(client['hourly_rate']) if client['hourly_rate'] else global_rate
    for s in sessions:
        s['rate']       = rate
        s['line_total'] = rate  # flat per-session rate

    return jsonify({'sessions': sessions, 'rate': rate})


@app.route('/invoices/generate', methods=['POST'])
def generate_invoice():
    data      = request.get_json() or {}
    client_id = data.get('client_id')
    try:
        month = int(data.get('month'))
        year  = int(data.get('year'))
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid month or year.'}), 400
    sessions  = data.get('sessions', [])
    late_fee  = data.get('late_fee')
    credit    = data.get('credit')
    force     = data.get('force', False)

    if not sessions:
        return jsonify({'error': 'No sessions selected.'}), 400

    client = get_client(client_id)
    if not client:
        return jsonify({'error': 'Student not found.'}), 404

    conn = get_db()

    if not force:
        existing = conn.execute(
            'SELECT id, invoice_number FROM invoices WHERE client_id=? AND month=? AND year=?',
            (client_id, month, year)
        ).fetchone()
        if existing:
            conn.close()
            return jsonify({
                'duplicate': True,
                'existing_invoice_id': existing['id'],
                'existing_number':     existing['invoice_number'],
            })

    cfg = get_settings_batch(('hourly_rate', 'business_name', 'business_title',
                               'business_email', 'business_phone', 'business_address',
                               'business_city', 'business_state', 'business_zip', 'venmo_handle'))

    rate             = float(cfg.get('hourly_rate', '0'))
    total_hours      = round(sum(s['duration_hours'] for s in sessions), 2)
    late_fee_amount  = round(float(late_fee['amount']), 2) if late_fee else 0
    credit_amount    = round(float(credit['amount']),   2) if credit   else 0
    total_amount     = round(len(sessions) * rate + late_fee_amount - credit_amount, 2)
    inv_number       = next_invoice_number(conn)
    now              = datetime.now()

    cursor = conn.execute('''
        INSERT INTO invoices
            (invoice_number, client_id, month, year, total_hours, total_amount, hourly_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (inv_number, client_id, month, year, total_hours, total_amount, rate))
    invoice_id = cursor.lastrowid

    lines_for_pdf = []
    for s in sessions:
        conn.execute('''
            INSERT INTO invoice_lines
                (invoice_id, session_date, start_time, end_time, duration_hours, rate, line_total, line_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'session')
        ''', (invoice_id, s['date_display'], s['start_time'], s['end_time'],
              s['duration_hours'], rate, rate))
        lines_for_pdf.append({
            'line_type':      'session',
            'session_date':   s['date_display'],
            'start_time':     s['start_time'],
            'end_time':       s['end_time'],
            'duration_hours': s['duration_hours'],
            'rate':           rate,
            'line_total':     rate,
        })

    if late_fee:
        late_fee_note = (late_fee.get('note') or 'Late fee').strip()
        conn.execute('''
            INSERT INTO invoice_lines
                (invoice_id, session_date, start_time, end_time, duration_hours, rate, line_total, line_type, note)
            VALUES (?, '', '', '', 0, 0, ?, 'late_fee', ?)
        ''', (invoice_id, late_fee_amount, late_fee_note))
        lines_for_pdf.append({'line_type': 'late_fee', 'note': late_fee_note, 'line_total': late_fee_amount})

    if credit:
        credit_note = (credit.get('note') or 'Credit').strip()
        conn.execute('''
            INSERT INTO invoice_lines
                (invoice_id, session_date, start_time, end_time, duration_hours, rate, line_total, line_type, note)
            VALUES (?, '', '', '', 0, 0, ?, 'credit', ?)
        ''', (invoice_id, credit_amount, credit_note))
        lines_for_pdf.append({'line_type': 'credit', 'note': credit_note, 'line_total': credit_amount})

    conn.commit()

    invoice_dict = {
        'invoice_number': inv_number,
        'client_name':    client['name'],
        'student_name':   client['name'],
        'month':          month,
        'year':           year,
        'hourly_rate':    rate,
        'total_hours':    total_hours,
        'total_amount':   total_amount,
        'invoice_date':   f"{now.month}/{now.day}/{now.year}",
    }
    business = {
        'name':         cfg.get('business_name',    'Your Name'),
        'title':        cfg.get('business_title',   ''),
        'email':        cfg.get('business_email',   ''),
        'phone':        cfg.get('business_phone',   ''),
        'address':      cfg.get('business_address', ''),
        'city':         cfg.get('business_city',    ''),
        'state':        cfg.get('business_state',   ''),
        'zip':          cfg.get('business_zip',     ''),
        'venmo_handle': cfg.get('venmo_handle',     ''),
    }
    parent = {
        'name':    _parent_bill_name(dict(client)),
        'address': client['parent_address'] or '',
        'city':    client['parent_city']    or '',
        'state':   client['parent_state']   or '',
        'zip':     client['parent_zip']     or '',
    }

    try:
        pdf_path = build_pdf(invoice_dict, lines_for_pdf, business, parent,
                              pdf_folder=_config.load()['pdf_folder'])
        conn.execute('UPDATE invoices SET pdf_path=? WHERE id=?', (pdf_path, invoice_id))
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Invoice saved but PDF failed: {e}'}), 500

    conn.close()
    return jsonify({'success': True, 'invoice_id': invoice_id, 'pdf_path': pdf_path})


@app.route('/invoices/<int:invoice_id>')
def invoice_detail(invoice_id):
    inv, lines = get_invoice(invoice_id)
    if not inv:
        flash('Invoice not found.', 'error')
        return redirect(url_for('invoices'))
    client = _enrich_student(get_client(inv['client_id']))
    return render_template('invoice_detail.html', inv=inv, lines=lines, client=client, month_name=month_name)


@app.route('/invoices/<int:invoice_id>/toggle-paid', methods=['POST'])
def toggle_paid(invoice_id):
    new_paid = toggle_invoice_paid(invoice_id)
    if new_paid is None:
        return jsonify({'error': 'Invoice not found.'}), 404
    return jsonify({'paid': bool(new_paid)})


@app.route('/summary')
@app.route('/summary/<int:year>')
def annual_summary(year=None):
    years = get_invoice_years()
    if year is None:
        year = years[0] if years else datetime.now().year
    data = get_annual_summary(year)
    return render_template('annual_summary.html',
        year=year, years=years, month_name=month_name, **data)


@app.route('/summary/<int:year>/export.csv')
def export_summary_csv(year):
    import csv, io
    conn = get_db()
    rows = conn.execute('''
        SELECT i.invoice_number, c.name AS student, i.month, i.year,
               i.total_hours, i.total_amount, i.hourly_rate,
               CASE WHEN i.paid=1 THEN 'Paid' ELSE 'Unpaid' END AS status,
               i.paid_at, i.created_at
        FROM invoices i JOIN clients c ON c.id = i.client_id
        WHERE i.year=? ORDER BY i.month, c.name
    ''', (year,)).fetchall()
    conn.close()

    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow(['Invoice #', 'Student', 'Month', 'Year', 'Hours', 'Amount',
                'Rate', 'Status', 'Paid Date', 'Created'])
    for r in rows:
        w.writerow([r['invoice_number'], r['student'],
                    cal_module.month_name[r['month']], r['year'],
                    r['total_hours'], r['total_amount'], r['hourly_rate'],
                    r['status'], r['paid_at'] or '', r['created_at'][:10]])

    from flask import Response
    return Response(buf.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=cadence_{year}.csv'})


@app.route('/settings/backup', methods=['POST'])
def backup_db():
    try:
        path = backup_database()
        flash(f'Backup saved: {path}', 'success')
    except Exception as e:
        flash(f'Backup failed: {e}', 'error')
    return redirect(url_for('settings'))


@app.route('/invoices/<int:invoice_id>/delete', methods=['POST'])
def delete_invoice(invoice_id):
    conn = get_db()
    inv = conn.execute('SELECT invoice_number FROM invoices WHERE id=?', (invoice_id,)).fetchone()
    if inv:
        conn.execute('DELETE FROM invoice_lines WHERE invoice_id=?', (invoice_id,))
        conn.execute('DELETE FROM invoices WHERE id=?', (invoice_id,))
        conn.commit()
        flash(f'Invoice {inv["invoice_number"]} deleted.', 'success')
    conn.close()
    return redirect(url_for('invoices'))


@app.route('/invoices/<int:invoice_id>/open-pdf', methods=['POST'])
def open_pdf(invoice_id):
    inv, _ = get_invoice(invoice_id)
    if not inv or not inv['pdf_path']:
        return jsonify({'error': 'PDF not found. Try regenerating the invoice.'}), 404
    try:
        os.startfile(inv['pdf_path'])
        return jsonify({'success': True})
    except (FileNotFoundError, OSError):
        return jsonify({'error': 'PDF not found. Try regenerating the invoice.'}), 404


@app.route('/invoices/<int:invoice_id>/open-folder', methods=['POST'])
def open_folder(invoice_id):
    inv, _ = get_invoice(invoice_id)
    if not inv or not inv['pdf_path']:
        return jsonify({'error': 'Folder not found.'}), 404
    try:
        subprocess.Popen(['explorer', os.path.dirname(inv['pdf_path'])])
        return jsonify({'success': True})
    except OSError:
        return jsonify({'error': 'Folder not found.'}), 404


@app.route('/invoices/<int:invoice_id>/send-email', methods=['POST'])
def send_email(invoice_id):
    inv, _ = get_invoice(invoice_id)
    if not inv:
        return jsonify({'error': 'Invoice not found.'}), 404
    if not inv['pdf_path']:
        return jsonify({'error': 'PDF not found. Open the invoice to regenerate it.'}), 404

    client = get_client(inv['client_id'])
    if not client or not client['email']:
        return jsonify({'error': 'This student has no email address. Add one in Students.'}), 400

    cfg = get_settings_batch(('business_name', 'business_title', 'business_phone', 'business_email'))

    period  = month_name(inv['month'], inv['year'])
    subject = f"Invoice {inv['invoice_number']} – {period}"
    body = (
        f"Dear {_parent_bill_name(dict(client))},\n\n"
        f"Please find attached your invoice for {period}.\n\n"
        f"Invoice #:  {inv['invoice_number']}\n"
        f"Student:    {client['name']}\n"
        f"Amount:     ${inv['total_amount']:,.2f}\n\n"
        f"Thank you for your continued trust in my services. "
        f"Please don't hesitate to reach out with any questions.\n\n"
        f"Best regards,\n"
        f"{cfg.get('business_name', '')}\n"
        f"{cfg.get('business_title', '')}\n"
        f"{cfg.get('business_phone', '')}\n"
        f"{cfg.get('business_email', '')}"
    )

    try:
        send_invoice_email(client['email'], subject, body, inv['pdf_path'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': f'Could not send email: {e}'}), 500


# ── Settings ──────────────────────────────────────────────────────────────────

_SETTINGS_DEFAULTS = {
    'hourly_rate':          '0',
    'business_name':        'Your Name',
    'business_title':       '',
    'business_email':       'your@email.com',
    'business_phone':       '(555) 555-5555',
    'business_address':     '',
    'business_city':        '',
    'business_state':       '',
    'business_zip':         '',
    'venmo_handle':         '',
    'graph_client_id':      '',
    'graph_timezone':       'Central Standard Time',
    'idle_timeout_minutes': '30',
}


@app.route('/settings')
def settings():
    cfg   = get_settings_batch(tuple(_SETTINGS_DEFAULTS))
    s     = {k: cfg.get(k, v) for k, v in _SETTINGS_DEFAULTS.items()}
    paths = _config.load()
    return render_template('settings.html', s=s, calendars=get_all_calendars(), paths=paths,
                           graph_connected=_graph_auth.is_connected())


@app.route('/settings/storage/save', methods=['POST'])
def save_storage():
    import shutil
    new_db     = request.form.get('db_path',    '').strip()
    new_folder = request.form.get('pdf_folder', '').strip()

    current = _config.load()
    old_db  = current['db_path']

    if new_db and new_db != old_db:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(new_db)), exist_ok=True)
            if os.path.exists(old_db) and not os.path.exists(new_db):
                shutil.copy2(old_db, new_db)
        except OSError as e:
            flash(f'Could not move database: {e}', 'error')
            return redirect(url_for('settings'))

    _config.save(new_db or old_db, new_folder or current['pdf_folder'])
    flash('Storage paths saved. Restart Cadence on both PCs for changes to take effect.', 'warning')
    return redirect(url_for('settings'))


@app.route('/settings/save', methods=['POST'])
def save_settings():
    for key in ('hourly_rate', 'business_name', 'business_title', 'business_email',
                'business_phone', 'business_address', 'business_city',
                'business_state', 'business_zip', 'venmo_handle', 'idle_timeout_minutes'):
        set_setting(key, request.form.get(key, ''))
    flash('Settings saved.', 'success')
    return redirect(url_for('settings'))


@app.route('/settings/calendars/save', methods=['POST'])
def save_calendars():
    conn = get_db()
    all_cals = conn.execute('SELECT id FROM calendars').fetchall()
    for cal in all_cals:
        enabled    = 1 if request.form.get(f'enabled_{cal["id"]}') else 0
        is_default = 1 if request.form.get(f'default_{cal["id"]}') else 0
        conn.execute(
            'UPDATE calendars SET enabled=?, is_default=? WHERE id=?',
            (enabled, is_default, cal['id'])
        )
    conn.commit()
    conn.close()
    flash('Calendar preferences saved.', 'success')
    return redirect(url_for('settings'))


@app.route('/settings/graph/save', methods=['POST'])
def save_graph_settings():
    client_id = request.form.get('graph_client_id', '').strip()
    timezone  = request.form.get('graph_timezone', '').strip()
    if client_id:
        set_setting('graph_client_id', client_id)
    if timezone:
        set_setting('graph_timezone', timezone)
    flash('Microsoft 365 settings saved.', 'success')
    return redirect(url_for('settings'))


@app.route('/settings/graph/connect', methods=['POST'])
def graph_connect():
    try:
        info = _graph_auth.start_device_flow()
        return jsonify(info)
    except RuntimeError as e:
        msg = str(e)
        if msg == 'no_client_id':
            msg = 'Enter and save your Azure App Client ID first.'
        return jsonify({'error': msg}), 400


@app.route('/settings/graph/poll')
def graph_auth_poll():
    return jsonify(_graph_auth.poll_auth())


@app.route('/settings/graph/disconnect', methods=['POST'])
def graph_disconnect():
    _graph_auth.disconnect()
    flash('Disconnected from Microsoft 365.', 'success')
    return redirect(url_for('settings'))


@app.route('/settings/calendars/refresh', methods=['POST'])
def refresh_calendars():
    try:
        cals = discover_calendars()
        upsert_calendars(cals)
        flash(f'Found {len(cals)} calendar(s) in Microsoft 365.', 'success')
    except RuntimeError as e:
        flash(f'Could not read calendars: {e}', 'error')
    return redirect(url_for('settings'))


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    import webbrowser, threading
    def open_browser():
        webbrowser.open('http://127.0.0.1:5000')
    threading.Timer(1.2, open_browser).start()
    app.run(host='127.0.0.1', port=5000, debug=False)
