"""Invoice routes — create, view, manage, export."""
import calendar as cal_module
import logging
import os
import subprocess
from datetime import datetime

from flask import render_template, request, redirect, url_for, flash, jsonify, Response

from app import app
import config as _config
from database import (
    get_db, get_client, get_all_invoices, get_invoice, get_setting, get_settings_batch,
    get_enabled_calendars, next_invoice_number, month_name,
    toggle_invoice_paid, get_invoice_years, get_annual_summary,
)
from outlook import get_sessions, send_invoice_email
from pdf_generator import build_pdf
from helpers import _parent_bill_name, current_year_month, next_year_month

log = logging.getLogger(__name__)


@app.route('/invoices')
def invoices():
    all_inv = get_all_invoices()
    years   = sorted({i['year'] for i in all_inv}, reverse=True)
    clients = sorted({i['client_name'] for i in all_inv})
    return render_template('invoice_history.html', invoices=all_inv,
                           month_name=month_name, years=years, filter_clients=clients)


@app.route('/invoices/create')
def create_invoice():
    year, month = next_year_month()
    cur_year = current_year_month()[0]
    return render_template('create_invoice.html',
        clients=__import__('database').get_all_clients(active_only=True),
        months=[(i, cal_module.month_name[i]) for i in range(1, 13)],
        years=list(range(cur_year - 2, cur_year + 2)),
        current_month=month,
        current_year=year,
    )


@app.route('/invoices/fetch-sessions', methods=['POST'])
def fetch_sessions():
    data      = request.get_json() or {}
    client_id = data.get('client_id')
    try:
        month = int(data.get('month'))
        year  = int(data.get('year'))
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid month or year.'}), 400

    client = get_client(client_id)
    if not client:
        return jsonify({'error': 'Student not found.'}), 404

    enabled = get_enabled_calendars()
    if not enabled:
        return jsonify({'error': 'No calendars are enabled. Go to Settings > Calendars.'}), 400

    try:
        sessions = get_sessions(client['initials'], month, year, enabled)
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 500

    global_rate = float(get_setting('hourly_rate', '0'))
    rate = float(client['hourly_rate']) if client['hourly_rate'] else global_rate
    for s in sessions:
        s['rate']       = rate
        s['line_total'] = rate
    return jsonify({'sessions': sessions, 'rate': rate})


@app.route('/invoices/generate', methods=['POST'])
def generate_invoice():
    data      = request.get_json() or {}
    client_id = data.get('client_id')
    try:
        month = int(data.get('month'))
        year  = int(data.get('year'))
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid month or year.'}), 400
    sessions = data.get('sessions', [])
    late_fee = data.get('late_fee')
    credit   = data.get('credit')
    force    = data.get('force', False)

    if not sessions:
        return jsonify({'error': 'No sessions selected.'}), 400

    client = get_client(client_id)
    if not client:
        return jsonify({'error': 'Student not found.'}), 404

    conn = get_db()

    if not force:
        existing = conn.execute(
            'SELECT id, invoice_number FROM invoices WHERE client_id=? AND month=? AND year=?',
            (client_id, month, year)
        ).fetchone()
        if existing:
            conn.close()
            return jsonify({
                'duplicate':             True,
                'existing_invoice_id':   existing['id'],
                'existing_number':       existing['invoice_number'],
            })

    cfg = get_settings_batch(('hourly_rate', 'business_name', 'business_title',
                               'business_email', 'business_phone', 'business_address',
                               'business_city', 'business_state', 'business_zip', 'venmo_handle'))

    rate            = float(cfg.get('hourly_rate', '0'))
    total_hours     = round(sum(s['duration_hours'] for s in sessions), 2)
    late_fee_amount = round(float(late_fee['amount']), 2) if late_fee else 0
    credit_amount   = round(float(credit['amount']),   2) if credit   else 0
    total_amount    = round(len(sessions) * rate + late_fee_amount - credit_amount, 2)
    inv_number      = next_invoice_number(conn)
    now             = datetime.now()

    cursor = conn.execute('''
        INSERT INTO invoices
            (invoice_number, client_id, month, year, total_hours, total_amount, hourly_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (inv_number, client_id, month, year, total_hours, total_amount, rate))
    invoice_id = cursor.lastrowid

    lines_for_pdf = []
    for s in sessions:
        conn.execute('''
            INSERT INTO invoice_lines
                (invoice_id, session_date, start_time, end_time, duration_hours, rate, line_total, line_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'session')
        ''', (invoice_id, s['date_display'], s['start_time'], s['end_time'],
              s['duration_hours'], rate, rate))
        lines_for_pdf.append({
            'line_type':      'session',
            'session_date':   s['date_display'],
            'start_time':     s['start_time'],
            'end_time':       s['end_time'],
            'duration_hours': s['duration_hours'],
            'rate':           rate,
            'line_total':     rate,
        })

    if late_fee:
        note = (late_fee.get('note') or 'Late fee').strip()
        conn.execute('''
            INSERT INTO invoice_lines
                (invoice_id, session_date, start_time, end_time, duration_hours, rate, line_total, line_type, note)
            VALUES (?, '', '', '', 0, 0, ?, 'late_fee', ?)
        ''', (invoice_id, late_fee_amount, note))
        lines_for_pdf.append({'line_type': 'late_fee', 'note': note, 'line_total': late_fee_amount})

    if credit:
        note = (credit.get('note') or 'Credit').strip()
        conn.execute('''
            INSERT INTO invoice_lines
                (invoice_id, session_date, start_time, end_time, duration_hours, rate, line_total, line_type, note)
            VALUES (?, '', '', '', 0, 0, ?, 'credit', ?)
        ''', (invoice_id, credit_amount, note))
        lines_for_pdf.append({'line_type': 'credit', 'note': note, 'line_total': credit_amount})

    conn.commit()
    log.info('Invoice %s created for client_id=%s (%s/%s) total=$%.2f',
             inv_number, client_id, month, year, total_amount)

    invoice_dict = {
        'invoice_number': inv_number,
        'client_name':    client['name'],
        'student_name':   client['name'],
        'month':          month,
        'year':           year,
        'hourly_rate':    rate,
        'total_hours':    total_hours,
        'total_amount':   total_amount,
        'invoice_date':   f'{now.month}/{now.day}/{now.year}',
    }
    business = {
        'name':         cfg.get('business_name',    'Your Name'),
        'title':        cfg.get('business_title',   ''),
        'email':        cfg.get('business_email',   ''),
        'phone':        cfg.get('business_phone',   ''),
        'address':      cfg.get('business_address', ''),
        'city':         cfg.get('business_city',    ''),
        'state':        cfg.get('business_state',   ''),
        'zip':          cfg.get('business_zip',     ''),
        'venmo_handle': cfg.get('venmo_handle',     ''),
    }
    _bill_to = client['bill_to_parent'] or '1'
    if _bill_to == 'custom':
        parent = {
            'name':    client['bill_to_custom_name']  or '',
            'address': client['bill_to_custom_addr']  or '',
            'city':    client['bill_to_custom_city']  or '',
            'state':   client['bill_to_custom_state'] or '',
            'zip':     client['bill_to_custom_zip']   or '',
        }
    elif _bill_to == '2' and client['parent2_name']:
        parent = {
            'name':    client['parent2_name']    or '',
            'address': client['parent2_address'] or '',
            'city':    client['parent2_city']    or '',
            'state':   client['parent2_state']   or '',
            'zip':     client['parent2_zip']     or '',
        }
    else:
        parent = {
            'name':    _parent_bill_name(dict(client)),
            'address': client['parent_address'] or '',
            'city':    client['parent_city']    or '',
            'state':   client['parent_state']   or '',
            'zip':     client['parent_zip']     or '',
        }

    try:
        pdf_path = build_pdf(invoice_dict, lines_for_pdf, business, parent,
                             pdf_folder=_config.load()['pdf_folder'])
        conn.execute('UPDATE invoices SET pdf_path=? WHERE id=?', (pdf_path, invoice_id))
        conn.commit()
    except Exception as e:
        conn.close()
        log.error('PDF generation failed for invoice %s: %s', inv_number, e)
        return jsonify({'error': f'Invoice saved but PDF failed: {e}'}), 500

    conn.close()
    return jsonify({'success': True, 'invoice_id': invoice_id, 'pdf_path': pdf_path})


@app.route('/invoices/<int:invoice_id>')
def invoice_detail(invoice_id):
    inv, lines = get_invoice(invoice_id)
    if not inv:
        flash('Invoice not found.', 'error')
        return redirect(url_for('invoices'))
    from helpers import _enrich_student
    client = _enrich_student(get_client(inv['client_id']))
    return render_template('invoice_detail.html', inv=inv, lines=lines,
                           client=client, month_name=month_name)


@app.route('/invoices/<int:invoice_id>/toggle-paid', methods=['POST'])
def toggle_paid(invoice_id):
    new_paid = toggle_invoice_paid(invoice_id)
    if new_paid is None:
        return jsonify({'error': 'Invoice not found.'}), 404
    return jsonify({'paid': bool(new_paid)})


@app.route('/summary')
@app.route('/summary/<int:year>')
def annual_summary(year=None):
    years = get_invoice_years()
    if year is None:
        year = years[0] if years else datetime.now().year
    data = get_annual_summary(year)
    return render_template('annual_summary.html',
        year=year, years=years, month_name=month_name, **data)


@app.route('/summary/<int:year>/export.csv')
def export_summary_csv(year):
    import csv, io
    conn = get_db()
    rows = conn.execute('''
        SELECT i.invoice_number, c.name AS student, i.month, i.year,
               i.total_hours, i.total_amount, i.hourly_rate,
               CASE WHEN i.paid=1 THEN 'Paid' ELSE 'Unpaid' END AS status,
               i.paid_at, i.created_at
        FROM invoices i JOIN clients c ON c.id = i.client_id
        WHERE i.year=? ORDER BY i.month, c.name
    ''', (year,)).fetchall()
    conn.close()

    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow(['Invoice #', 'Student', 'Month', 'Year', 'Hours', 'Amount',
                'Rate', 'Status', 'Paid Date', 'Created'])
    for r in rows:
        w.writerow([r['invoice_number'], r['student'],
                    cal_module.month_name[r['month']], r['year'],
                    r['total_hours'], r['total_amount'], r['hourly_rate'],
                    r['status'], r['paid_at'] or '', r['created_at'][:10]])
    return Response(buf.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=cadence_{year}.csv'})


@app.route('/invoices/<int:invoice_id>/delete', methods=['POST'])
def delete_invoice(invoice_id):
    conn = get_db()
    inv  = conn.execute('SELECT invoice_number FROM invoices WHERE id=?', (invoice_id,)).fetchone()
    if inv:
        conn.execute('DELETE FROM invoice_lines WHERE invoice_id=?', (invoice_id,))
        conn.execute('DELETE FROM invoices WHERE id=?', (invoice_id,))
        conn.commit()
        log.info('Invoice %s deleted', inv['invoice_number'])
        flash(f'Invoice {inv["invoice_number"]} deleted.', 'success')
    conn.close()
    return redirect(url_for('invoices'))


@app.route('/invoices/<int:invoice_id>/open-pdf', methods=['POST'])
def open_pdf(invoice_id):
    inv, _ = get_invoice(invoice_id)
    if not inv or not inv['pdf_path']:
        return jsonify({'error': 'PDF not found. Try regenerating the invoice.'}), 404
    try:
        os.startfile(inv['pdf_path'])
        return jsonify({'success': True})
    except (FileNotFoundError, OSError):
        return jsonify({'error': 'PDF not found. Try regenerating the invoice.'}), 404


@app.route('/invoices/<int:invoice_id>/open-folder', methods=['POST'])
def open_folder(invoice_id):
    inv, _ = get_invoice(invoice_id)
    if not inv or not inv['pdf_path']:
        return jsonify({'error': 'Folder not found.'}), 404
    try:
        subprocess.Popen(['explorer', os.path.dirname(inv['pdf_path'])])
        return jsonify({'success': True})
    except OSError:
        return jsonify({'error': 'Folder not found.'}), 404


@app.route('/invoices/<int:invoice_id>/send-email', methods=['POST'])
def send_email(invoice_id):
    inv, _ = get_invoice(invoice_id)
    if not inv:
        return jsonify({'error': 'Invoice not found.'}), 404
    if not inv['pdf_path']:
        return jsonify({'error': 'PDF not found. Open the invoice to regenerate it.'}), 404

    client = get_client(inv['client_id'])
    if not client or not client['email']:
        return jsonify({'error': 'This student has no email address. Add one in Students.'}), 400

    cfg    = get_settings_batch(('business_name', 'business_title', 'business_phone', 'business_email'))
    period = month_name(inv['month'], inv['year'])
    subject = f"Invoice {inv['invoice_number']} \u2013 {period}"
    body = (
        f"Dear {_parent_bill_name(dict(client))},\n\n"
        f"Please find attached your invoice for {period}.\n\n"
        f"Invoice #:  {inv['invoice_number']}\n"
        f"Student:    {client['name']}\n"
        f"Amount:     ${inv['total_amount']:,.2f}\n\n"
        f"Thank you for your continued trust in my services. "
        f"Please don't hesitate to reach out with any questions.\n\n"
        f"Best regards,\n"
        f"{cfg.get('business_name', '')}\n"
        f"{cfg.get('business_title', '')}\n"
        f"{cfg.get('business_phone', '')}\n"
        f"{cfg.get('business_email', '')}"
    )

    try:
        send_invoice_email(client['email'], subject, body, inv['pdf_path'])
        log.info('Invoice %s emailed to %s', inv['invoice_number'], client['email'])
        return jsonify({'success': True})
    except Exception as e:
        log.error('Email send failed for invoice %s: %s', inv['invoice_number'], e)
        return jsonify({'error': f'Could not send email: {e}'}), 500
