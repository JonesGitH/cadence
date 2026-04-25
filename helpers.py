"""
Shared helpers used across multiple route modules.
No Flask imports — pure Python, so this module is also safe to import in tests.
"""
import json
import re
from datetime import date as _date
from flask import request

SERVICES = [
    ('written_expression',    'Written Expression'),
    ('grammar',               'Grammar'),
    ('spelling',              'Spelling'),
    ('reading',               'Reading'),
    ('reading_comprehension', 'Reading Comprehension'),
    ('executive_functioning', 'Executive Functioning'),
    ('middle_school_math',    'Middle School Math'),
    ('elementary_math',       'Elementary Math'),
    ('algebra',               'Algebra'),
    ('geometry',              'Geometry'),
    ('algebra2',              'Algebra 2'),
    ('precal',                'PreCal'),
    ('trig',                  'Trig'),
    ('high_school_math',      'High School Math'),
    ('other',                 'Other'),
]

GRADES = ['K', '1st', '2nd', '3rd', '4th', '5th', '6th', '7th',
          '8th', '9th', '10th', '11th', '12th', 'College', 'Other']

SERVICES_MAP = dict(SERVICES)


def current_year_month():
    from datetime import datetime
    now = datetime.now()
    return now.year, now.month


def next_year_month():
    from datetime import datetime
    now = datetime.now()
    if now.month == 12:
        return now.year + 1, 1
    return now.year, now.month + 1


def _calculate_age(birthday_str):
    if not birthday_str:
        return None
    try:
        bday  = _date.fromisoformat(birthday_str)
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
        return f'{p1} & {p2}'
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
        'parent_address':  request.form.get('parent_address',  '').strip(),
        'parent_city':     request.form.get('parent_city',    '').strip(),
        'parent_state':    request.form.get('parent_state',   '').strip(),
        'parent_zip':      request.form.get('parent_zip',     '').strip(),
        'parent2_address': request.form.get('parent2_address', '').strip(),
        'parent2_city':    request.form.get('parent2_city',    '').strip(),
        'parent2_state':   request.form.get('parent2_state',   '').strip(),
        'parent2_zip':     request.form.get('parent2_zip',     '').strip(),
        'bill_to_parent':       request.form.get('bill_to_parent',       '1').strip() or '1',
        'bill_to_custom_name':  request.form.get('bill_to_custom_name',  '').strip(),
        'bill_to_custom_addr':  request.form.get('bill_to_custom_addr',  '').strip(),
        'bill_to_custom_city':  request.form.get('bill_to_custom_city',  '').strip(),
        'bill_to_custom_state': request.form.get('bill_to_custom_state', '').strip(),
        'bill_to_custom_zip':   request.form.get('bill_to_custom_zip',   '').strip(),
        'intake_complete': 1 if request.form.get('intake_complete') else 0,
        'roi_complete':    1 if request.form.get('roi_complete')    else 0,
        'notes':           request.form.get('notes', '').strip(),
        'hourly_rate':     (
            float(request.form.get('hourly_rate'))
            if request.form.get('hourly_rate', '').strip() else None
        ),
    }
