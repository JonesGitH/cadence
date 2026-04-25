"""
Shared pytest fixtures for Cadence tests.

Each test function gets:
  - an isolated in-memory SQLite database (no file I/O)
  - a Flask test client with TESTING=True
  - session pre-seeded as authenticated (so auth gate is bypassed by default)

Design note — stable proxy pattern
------------------------------------
database.py opens a new connection per call (get_db()) and closes it when
done.  Route modules import get_db by name:

    from database import get_db   # captures a reference at import time

Monkeypatching database.get_db per test doesn't fix those captured references.
Instead we install a single *stable* callable (_DB_PROXY) once for the whole
session and simply swap the underlying connection between tests.  Because the
proxy object never changes, every import of get_db — whether from database.py
or from a route module — always calls through to whatever connection is
currently active.

Closing the connection per helper call (as production code does) would destroy
the shared in-memory DB, so _NoCloseConn makes close() a no-op.
"""
import os
import sys
import sqlite3
import pytest

# ── Ensure repo root is importable ───────────────────────────────────────────
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

# Tests use the repo directory as both bundle and data dir
os.environ.setdefault('CADENCE_BUNDLE_DIR', _REPO)
os.environ.setdefault('CADENCE_DATA_DIR',   _REPO)


# ── Connection wrapper ────────────────────────────────────────────────────────

class _NoCloseConn:
    """Proxy for sqlite3.Connection whose close() is a no-op in tests."""

    def __init__(self, raw: sqlite3.Connection):
        self._raw = raw

    def close(self):
        """No-op — prevents helpers from destroying the shared test conn."""

    def really_close(self):
        self._raw.close()

    def __getattr__(self, name):
        return getattr(self._raw, name)

    def __enter__(self):
        return self._raw.__enter__()

    def __exit__(self, *args):
        return self._raw.__exit__(*args)


# ── Stable get_db proxy (installed once, swapped per test) ───────────────────

class _GetDbProxy:
    """
    Callable installed in place of database.get_db for the whole test session.

    Because it is the *same object* for every test, all callers that did
    `from database import get_db` will call through here regardless of when
    the import happened.  We update `.conn` before each test.
    """
    def __init__(self):
        self.conn = None

    def __call__(self):
        return self.conn


_DB_PROXY = _GetDbProxy()
_PROXY_INSTALLED = False


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _in_memory_db():
    """Fresh in-memory SQLite for every test; no file I/O."""
    global _PROXY_INSTALLED

    import database as db_module

    # Install proxy once for the whole process (stays in place across tests)
    if not _PROXY_INSTALLED:
        db_module.get_db = _DB_PROXY
        _PROXY_INSTALLED = True

    # Build a fresh in-memory connection with the full schema
    raw = sqlite3.connect(':memory:', check_same_thread=False)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys = ON")
    wrapped = _NoCloseConn(raw)

    _DB_PROXY.conn = wrapped
    db_module.init_db()

    yield wrapped

    _DB_PROXY.conn = None
    wrapped.really_close()


@pytest.fixture()
def client(_in_memory_db):
    """Flask test client with TESTING=True and a pre-authenticated session."""
    import app as app_module   # cached after first import; proxy already live

    flask_app = app_module.app
    flask_app.config['TESTING'] = True

    with flask_app.test_client() as c:
        with c.session_transaction() as sess:
            sess['authenticated'] = True
        yield c
