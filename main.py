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

# ── Resolve dirs before importing any cadence module ─────────────────────────
# BUNDLE_DIR  →  read-only resources (templates, static); sys._MEIPASS when frozen
# DATA_DIR    →  writable data (cadence.db, config.txt); beside the .exe when frozen

if getattr(sys, 'frozen', False):
    _BUNDLE_DIR = sys._MEIPASS
    _DATA_DIR   = os.path.dirname(sys.executable)
else:
    _BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    _DATA_DIR   = _BUNDLE_DIR

os.environ.setdefault('CADENCE_BUNDLE_DIR', _BUNDLE_DIR)
os.environ.setdefault('CADENCE_DATA_DIR',   _DATA_DIR)

sys.path.insert(0, _BUNDLE_DIR)

# ── Bootstrap DB then import Flask app ───────────────────────────────────────
from database import init_db, get_setting
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


def _run_flask(port: int) -> None:
    _flask_app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)


def _open_browser(port: int) -> None:
    time.sleep(1.5)
    webbrowser.open(f'http://127.0.0.1:{port}')


def _make_tray_image():
    from create_icon import draw_icon
    return draw_icon(64)


def _shutdown(icon) -> None:
    try:
        icon.stop()
    finally:
        time.sleep(0.2)
        os._exit(0)


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

    threading.Thread(target=_run_flask,    args=(port,), daemon=True).start()
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
    main()
