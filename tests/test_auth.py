"""
Tests for authentication gate and redirect-safety rules.

Covers:
  - Unauthenticated request is redirected to /unlock
  - /unlock with correct password sets session and redirects to dashboard
  - /unlock with bad password returns error
  - Open-redirect blocked: external URL → dashboard
  - Open-redirect blocked: protocol-relative URL → dashboard
  - Valid local path is honoured
  - Expired password forces /change-password redirect
  - /change-password enforces history, length, and confirmation checks
"""
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _set_password(password: str = 'TestPass1!'):
    """Insert a password into the in-memory DB directly."""
    import database as db
    db.set_new_password(password)


# ── Auth gate ─────────────────────────────────────────────────────────────────

def test_unauthenticated_redirects_to_unlock(client):
    """A page that requires auth should redirect to /unlock when no session."""
    import app as app_module
    flask_app = app_module.app
    _set_password()

    with flask_app.test_client() as anon:
        resp = anon.get('/clients')
    assert resp.status_code == 302
    assert '/unlock' in resp.headers['Location']


def test_no_password_set_allows_access(client):
    """/clients should be accessible without a session when no password is set."""
    resp = client.get('/clients')
    assert resp.status_code == 200


# ── /unlock ───────────────────────────────────────────────────────────────────

def test_unlock_correct_password(client):
    _set_password('MySecret99')
    import app as app_module
    flask_app = app_module.app

    with flask_app.test_client() as c:
        resp = c.post('/unlock', data={'password': 'MySecret99'}, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers['Location'] in ('/', 'http://localhost/')


def test_unlock_wrong_password(client):
    _set_password('MySecret99')
    import app as app_module
    flask_app = app_module.app

    with flask_app.test_client() as c:
        resp = c.post('/unlock', data={'password': 'wrongpassword'},
                      follow_redirects=False)
    assert resp.status_code == 200
    assert b'Incorrect password' in resp.data


# ── Open-redirect safety ──────────────────────────────────────────────────────

@pytest.mark.parametrize('bad_next', [
    'http://evil.com',
    'https://evil.com/steal',
    '//evil.com',
    '//evil.com/path',
])
def test_open_redirect_blocked(client, bad_next):
    _set_password('Safe123!!')
    import app as app_module
    flask_app = app_module.app

    with flask_app.test_client() as c:
        resp = c.post('/unlock',
                      data={'password': 'Safe123!!', 'next': bad_next},
                      follow_redirects=False)
    # Must redirect, but NOT to the bad URL
    assert resp.status_code == 302
    location = resp.headers['Location']
    assert 'evil.com' not in location


def test_valid_local_next_honoured(client):
    _set_password('Safe123!!')
    import app as app_module
    flask_app = app_module.app

    with flask_app.test_client() as c:
        resp = c.post('/unlock',
                      data={'password': 'Safe123!!', 'next': '/invoices'},
                      follow_redirects=False)
    assert resp.status_code == 302
    assert '/invoices' in resp.headers['Location']


# ── Force-change on expiry ────────────────────────────────────────────────────

def test_expired_password_forces_change(client):
    """If the password is older than 180 days the gate must redirect to /change-password."""
    import database as db
    import json
    from datetime import datetime, timedelta, timezone

    _set_password('ExpiredPW1')
    # Back-date the password change timestamp by 181 days
    old_date = (datetime.now(timezone.utc) - timedelta(days=181)).isoformat()
    db.set_setting('security_password_changed_at', old_date)

    import app as app_module
    flask_app = app_module.app

    with flask_app.test_client() as c:
        # Authenticate successfully first
        c.post('/unlock', data={'password': 'ExpiredPW1'}, follow_redirects=False)
        # Any subsequent page should redirect to change-password
        resp = c.get('/clients', follow_redirects=False)
    assert resp.status_code == 302
    assert 'change-password' in resp.headers['Location']


# ── /change-password validation ───────────────────────────────────────────────

def test_change_password_too_short(client):
    _set_password('Original1!')
    resp = client.post('/change-password', data={
        'current_password': 'Original1!',
        'new_password':     'short',
        'confirm_password': 'short',
    })
    assert resp.status_code == 200
    assert b'8 characters' in resp.data


def test_change_password_mismatch(client):
    _set_password('Original1!')
    resp = client.post('/change-password', data={
        'current_password': 'Original1!',
        'new_password':     'NewPassword1!',
        'confirm_password': 'Different1!',
    })
    assert resp.status_code == 200
    assert b'do not match' in resp.data


def test_change_password_history_reuse(client):
    _set_password('Original1!')
    resp = client.post('/change-password', data={
        'current_password': 'Original1!',
        'new_password':     'Original1!',
        'confirm_password': 'Original1!',
    })
    assert resp.status_code == 200
    assert b'used before' in resp.data


def test_change_password_success(client):
    _set_password('Original1!')
    resp = client.post('/change-password', data={
        'current_password': 'Original1!',
        'new_password':     'NewPassword1!',
        'confirm_password': 'NewPassword1!',
    }, follow_redirects=False)
    assert resp.status_code == 302
    import database as db
    assert db.verify_password('NewPassword1!')
    assert not db.verify_password('Original1!')
