import re
import base64
import calendar
import requests
from datetime import date, datetime

from graph_auth import get_headers as _auth_headers
from database import get_setting

GRAPH = 'https://graph.microsoft.com/v1.0'


def _headers():
    tz = get_setting('graph_timezone', 'Central Standard Time')
    h  = _auth_headers()
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
    r = requests.get(f'{GRAPH}/me/calendars?$select=id,name', headers=_headers())
    r.raise_for_status()
    return {c['name']: c['id'] for c in r.json().get('value', [])}


def discover_calendars():
    try:
        r = requests.get(f'{GRAPH}/me/calendars?$select=id,name', headers=_headers())
        r.raise_for_status()
        return [{'name': c['name'], 'id': c['id']} for c in r.json().get('value', [])]
    except Exception as e:
        raise RuntimeError(f'Could not read Microsoft 365 calendars: {e}')


def get_today_items(enabled_calendar_names):
    if not enabled_calendar_names:
        return []
    today       = date.today().isoformat()
    start, end  = f'{today}T00:00:00', f'{today}T23:59:59'
    enabled_set = set(enabled_calendar_names)
    try:
        cal_map = _calendar_id_map()
    except Exception:
        return []
    items = []
    for name, cal_id in cal_map.items():
        if name not in enabled_set:
            continue
        try:
            for ev in _fetch_events(cal_id, start, end):
                s = _parse_dt(ev['start']['dateTime'])
                e = _parse_dt(ev['end']['dateTime'])
                items.append({
                    'subject':    ev.get('subject') or '',
                    'start_time': _fmt_time(s),
                    'end_time':   _fmt_time(e),
                    'start_24':   s.strftime('%H:%M'),
                    'end_24':     e.strftime('%H:%M'),
                })
        except Exception:
            continue
    items.sort(key=lambda x: x['start_24'])
    return items


def get_all_calendar_items(month, year, enabled_calendar_names):
    if not enabled_calendar_names:
        return []
    start, end  = _iso_range(month, year)
    enabled_set = set(enabled_calendar_names)
    try:
        cal_map = _calendar_id_map()
    except Exception as e:
        raise RuntimeError(str(e))
    items = []
    for name, cal_id in cal_map.items():
        if name not in enabled_set:
            continue
        try:
            for ev in _fetch_events(cal_id, start, end):
                s = _parse_dt(ev['start']['dateTime'])
                e = _parse_dt(ev['end']['dateTime'])
                items.append({
                    'entry_id':   ev['id'],
                    'date':       s.strftime('%Y-%m-%d'),
                    'day':        s.day,
                    'start_time': _fmt_time(s),
                    'end_time':   _fmt_time(e),
                    'start_24':   s.strftime('%H:%M'),
                    'end_24':     e.strftime('%H:%M'),
                    'subject':    ev.get('subject') or '',
                    'calendar':   name,
                })
        except Exception:
            continue
    items.sort(key=lambda x: (x['date'], x['start_24']))
    return items


def update_calendar_item(entry_id, subject, new_start, new_end):
    tz      = get_setting('graph_timezone', 'Central Standard Time')
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
    payload  = {
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


def get_sessions(initials, month, year, enabled_calendar_names):
    if not enabled_calendar_names:
        return []
    start, end  = _iso_range(month, year)
    enabled_set = set(enabled_calendar_names)
    pattern     = re.compile(r'\b' + re.escape(initials.upper()) + r'\b', re.IGNORECASE)
    try:
        cal_map = _calendar_id_map()
    except Exception as e:
        raise RuntimeError(str(e))
    sessions = []
    for name, cal_id in cal_map.items():
        if name not in enabled_set:
            continue
        try:
            for ev in _fetch_events(cal_id, start, end):
                subj = ev.get('subject') or ''
                if not pattern.search(subj):
                    continue
                s = _parse_dt(ev['start']['dateTime'])
                e = _parse_dt(ev['end']['dateTime'])
                sessions.append({
                    'date':           s.strftime('%Y-%m-%d'),
                    'date_display':   s.strftime('%B %d, %Y'),
                    'start_time':     _fmt_time(s),
                    'end_time':       _fmt_time(e),
                    'duration_hours': round((e - s).total_seconds() / 3600, 2),
                    'subject':        subj,
                    'calendar':       name,
                })
        except Exception:
            continue
    sessions.sort(key=lambda x: x['date'])
    return sessions
