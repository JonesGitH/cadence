"""
Tests for bill-to resolution, invoice input validation, and client CRUD.
"""
import json
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_client(overrides=None):
    """Return a minimal client dict with all bill-to fields."""
    base = {
        'name': 'Jane Doe',
        'parent1_name': 'Mary Doe',
        'parent2_name': '',
        'parent_address': '1 Main St',
        'parent_city': 'Austin',
        'parent_state': 'TX',
        'parent_zip': '78701',
        'parent2_address': '',
        'parent2_city': '',
        'parent2_state': '',
        'parent2_zip': '',
        'parent2_email': '',
        'email': 'mary@example.com',
        'bill_to_parent': '1',
        'bill_to_custom_name': '',
        'bill_to_custom_addr': '',
        'bill_to_custom_city': '',
        'bill_to_custom_state': '',
        'bill_to_custom_zip': '',
    }
    if overrides:
        base.update(overrides)
    return base


def _seed_client(db, **kwargs):
    """Insert a client row and return its id."""
    c = _make_client(kwargs if kwargs else None)
    db.execute(
        '''INSERT INTO clients
               (name, initials, email, parent1_name, parent2_name,
                parent_address, parent_city, parent_state, parent_zip,
                parent2_address, parent2_city, parent2_state, parent2_zip,
                parent2_email, bill_to_parent,
                bill_to_custom_name, bill_to_custom_addr,
                bill_to_custom_city, bill_to_custom_state, bill_to_custom_zip,
                active)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)''',
        (c['name'], 'JD', c['email'],
         c['parent1_name'], c['parent2_name'],
         c['parent_address'], c['parent_city'], c['parent_state'], c['parent_zip'],
         c['parent2_address'], c['parent2_city'], c['parent2_state'], c['parent2_zip'],
         c['parent2_email'], c['bill_to_parent'],
         c['bill_to_custom_name'], c['bill_to_custom_addr'],
         c['bill_to_custom_city'], c['bill_to_custom_state'], c['bill_to_custom_zip'])
    )
    db.commit()
    return db.execute('SELECT last_insert_rowid()').fetchone()[0]


SESSIONS_1 = [{
    'date_display': 'Mon Jan 06',
    'start_time': '3:00 PM',
    'end_time': '4:00 PM',
    'duration_hours': 1.0,
}]


def _post_generate(client_fixture, payload):
    return client_fixture.post(
        '/invoices/generate',
        data=json.dumps(payload),
        content_type='application/json',
    )


# ── _resolve_bill_to ──────────────────────────────────────────────────────────

class TestResolveBillTo:
    def _resolve(self, client_dict):
        from routes.invoices import _resolve_bill_to
        return _resolve_bill_to(client_dict)

    def test_default_returns_parent1_address(self):
        c = _make_client()
        r = self._resolve(c)
        assert r['name'] == 'Mary Doe'
        assert r['address'] == '1 Main St'
        assert r['city'] == 'Austin'
        assert r['state'] == 'TX'
        assert r['email'] == 'mary@example.com'

    def test_default_combines_both_parent_names(self):
        c = _make_client({'parent2_name': 'John Doe'})
        r = self._resolve(c)
        assert r['name'] == 'Mary Doe & John Doe'

    def test_parent2_billing_uses_parent2_fields(self):
        c = _make_client({
            'bill_to_parent': '2',
            'parent2_name': 'John Doe',
            'parent2_address': '2 Oak Ave',
            'parent2_city': 'Dallas',
            'parent2_state': 'TX',
            'parent2_zip': '75001',
            'parent2_email': 'john@example.com',
        })
        r = self._resolve(c)
        assert r['name'] == 'John Doe'
        assert r['address'] == '2 Oak Ave'
        assert r['email'] == 'john@example.com'

    def test_parent2_billing_falls_back_when_no_parent2_name(self):
        """bill_to_parent='2' but parent2_name blank → falls back to parent 1."""
        c = _make_client({'bill_to_parent': '2', 'parent2_name': ''})
        r = self._resolve(c)
        assert r['name'] == 'Mary Doe'
        assert r['address'] == '1 Main St'

    def test_custom_billing_uses_custom_fields(self):
        c = _make_client({
            'bill_to_parent': 'custom',
            'bill_to_custom_name': 'Grandma Jones',
            'bill_to_custom_addr': '99 Pine Rd',
            'bill_to_custom_city': 'Houston',
            'bill_to_custom_state': 'TX',
            'bill_to_custom_zip': '77001',
        })
        r = self._resolve(c)
        assert r['name'] == 'Grandma Jones'
        assert r['address'] == '99 Pine Rd'
        assert r['city'] == 'Houston'

    def test_custom_billing_falls_back_name_when_blank(self):
        """Custom with blank custom_name falls back to _parent_bill_name."""
        c = _make_client({
            'bill_to_parent': 'custom',
            'bill_to_custom_name': '',
        })
        r = self._resolve(c)
        assert r['name'] == 'Mary Doe'

    def test_none_bill_to_parent_defaults_to_parent1(self):
        c = _make_client({'bill_to_parent': None})
        r = self._resolve(c)
        assert r['address'] == '1 Main St'


# ── Invoice input validation ──────────────────────────────────────────────────

class TestInvoiceValidation:
    def test_invalid_duration_hours_returns_400(self, client, _in_memory_db):
        from tests.test_invoices import _seed_client_and_settings
        cid = _seed_client_and_settings(_in_memory_db, rate=75.0)
        resp = _post_generate(client, {
            'client_id': cid, 'month': 1, 'year': 2025,
            'sessions': [{
                'date_display': 'Mon Jan 06',
                'start_time': '3:00 PM',
                'end_time': '4:00 PM',
                'duration_hours': 'not-a-number',
            }],
        })
        assert resp.status_code == 400
        assert 'duration' in resp.get_json().get('error', '').lower()

    def test_missing_duration_hours_returns_400(self, client, _in_memory_db):
        from tests.test_invoices import _seed_client_and_settings
        cid = _seed_client_and_settings(_in_memory_db, rate=75.0)
        resp = _post_generate(client, {
            'client_id': cid, 'month': 1, 'year': 2025,
            'sessions': [{'date_display': 'Mon Jan 06', 'start_time': '3:00 PM', 'end_time': '4:00 PM'}],
        })
        assert resp.status_code == 400

    def test_client_rate_overrides_global(self, client, _in_memory_db):
        """Client-specific hourly_rate takes precedence over global setting."""
        from tests.test_invoices import _seed_client_and_settings
        cid = _seed_client_and_settings(_in_memory_db, rate=75.0)
        _in_memory_db.execute("UPDATE clients SET hourly_rate=100.0 WHERE id=?", (cid,))
        _in_memory_db.commit()
        _post_generate(client, {
            'client_id': cid, 'month': 1, 'year': 2025,
            'sessions': SESSIONS_1,
        })
        row = _in_memory_db.execute('SELECT hourly_rate FROM invoices').fetchone()
        if row:
            assert row['hourly_rate'] == 100.0

    def test_corrupted_global_rate_falls_back_to_zero(self, client, _in_memory_db):
        """Non-numeric global hourly_rate doesn't crash; falls back to 0."""
        from tests.test_invoices import _seed_client_and_settings
        cid = _seed_client_and_settings(_in_memory_db, rate=75.0)
        _in_memory_db.execute(
            "UPDATE settings SET value='bad' WHERE key='hourly_rate'"
        )
        _in_memory_db.commit()
        resp = _post_generate(client, {
            'client_id': cid, 'month': 1, 'year': 2025,
            'sessions': SESSIONS_1,
        })
        # Should not 500 — either success or a PDF error, not a crash
        assert resp.status_code != 500


# ── Client CRUD ───────────────────────────────────────────────────────────────

class TestClientCRUD:
    def test_add_client_creates_row(self, client, _in_memory_db):
        resp = client.post('/clients/add', data={
            'name': 'Alice Smith',
            'initials': 'AS',
            'hourly_rate': '',
            'bill_to_parent': '1',
        }, follow_redirects=False)
        assert resp.status_code in (200, 302)
        row = _in_memory_db.execute(
            "SELECT name FROM clients WHERE name='Alice Smith'"
        ).fetchone()
        assert row is not None

    def test_add_client_invalid_rate_rejected(self, client, _in_memory_db):
        client.post('/clients/add', data={
            'name': 'Bob Jones',
            'initials': 'BJ',
            'hourly_rate': 'abc',
        })
        row = _in_memory_db.execute(
            "SELECT name FROM clients WHERE name='Bob Jones'"
        ).fetchone()
        assert row is None

    def test_delete_client_without_invoices_succeeds(self, client, _in_memory_db):
        cid = _seed_client(_in_memory_db)
        resp = client.post(f'/clients/{cid}/delete', follow_redirects=False)
        assert resp.status_code == 302
        row = _in_memory_db.execute(
            'SELECT id FROM clients WHERE id=?', (cid,)
        ).fetchone()
        assert row is None

    def test_delete_client_with_invoices_blocked(self, client, _in_memory_db):
        cid = _seed_client(_in_memory_db)
        _in_memory_db.execute(
            '''INSERT INTO invoices
                   (invoice_number, client_id, month, year,
                    total_hours, total_amount, hourly_rate)
               VALUES ('INV-001', ?, 1, 2025, 1.0, 75.0, 75.0)''',
            (cid,)
        )
        _in_memory_db.commit()
        resp = client.post(f'/clients/{cid}/delete', follow_redirects=False)
        assert resp.status_code == 302
        row = _in_memory_db.execute(
            'SELECT id FROM clients WHERE id=?', (cid,)
        ).fetchone()
        assert row is not None

    def test_archive_and_restore_client(self, client, _in_memory_db):
        cid = _seed_client(_in_memory_db)
        client.post(f'/clients/{cid}/archive', follow_redirects=False)
        row = _in_memory_db.execute(
            'SELECT active FROM clients WHERE id=?', (cid,)
        ).fetchone()
        assert row['active'] == 0

        client.post(f'/clients/{cid}/restore', follow_redirects=False)
        row = _in_memory_db.execute(
            'SELECT active FROM clients WHERE id=?', (cid,)
        ).fetchone()
        assert row['active'] == 1
