"""
Microsoft Graph API helpers — calendar events and email.

All HTTP calls go through _req() which enforces a timeout and retries on
transient failures (429 rate-limit, 503 service unavailable, network errors).
Calendars are identified by their stored graph_id (stable) rather than by
display name, which breaks if the user renames a calendar in Outlook.
"""
import logging
import re
import base64
import calendar
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime

import requests
from requests.exceptions import Timeout, ConnectionError as ConnError, RequestException

from graph_auth import get_headers as _auth_headers
from database import get_setting

log = logging.getLogger(__name__)

GRAPH = 'https://graph.microsoft.com/v1.0'

# ── HTTP tunables ─────────────────────────────────────────────────────────────
_TIMEOUT      = 15   # seconds per individual request
_MAX_RETRIES  = 3
_RETRY_WAIT   = 2    # base backoff in seconds


def _req(method: str, url: str, **kwargs) -> requests.Response:
    """Make a Graph API call with timeout and retry/backoff.

    Retries on: connection errors, read timeouts, 429, 503.
    Raises immediately on other 4xx / 5xx responses.
    Raises RuntimeError with a user-friendly message on permanent failure.
    """
    kwargs.setdefault('timeout', _TIMEOUT)
    last_exc: Exception | None = None

    for attempt in range(_MAX_RETRIES):
        try:
            r = requests.request(method, url, **kwargs)

            if r.status_code == 429:
                wait = int(r.headers.get('Retry-After', _RETRY_WAIT * (attempt + 1)))
                log.warning('Graph 429 rate-limit; retrying in %ss (attempt %d)', wait, attempt + 1)
                time.sleep(min(wait, 60))
                last_exc = requests.HTTPError(response=r)
                continue

            if r.status_code == 503:
                wait = _RETRY_WAIT * (attempt + 1)
                log.warning('Graph 503; retrying in %ss (attempt %d)', wait, attempt + 1)
                time.sleep(wait)
                last_exc = requests.HTTPError(response=r)
                continue

            if r.status_code == 401:
                raise RuntimeError(
                    'Microsoft 365 session expired. Go to Settings → Microsoft 365 to reconnect.'
                )

            r.raise_for_status()
            return r

        except Timeout as exc:
            last_exc = exc
            log.warning('Graph request timed out (attempt %d/%d): %s', attempt + 1, _MAX_RETRIES, url)
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_WAIT)

        except ConnError as exc:
            last_exc = exc
            log.warning('Graph connection error (attempt %d/%d): %s', attempt + 1, _MAX_RETRIES, exc)
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_WAIT)

        except RuntimeError:
            raise   # user-friendly messages — don't swallow

        except RequestException as exc:
            # Non-retryable HTTP error (e.g. 400, 404)
            raise RuntimeError(f'Microsoft 365 returned an error: {exc}') from exc

    # All retries exhausted
    if isinstance(last_exc, Timeout):
        raise RuntimeError(
            'Microsoft 365 is taking too long to respond. '
            'Check your internet connection and try again.'
        )
    raise RuntimeError(
        f'Cannot reach Microsoft 365. Check your internet connection. ({last_exc})'
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _headers() -> dict:
    tz = get_setting('graph_timezone', 'Central Standard Time')
    h  = _auth_headers()
    h['Prefer'] = f'outlook.timezone="{tz}"'
    return h


def _parse_dt(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str[:19])


def _fmt_time(dt: datetime) -> str:
    return dt.strftime('%I:%M %p').lstrip('0')


def _iso_range(month: int, year: int) -> tuple[str, str]:
    last_day = calendar.monthrange(year, month)[1]
    return (
        f'{year}-{month:02d}-01T00:00:00',
        f'{year}-{month:02d}-{last_day:02d}T23:59:59',
    )


# ── Calendar ID cache (name → id) — fallback for calendars missing graph_id ──

_CAL_MAP_TTL   = 300
_cal_map_cache = {'value': None, 'expires': 0.0}
_cal_map_lock  = threading.Lock()


def _calendar_id_map() -> dict[str, str]:
    """Fetch name→id map from Graph. Cached for _CAL_MAP_TTL seconds."""
    with _cal_map_lock:
        if _cal_map_cache['value'] is not None and time.monotonic() < _cal_map_cache['expires']:
            return _cal_map_cache['value']
    r     = _req('GET', f'{GRAPH}/me/calendars?$select=id,name', headers=_headers())
    value = {c['name']: c['id'] for c in r.json().get('value', [])}
    with _cal_map_lock:
        _cal_map_cache['value']   = value
        _cal_map_cache['expires'] = time.monotonic() + _CAL_MAP_TTL
    return value


def _invalidate_calendar_cache() -> None:
    with _cal_map_lock:
        _cal_map_cache['value']   = None
        _cal_map_cache['expires'] = 0.0


# ── Core event fetcher ────────────────────────────────────────────────────────

def _fetch_events(calendar_id: str, start_iso: str, end_iso: str) -> list[dict]:
    url    = (
        f'{GRAPH}/me/calendars/{calendar_id}/calendarView'
        f'?startDateTime={start_iso}&endDateTime={end_iso}'
        f'&$select=id,subject,start,end,isAllDay&$top=100'
    )
    events: list[dict] = []
    while url:
        r = _req('GET', url, headers=_headers())
        data = r.json()
        events.extend(data.get('value', []))
        url = data.get('@odata.nextLink')
    return events


# ── Public API ────────────────────────────────────────────────────────────────

def discover_calendars() -> list[dict]:
    """Return [{name, id}] from Graph. Invalidates the local name→id cache."""
    _invalidate_calendar_cache()
    try:
        r = _req('GET', f'{GRAPH}/me/calendars?$select=id,name', headers=_headers())
        return [{'name': c['name'], 'id': c['id']} for c in r.json().get('value', [])]
    except RuntimeError:
        raise
    except RequestException as e:
        raise RuntimeError(f'Could not read Microsoft 365 calendars: {e}') from e


def _scan_calendars(
    calendars: list[tuple[str, str]],
    start_iso: str,
    end_iso:   str,
    transform,
) -> list[dict]:
    """Fetch events from each enabled calendar in parallel and transform them.

    ``calendars`` is a list of ``(name, graph_id)`` pairs as stored in the DB.
    If ``graph_id`` is empty (legacy row), falls back to a live name→id lookup
    so renamed calendars still work after a fresh Refresh in Settings.

    ``transform(event, name)`` returns an item dict or None to skip.
    A failure in one calendar does not abort the others.
    """
    if not calendars:
        return []

    # Resolve any entries that lack a stored graph_id
    needs_lookup = [name for name, gid in calendars if not gid]
    live_map: dict[str, str] = {}
    if needs_lookup:
        try:
            live_map = _calendar_id_map()
        except RuntimeError:
            live_map = {}

    targets: list[tuple[str, str]] = []
    for name, gid in calendars:
        cal_id = gid or live_map.get(name)
        if cal_id:
            targets.append((name, cal_id))
        else:
            log.warning('Calendar "%s" has no graph_id — skipped. Refresh calendars in Settings.', name)

    if not targets:
        return []

    def _pull(name: str, cal_id: str) -> list[dict]:
        out: list[dict] = []
        try:
            events = _fetch_events(cal_id, start_iso, end_iso)
        except RuntimeError as exc:
            log.error('Failed to fetch events for calendar "%s": %s', name, exc)
            return out
        for ev in events:
            try:
                item = transform(ev, name)
            except (KeyError, ValueError):
                continue
            if item is not None:
                out.append(item)
        return out

    items: list[dict] = []
    with ThreadPoolExecutor(max_workers=min(8, len(targets))) as pool:
        for result in pool.map(lambda t: _pull(*t), targets):
            items.extend(result)
    return items


def get_today_items(calendars: list[tuple[str, str]]) -> list[dict]:
    today      = date.today().isoformat()
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
        items = _scan_calendars(calendars, start, end, transform)
    except RuntimeError:
        return []
    items.sort(key=lambda x: x['start_24'])
    return items


def get_all_calendar_items(month: int, year: int, calendars: list[tuple[str, str]]) -> list[dict]:
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
            'is_all_day': bool(ev.get('isAllDay')),
        }

    try:
        items = _scan_calendars(calendars, start, end, transform)
    except RuntimeError:
        raise
    items.sort(key=lambda x: (x['date'], x['start_24']))
    return items


def get_sessions(
    initials: str,
    month:    int,
    year:     int,
    calendars: list[tuple[str, str]],
) -> list[dict]:
    start, end = _iso_range(month, year)
    pattern    = re.compile(r'\b' + re.escape(initials.upper()) + r'\b', re.IGNORECASE)

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
        sessions = _scan_calendars(calendars, start, end, transform)
    except RuntimeError:
        raise
    sessions.sort(key=lambda x: x['date'])
    return sessions


def update_calendar_item(
    entry_id:  str,
    subject:   str,
    new_start: datetime,
    new_end:   datetime,
) -> None:
    tz = get_setting('graph_timezone', 'Central Standard Time')
    payload = {
        'subject': subject,
        'start':   {'dateTime': new_start.strftime('%Y-%m-%dT%H:%M:%S'), 'timeZone': tz},
        'end':     {'dateTime': new_end.strftime('%Y-%m-%dT%H:%M:%S'),   'timeZone': tz},
    }
    _req('PATCH', f'{GRAPH}/me/events/{entry_id}', json=payload, headers=_headers())


def send_invoice_email(to_email: str, subject: str, body: str, pdf_path: str) -> None:
    with open(pdf_path, 'rb') as f:
        pdf_b64 = base64.b64encode(f.read()).decode()
    filename = pdf_path.replace('\\', '/').rsplit('/', 1)[-1]
    payload = {
        'message': {
            'subject': subject,
            'body':    {'contentType': 'Text', 'content': body},
            'toRecipients': [{'emailAddress': {'address': to_email}}],
            'attachments': [{
                '@odata.type':  '#microsoft.graph.fileAttachment',
                'name':         filename,
                'contentType':  'application/pdf',
                'contentBytes': pdf_b64,
            }],
        },
        'saveToSentItems': True,
    }
    _req('POST', f'{GRAPH}/me/sendMail', json=payload, headers=_headers())
