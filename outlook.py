import re
import base64
import calendar
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime

import requests

from graph_auth import get_headers as _auth_headers
from database import get_setting

GRAPH = 'https://graph.microsoft.com/v1.0'

_CAL_MAP_TTL = 300  # seconds
_cal_map_cache = {'value': None, 'expires': 0.0}
_cal_map_lock = threading.Lock()


def _headers():
    tz = get_setting('graph_timezone', 'Central Standard Time')
    h = _auth_headers()
    h['Prefer'] = f'outlook.timezone="{tz}"'
    return h


def _parse_dt(dt_str):
    return datetime.fromisoformat(dt_str[:19])


def _fmt_time(dt):
    return dt.strftime('%I:%M %p').lstrip('0')


def _iso_range(month, year):
    last_day = calendar.monthrange(year, month)[1]
    return (
        f'{year}-{month:02d}-01T00:00:00',
        f'{year}-{month:02d}-{last_day:02d}T23:59:59',
    )


def _fetch_events(calendar_id, start_iso, end_iso):
    url = (
        f'{GRAPH}/me/calendars/{calendar_id}/calendarView'
        f'?startDateTime={start_iso}&endDateTime={end_iso}'
        f'&$select=id,subject,start,end&$top=100'
    )
    events = []
    while url:
        r = requests.get(url, headers=_headers())
        r.raise_for_status()
        data = r.json()
        events.extend(data.get('value', []))
        url = data.get('@odata.nextLink')
    return events


def _calendar_id_map():
    with _cal_map_lock:
        if _cal_map_cache['value'] is not None and time.monotonic() < _cal_map_cache['expires']:
            return _cal_map_cache['value']
    r = requests.get(f'{GRAPH}/me/calendars?$select=id,name', headers=_headers())
    r.raise_for_status()
    value = {c['name']: c['id'] for c in r.json().get('value', [])}
    with _cal_map_lock:
        _cal_map_cache['value'] = value
        _cal_map_cache['expires'] = time.monotonic() + _CAL_MAP_TTL
    return value


def _invalidate_calendar_cache():
    with _cal_map_lock:
        _cal_map_cache['value'] = None
        _cal_map_cache['expires'] = 0.0


def discover_calendars():
    _invalidate_calendar_cache()
    try:
        r = requests.get(f'{GRAPH}/me/calendars?$select=id,name', headers=_headers())
        r.raise_for_status()
        return [{'name': c['name'], 'id': c['id']} for c in r.json().get('value', [])]
    except requests.RequestException as e:
        raise RuntimeError(f'Could not read Microsoft 365 calendars: {e}')


def _scan_calendars(enabled_calendar_names, start_iso, end_iso, transform):
    """Fetch events from each enabled calendar in parallel and transform them.

    `transform(event, name)` returns an item dict (or None to skip).
    Event/parse failures for one calendar do not abort the others.
    """
    if not enabled_calendar_names:
        return []
    enabled_set = set(enabled_calendar_names)
    cal_map = _calendar_id_map()
    targets = [(name, cid) for name, cid in cal_map.items() if name in enabled_set]
    if not targets:
        return []

    def _pull(name, cal_id):
        out = []
        try:
            events = _fetch_events(cal_id, start_iso, end_iso)
        except requests.RequestException:
            return out
        for ev in events:
            try:
                item = transform(ev, name)
            except (KeyError, ValueError):
                continue
            if item is not None:
                out.append(item)
        return out

    items = []
    with ThreadPoolExecutor(max_workers=min(8, len(targets))) as pool:
        for result in pool.map(lambda t: _pull(*t), targets):
            items.extend(result)
    return items


def get_today_items(enabled_calendar_names):
    today = date.today().isoformat()
    start, end = f'{today}T00:00:00', f'{today}T23:59:59'

    def transform(ev, _name):
        s = _parse_dt(ev['start']['dateTime'])
        e = _parse_dt(ev['end']['dateTime'])
        return {
            'subject':    ev.get('subject') or '',
            'start_time': _fmt_time(s),
            'end_time':   _fmt_time(e),
            'start_24':   s.strftime('%H:%M'),
            'end_24':     e.strftime('%H:%M'),
        }

    try:
        items = _scan_calendars(enabled_calendar_names, start, end, transform)
    except requests.RequestException:
        return []
    items.sort(key=lambda x: x['start_24'])
    return items


def get_all_calendar_items(month, year, enabled_calendar_names):
    start, end = _iso_range(month, year)

    def transform(ev, name):
        s = _parse_dt(ev['start']['dateTime'])
        e = _parse_dt(ev['end']['dateTime'])
        return {
            'entry_id':   ev['id'],
            'date':       s.strftime('%Y-%m-%d'),
            'day':        s.day,
            'start_time': _fmt_time(s),
            'end_time':   _fmt_time(e),
            'start_24':   s.strftime('%H:%M'),
            'end_24':     e.strftime('%H:%M'),
            'subject':    ev.get('subject') or '',
            'calendar':   name,
        }

    try:
        items = _scan_calendars(enabled_calendar_names, start, end, transform)
    except requests.RequestException as e:
        raise RuntimeError(str(e))
    items.sort(key=lambda x: (x['date'], x['start_24']))
    return items


def get_sessions(initials, month, year, enabled_calendar_names):
    start, end = _iso_range(month, year)
    pattern = re.compile(r'\b' + re.escape(initials.upper()) + r'\b', re.IGNORECASE)

    def transform(ev, name):
        subj = ev.get('subject') or ''
        if not pattern.search(subj):
            return None
        s = _parse_dt(ev['start']['dateTime'])
        e = _parse_dt(ev['end']['dateTime'])
        return {
            'date':           s.strftime('%Y-%m-%d'),
            'date_display':   s.strftime('%B %d, %Y'),
            'start_time':     _fmt_time(s),
            'end_time':       _fmt_time(e),
            'duration_hours': round((e - s).total_seconds() / 3600, 2),
            'subject':        subj,
            'calendar':       name,
        }

    try:
        sessions = _scan_calendars(enabled_calendar_names, start, end, transform)
    except requests.RequestException as e:
        raise RuntimeError(str(e))
    sessions.sort(key=lambda x: x['date'])
    return sessions


def update_calendar_item(entry_id, subject, new_start, new_end):
    tz = get_setting('graph_timezone', 'Central Standard Time')
    payload = {
        'subject': subject,
        'start':   {'dateTime': new_start.strftime('%Y-%m-%dT%H:%M:%S'), 'timeZone': tz},
        'end':     {'dateTime': new_end.strftime('%Y-%m-%dT%H:%M:%S'),   'timeZone': tz},
    }
    r = requests.patch(f'{GRAPH}/me/events/{entry_id}', json=payload, headers=_headers())
    r.raise_for_status()


def send_invoice_email(to_email, subject, body, pdf_path):
    with open(pdf_path, 'rb') as f:
        pdf_b64 = base64.b64encode(f.read()).decode()
    filename = pdf_path.replace('\\', '/').rsplit('/', 1)[-1]
    payload = {
        'message': {
            'subject': subject,
            'body':    {'contentType': 'Text', 'content': body},
            'toRecipients': [{'emailAddress': {'address': to_email}}],
            'attachments': [{
                '@odata.type': '#microsoft.graph.fileAttachment',
                'name':         filename,
                'contentType':  'application/pdf',
                'contentBytes': pdf_b64,
            }],
        },
        'saveToSentItems': True,
    }
    r = requests.post(f'{GRAPH}/me/sendMail', json=payload, headers=_headers())
    r.raise_for_status()
