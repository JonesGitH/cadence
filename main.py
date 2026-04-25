"""
Cadence entry point — starts Flask in a background thread and shows a
Windows system-tray icon. Used by the packaged .exe and by launch.bat.
"""
import sys
import os
import threading
import webbrowser
import time
import socket
import traceback

# ── Resolve dirs before importing any cadence module ─────────────────────────
# BUNDLE_DIR  →  read-only resources (templates, static); sys._MEIPASS when frozen
# DATA_DIR    →  writable data (cadence.db, config.txt); beside the .exe when frozen

if getattr(sys, 'frozen', False):
    _BUNDLE_DIR = sys._MEIPASS
    _DATA_DIR   = os.path.dirname(sys.executable)
else:
    _BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    _DATA_DIR   = _BUNDLE_DIR

# ── Logging — configured before any cadence module is imported ────────────────
import logging
import logging.handlers

_LOG_PATH = os.path.join(_DATA_DIR, 'cadence.log')

_log_handler = logging.handlers.RotatingFileHandler(
    _LOG_PATH, maxBytes=2 * 1024 * 1024, backupCount=3, encoding='utf-8'
)
_log_handler.setFormatter(
    logging.Formatter('%(asctime)s %(levelname)-8s %(name)s  %(message)s',
                      datefmt='%Y-%m-%d %H:%M:%S')
)
logging.basicConfig(level=logging.INFO, handlers=[_log_handler])
# Keep noisy libraries quiet
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('waitress').setLevel(logging.WARNING)

_applog = logging.getLogger('cadence.main')

def _log(msg: str) -> None:
    """Fallback plain-text logger for pre-import crash capture."""
    _applog.critical(msg)

sys.excepthook = lambda etype, val, tb: _log(
    ''.join(traceback.format_exception(etype, val, tb))
)

os.environ.setdefault('CADENCE_BUNDLE_DIR', _BUNDLE_DIR)
os.environ.setdefault('CADENCE_DATA_DIR',   _DATA_DIR)

sys.path.insert(0, _BUNDLE_DIR)

# ── Bootstrap DB then import Flask app ───────────────────────────────────────
from version import __version__
from database import init_db, get_setting
_applog.info('Cadence %s starting — data dir: %s', __version__, _DATA_DIR)
init_db()

from app import app as _flask_app, get_last_activity

PORT = 5000


def _free_port(start: int = PORT) -> int:
    for p in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', p))
                return p
            except OSError:
                continue
    return start


_server = None  # waitress.TcpServer — set by main(), used by _shutdown()


def _run_server(port: int) -> None:
    """Start the Waitress WSGI server (blocks until _server.close() is called)."""
    import waitress
    global _server
    _server = waitress.create_server(_flask_app, host='127.0.0.1', port=port,
                                     threads=4, channel_timeout=120)
    _applog.info('Waitress listening on http://127.0.0.1:%d', port)
    _server.run()
    _applog.info('Waitress server stopped')


def _open_browser(port: int) -> None:
    time.sleep(1.5)
    webbrowser.open(f'http://127.0.0.1:{port}')


def _make_tray_image():
    """Build the tray icon image inline — no file I/O, no cross-module imports."""
    from PIL import Image, ImageDraw
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    pad = max(1, size // 16)
    d.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=max(2, size // 6),
        fill='#2563eb',
    )
    cx, cy, r = size // 2, size // 2, size // 4
    d.polygon(
        [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)],
        fill='white',
    )
    return img


def _shutdown(icon) -> None:
    """Stop the tray icon, close the WSGI server, then exit cleanly."""
    _applog.info('Shutdown requested')
    try:
        icon.stop()
    except Exception:
        pass
    if _server is not None:
        try:
            _server.close()
        except Exception:
            pass
    # Give waitress a moment to drain, then exit
    time.sleep(0.4)
    sys.exit(0)


def _idle_watcher(icon, timeout_minutes: int) -> None:
    timeout_sec = timeout_minutes * 60
    check_interval = max(5, min(60, timeout_sec // 2))
    while True:
        time.sleep(check_interval)
        if time.monotonic() - get_last_activity() > timeout_sec:
            _shutdown(icon)
            return


def main() -> None:
    import pystray

    port = _free_port()

    threading.Thread(target=_run_server,   args=(port,), daemon=True).start()
    threading.Thread(target=_open_browser, args=(port,), daemon=True).start()

    def on_open(icon, item):
        webbrowser.open(f'http://127.0.0.1:{port}')

    def on_quit(icon, item):
        _shutdown(icon)

    icon = pystray.Icon(
        'Cadence',
        _make_tray_image(),
        'Cadence',
        pystray.Menu(
            pystray.MenuItem('Open Cadence', on_open, default=True),
            pystray.MenuItem('Stop Cadence', on_quit),
        ),
    )

    timeout = int(get_setting('idle_timeout_minutes', '30') or '30')
    if timeout > 0:
        threading.Thread(target=_idle_watcher, args=(icon, timeout), daemon=True).start()

    icon.run()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        _log(traceback.format_exc())
