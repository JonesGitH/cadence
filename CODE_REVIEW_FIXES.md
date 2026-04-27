# Cadence Code Review Fix Plan

This file turns the review findings into an implementation checklist. The recommended order is to fix the P1 items first, add the matching tests, then move through the P2 cleanup.

## 1. Calendar Default Is Never Saved

**Files:** `templates/settings.html`, `routes/settings.py`

**Problem:** The form posts one field named `default_cal`, but the route checks for `default_<id>`, so every calendar default gets cleared.

**Fix:**

- Keep the template as-is with `name="default_cal"`.
- In `save_calendars()`, read `default_cal = request.form.get('default_cal')`.
- Set `is_default = 1 if str(cal["id"]) == default_cal else 0`.
- Consider forcing the default calendar to be enabled when selected, or rejecting a disabled default.

**Test to add:**

- Seed two calendars.
- POST `/settings/calendars/save` with `default_cal` set to the second calendar id.
- Assert exactly one row has `is_default = 1`.

## 2. Nested Microsoft 365 Disconnect Form

**File:** `templates/settings.html`

**Problem:** The Disconnect form is nested inside the Save Microsoft 365 settings form, which is invalid HTML and can submit the wrong action.

**Fix:**

- Close the `save_graph_settings` form before rendering the disconnect form.
- Put Connect/Disconnect controls outside the save form, or use separate sibling forms.
- Keep the Connect button as `type="button"` because JavaScript starts the device flow.

**Test to add:**

- Render `/settings` while connected is true.
- Assert the HTML does not contain a `<form>` inside another `<form>` in the Microsoft 365 section.

## 3. Graph Calendar Failures Hidden As Empty Results

**File:** `outlook.py`

**Problem:** `_scan_calendars()` catches `RuntimeError` per calendar and returns an empty list. If Graph auth expires or the network fails, users see “no sessions” instead of a reconnect/error message.

**Fix:**

- Let auth/connectivity failures bubble up when all calendar fetches fail.
- Optionally collect per-calendar errors and only degrade gracefully when at least one calendar succeeds.
- For `not_connected`, expired token, and no client id states, return a clear `RuntimeError` message to callers.

**Test to add:**

- Mock `_fetch_events()` to raise `RuntimeError("Microsoft 365 session expired...")`.
- Call `get_sessions()` with one enabled calendar.
- Assert the RuntimeError is raised and not converted to `[]`.

## 4. Invoice Detail Ignores Selected Bill-To

**Files:** `templates/invoice_detail.html`, optionally `helpers.py`

**Problem:** The invoice detail page always displays Parent 1/Parent 2 combined with Parent 1 address. It does not use `bill_to_parent` or custom bill-to fields, so it can disagree with the PDF.

**Fix:**

- Extract bill-to selection into a shared helper, for example `resolve_bill_to(client)`.
- Use that helper in both `routes/invoices.py` PDF generation and `invoice_detail.html`.
- Pass `bill_to` into the template from `invoice_detail()`.
- Render `bill_to.name`, `bill_to.address`, `bill_to.city`, `bill_to.state`, and `bill_to.zip`.

**Test to add:**

- Seed a client with `bill_to_parent = 'custom'`.
- Create an invoice.
- GET `/invoices/<id>`.
- Assert the custom bill-to name/address appear and Parent 1 address does not.

## 5. Email Recipient And Greeting Ignore Bill-To

**Files:** `routes/invoices.py`, `helpers.py`, database/schema if adding custom payer email

**Problem:** Email sending always uses `client.email` and greets `_parent_bill_name()`. Parent 2 and custom bill-to choices are ignored.

**Fix:**

- Reuse the same `resolve_bill_to(client)` helper.
- Include an email field in the resolved bill-to result.
- For Parent 1 use `client.email`.
- For Parent 2 use `client.parent2_email`.
- For custom bill-to, add `bill_to_custom_email` if custom email delivery is needed; otherwise fall back with a clear UI warning.
- Update the disabled/enabled logic in `invoice_detail.html` so “Send via Email” reflects the selected recipient.

**Test to add:**

- Seed a client with `bill_to_parent = '2'`, `parent2_email`, and a different Parent 1 email.
- Mock `send_invoice_email`.
- POST `/invoices/<id>/send-email`.
- Assert email is sent to Parent 2 email and the greeting uses Parent 2 name.

## 6. Deleting Students With Invoices Can 500

**File:** `routes/clients.py`

**Problem:** With SQLite foreign keys enabled, deleting a client that has invoices can raise `sqlite3.IntegrityError`.

**Fix Options:**

- Preferred: block deletion if invoices exist and tell the user to archive instead.
- Alternative: implement cascading delete intentionally, including invoices and invoice lines, but this is risky for billing history.

**Recommended Fix:**

- Before `DELETE FROM clients`, query `SELECT COUNT(*) FROM invoices WHERE client_id = ?`.
- If count is greater than 0, flash a friendly error and do not delete.
- Keep archive as the safe path.

**Test to add:**

- Seed a client and invoice.
- POST `/clients/<id>/delete`.
- Assert response redirects without 500.
- Assert the client still exists and a flash message says to archive instead.

## 7. Numeric JSON Fields Can Crash Invoice Generation

**File:** `routes/invoices.py`

**Problem:** `float(late_fee['amount'])`, `float(credit['amount'])`, and rate parsing can raise exceptions from malformed JSON.

**Fix:**

- Add a small helper like `_parse_money(value, label)` or `_coerce_amount`.
- Validate `late_fee` and `credit` shape before using keys.
- Return `400` JSON errors for invalid amount, negative amount, or missing amount.
- Validate `sessions[*].duration_hours` as numeric too, since the frontend sends session data back to the server.

**Test to add:**

- POST `/invoices/generate` with `late_fee: {"amount": "abc"}`.
- Assert `400` and a helpful JSON error.
- POST with malformed session duration and assert `400`.

## 8. Student Form Rate Parsing Can 500

**File:** `helpers.py`, `routes/clients.py`

**Problem:** `_parse_student_form()` directly casts `hourly_rate` with `float()`.

**Fix:**

- Do not cast inside `_parse_student_form()` without validation.
- Either:
  - return the raw string and validate in routes, or
  - catch `ValueError` and return an error object/message.
- In `add_client()` and `edit_client()`, re-render the form with a flash error if the rate is invalid.

**Test to add:**

- POST `/clients/add` with valid name/initials and `hourly_rate=abc`.
- Assert status is `200`, no client inserted, and the form shows a validation error.

## 9. Excel Import Omits New Billing Fields

**Files:** `routes/settings.py`, possibly `database.py`

**Problem:** Manual student entry supports Parent 2 phone/email and bill-to fields, but the Excel template/import does not.

**Fix:**

- Add these columns to the template:
  - `parent2_phone`
  - `parent2_email`
  - `bill_to_parent`
  - `bill_to_custom_name`
  - `bill_to_custom_addr`
  - `bill_to_custom_city`
  - `bill_to_custom_state`
  - `bill_to_custom_zip`
  - optionally `bill_to_custom_email`
- Add the same keys to `COL_KEYS`.
- Include them in the import `INSERT`.
- Validate `bill_to_parent` to only allow `1`, `2`, or `custom`; default to `1`.

**Test to add:**

- Generate the template and assert the new headers exist.
- Import a workbook row with `bill_to_parent = custom`.
- Assert the imported client has the custom bill-to fields.

## 10. Generated Artifacts Are Unignored

**File:** `.gitignore`

**Problem:** Generated deck/runtime artifacts are untracked and easy to commit accidentally: `node_modules/`, `scratch/`, `output/`, `package.json`, and `src/cadence-marketing.mjs`.

**Fix:**

- Add generated presentation paths to `.gitignore`, for example:

```gitignore
node_modules/
scratch/
output/
package.json
src/cadence-marketing.mjs
```

- If `package.json` may become a real project file later, ignore only the presentation workspace by moving deck generation into a subfolder like `marketing_deck/` and ignoring that folder instead.

**Test/verification:**

- Run `git status --short`.
- Confirm generated artifacts no longer appear as untracked files.

## 11. Cross-Cutting Improvement: CSRF Protection

**Files:** `app.py`, forms/templates, JavaScript fetch calls

**Problem:** Most mutating routes use POST without CSRF protection. The app is local, so risk is lower, but a browser page can still send requests to `127.0.0.1:5000`.

**Fix:**

- Add CSRF support, preferably via Flask-WTF or a small custom session token.
- Include the token in every HTML form.
- Include the token header in JavaScript `fetch()` POST requests.
- Validate the token in a `before_request` hook for mutating methods.

**Test to add:**

- POST to a mutating route without token and assert `400` or `403`.
- POST with token and assert normal behavior.

## Test Runner Notes

The test runner issue is resolved on this machine.

Working command:

```powershell
& 'C:\Users\Alex\AppData\Local\Programs\Python\Python314\python.exe' -m pytest -q -p no:cacheprovider
```

Current result:

```text
27 passed in 3.85s
```

The passing tests do not cover the findings above yet. Add targeted regression tests while fixing each item.
