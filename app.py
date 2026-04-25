"""
app.py — Flask application factory.

Creates the Flask app object, wires up the secret key, activity tracking,
auth gate, and template filter, then imports all route modules so their
@app.route decorators register against the shared `app` instance.
"""
import logging
import os
import threading
import time
from datetime import datetime

from flask import Flask, redirect, request, session, url_for

from database import (
    get_or_create_secret_key,
    init_db,
    password_is_set,
)

log = logging.getLogger(__name__)

# ── Resource directory (frozen bundle or source tree) ─────────────────────────
_res_dir = os.environ.get('CADENCE_BUNDLE_DIR', os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__,
            template_folder=os.path.join(_res_dir, 'templates'),
            static_folder=os.path.join(_res_dir, 'static'))
app.secret_key = get_or_create_secret_key()

# ── Activity tracking (used by main.py for idle-timeout tray logic) ───────────
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


# ── Authentication gate ───────────────────────────────────────────────────────
_AUTH_EXEMPT = {'unlock', 'change_password', 'static'}


@app.before_request
def _require_auth():
    ep = request.endpoint or ''
    if ep in _AUTH_EXEMPT or ep.startswith('static'):
        return None
    if not password_is_set():
        return None
    if not session.get('authenticated'):
        next_url = request.path
        return redirect(url_for('unlock', next=next_url if next_url != '/' else None))
    if session.get('force_change') and ep != 'change_password':
        return redirect(url_for('change_password'))
    return None


# ── Template filter ───────────────────────────────────────────────────────────
@app.template_filter('friendly_date')
def friendly_date_filter(value):
    try:
        dt = datetime.strptime(str(value)[:10], '%Y-%m-%d')
        return f"{dt.strftime('%b')} {dt.day}, {dt.year}"
    except ValueError:
        return value


# ── Route modules — import last so decorators see the app object above ────────
import routes.auth        # noqa: E402, F401
import routes.dashboard   # noqa: E402, F401
import routes.calendar    # noqa: E402, F401
import routes.clients     # noqa: E402, F401
import routes.invoices    # noqa: E402, F401
import routes.settings    # noqa: E402, F401


# ── Dev entry point ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    import webbrowser
    threading.Timer(1.2, lambda: webbrowser.open('http://127.0.0.1:5000')).start()
    app.run(host='127.0.0.1', port=5000, debug=False)
