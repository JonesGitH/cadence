"""Dashboard route."""
import logging
from collections import defaultdict
from datetime import datetime
from flask import render_template
from app import app
from database import get_db, get_enabled_calendars, month_name
from outlook import get_today_items
from helpers import _enrich_student, _match_initials, SERVICES_MAP

log = logging.getLogger(__name__)


@app.route('/')
def dashboard():
    conn  = get_db()
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
    all_students = [_enrich_student(r)
                    for r in conn.execute('SELECT * FROM clients ORDER BY name').fetchall()]
    conn.close()

    initials_map = {s['initials'].upper(): s['name'] for s in all_students}
    calendar_error = None
    try:
        raw_today = get_today_items(get_enabled_calendars())
    except RuntimeError as e:
        raw_today = []
        calendar_error = str(e)
    except Exception as e:
        raw_today = []
        log.warning('Calendar fetch failed: %s', e)
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

    schools  = defaultdict(int)
    ages     = defaultdict(int)
    services = defaultdict(int)
    for s in all_students:
        school = (s.get('school') or '').strip() or 'No School Listed'
        schools[school] += 1
        if s['age'] is not None:
            ages[s['age']] += 1
        for svc_key in s['services_list']:
            services[svc_key] += 1

    return render_template('dashboard.html',
        total_clients=stats['total_clients'],
        total_invoices=stats['total_invoices'],
        total_billed=stats['total_billed'],
        recent=recent,
        month_name=month_name,
        school_counts=sorted(schools.items(),
                             key=lambda x: (x[0] == 'No School Listed', x[0].lower())),
        age_counts=sorted(ages.items(), key=lambda x: x[0]),
        service_counts=sorted(services.items(), key=lambda x: -x[1]),
        services_map=SERVICES_MAP,
        today_appointments=today_appointments,
        calendar_error=calendar_error,
    )
