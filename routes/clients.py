"""Student / client routes."""
import logging
from flask import render_template, request, redirect, url_for, flash
from app import app
from database import get_db, get_all_clients, get_client
from helpers import _enrich_student, _parse_services, _calculate_age, _parse_student_form, _parse_rate, SERVICES, GRADES

log = logging.getLogger(__name__)


@app.route('/clients')
def clients():
    all_students = [_enrich_student(r) for r in get_all_clients()]
    active   = [s for s in all_students if s['active']]
    inactive = [s for s in all_students if not s['active']]
    return render_template('clients.html', clients=active, archived=inactive)


@app.route('/clients/add', methods=['GET', 'POST'])
def add_client():
    if request.method == 'GET':
        return render_template('student_form.html', student=None, services=SERVICES, grades=GRADES)

    try:
        d = _parse_student_form()
    except ValueError:
        flash('Per-session rate must be a number.', 'error')
        return render_template('student_form.html', student=None, services=SERVICES, grades=GRADES)
    if not d['name'] or not d['initials']:
        flash('Name and initials are required.', 'error')
        return render_template('student_form.html', student=d, services=SERVICES, grades=GRADES)

    conn = get_db()
    dup = conn.execute(
        'SELECT id FROM clients WHERE UPPER(initials) = ? AND active = 1',
        (d['initials'],)
    ).fetchone()
    if dup:
        conn.close()
        flash(f'A student with initials "{d["initials"]}" already exists. Initials must be unique.', 'error')
        return render_template('student_form.html', student=d, services=SERVICES, grades=GRADES)

    conn.execute('''
        INSERT INTO clients
            (name, initials, email, phone, school, grade, birthday, diagnosis,
             services, services_other, start_date, end_date, test_date,
             parent1_name, parent2_name, parent_address, parent_city,
             parent_state, parent_zip, parent2_address, parent2_city,
             parent2_state, parent2_zip, parent2_phone, parent2_email,
             bill_to_parent,
             bill_to_custom_name, bill_to_custom_addr, bill_to_custom_city,
             bill_to_custom_state, bill_to_custom_zip,
             intake_complete, roi_complete, notes, hourly_rate)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (d['name'], d['initials'], d['email'], d['phone'],
          d['school'], d['grade'], d['birthday'], d['diagnosis'],
          d['services'], d['services_other'],
          d['start_date'], d['end_date'], d['test_date'],
          d['parent1_name'], d['parent2_name'], d['parent_address'],
          d['parent_city'], d['parent_state'], d['parent_zip'],
          d['parent2_address'], d['parent2_city'], d['parent2_state'], d['parent2_zip'],
          d['parent2_phone'], d['parent2_email'],
          d['bill_to_parent'],
          d['bill_to_custom_name'], d['bill_to_custom_addr'], d['bill_to_custom_city'],
          d['bill_to_custom_state'], d['bill_to_custom_zip'],
          d['intake_complete'], d['roi_complete'], d['notes'], d['hourly_rate']))
    conn.commit()
    conn.close()
    log.info('Student added: %s', d['name'])
    flash(f'Student "{d["name"]}" added.', 'success')
    return redirect(url_for('clients'))


@app.route('/clients/<int:client_id>/edit', methods=['GET', 'POST'])
def edit_client(client_id):
    if request.method == 'GET':
        student = _enrich_student(get_client(client_id))
        if not student:
            flash('Student not found.', 'error')
            return redirect(url_for('clients'))
        return render_template('student_form.html', student=student, services=SERVICES, grades=GRADES)

    try:
        d = _parse_student_form()
    except ValueError:
        student = _enrich_student(get_client(client_id))
        flash('Per-session rate must be a number.', 'error')
        return render_template('student_form.html', student=student, services=SERVICES, grades=GRADES)
    if not d['name'] or not d['initials']:
        flash('Name and initials are required.', 'error')
        d['id'] = client_id
        d['services_list'] = _parse_services(d.get('services'))
        d['age'] = _calculate_age(d.get('birthday'))
        return render_template('student_form.html', student=d, services=SERVICES, grades=GRADES)

    conn = get_db()
    dup = conn.execute(
        'SELECT id FROM clients WHERE UPPER(initials) = ? AND active = 1 AND id != ?',
        (d['initials'], client_id)
    ).fetchone()
    if dup:
        conn.close()
        flash(f'A student with initials "{d["initials"]}" already exists. Initials must be unique.', 'error')
        d['id'] = client_id
        d['services_list'] = _parse_services(d.get('services'))
        d['age'] = _calculate_age(d.get('birthday'))
        return render_template('student_form.html', student=d, services=SERVICES, grades=GRADES)

    conn.execute('''
        UPDATE clients SET
            name=?, initials=?, email=?, phone=?, school=?, grade=?, birthday=?,
            diagnosis=?, services=?, services_other=?, start_date=?, end_date=?,
            test_date=?, parent1_name=?, parent2_name=?, parent_address=?,
            parent_city=?, parent_state=?, parent_zip=?,
            parent2_address=?, parent2_city=?, parent2_state=?, parent2_zip=?,
            parent2_phone=?, parent2_email=?,
            bill_to_parent=?,
            bill_to_custom_name=?, bill_to_custom_addr=?, bill_to_custom_city=?,
            bill_to_custom_state=?, bill_to_custom_zip=?,
            intake_complete=?, roi_complete=?, notes=?, hourly_rate=?
        WHERE id=?
    ''', (d['name'], d['initials'], d['email'], d['phone'],
          d['school'], d['grade'], d['birthday'], d['diagnosis'],
          d['services'], d['services_other'],
          d['start_date'], d['end_date'], d['test_date'],
          d['parent1_name'], d['parent2_name'], d['parent_address'],
          d['parent_city'], d['parent_state'], d['parent_zip'],
          d['parent2_address'], d['parent2_city'], d['parent2_state'], d['parent2_zip'],
          d['parent2_phone'], d['parent2_email'],
          d['bill_to_parent'],
          d['bill_to_custom_name'], d['bill_to_custom_addr'], d['bill_to_custom_city'],
          d['bill_to_custom_state'], d['bill_to_custom_zip'],
          d['intake_complete'], d['roi_complete'], d['notes'], d['hourly_rate'], client_id))
    conn.commit()
    conn.close()
    log.info('Student updated: %s (id=%d)', d['name'], client_id)
    flash(f'Student "{d["name"]}" updated.', 'success')
    return redirect(url_for('clients'))


def _set_client_active(client_id, active, flash_template):
    conn = get_db()
    client = conn.execute('SELECT name FROM clients WHERE id=?', (client_id,)).fetchone()
    if not client:
        conn.close()
        flash('Student not found.', 'error')
        return
    conn.execute('UPDATE clients SET active=? WHERE id=?', (active, client_id))
    conn.commit()
    conn.close()
    flash(flash_template.format(name=client['name']), 'success')


@app.route('/clients/<int:client_id>/archive', methods=['POST'])
def archive_client(client_id):
    _set_client_active(client_id, 0, '"{name}" archived. Restore them from the Archived section.')
    return redirect(url_for('clients'))


@app.route('/clients/<int:client_id>/restore', methods=['POST'])
def restore_client(client_id):
    _set_client_active(client_id, 1, '"{name}" restored to active students.')
    return redirect(url_for('clients'))


@app.route('/clients/<int:client_id>/delete', methods=['POST'])
def delete_client(client_id):
    conn   = get_db()
    client = conn.execute('SELECT name FROM clients WHERE id=?', (client_id,)).fetchone()
    if client:
        invoice_count = conn.execute(
            'SELECT COUNT(*) FROM invoices WHERE client_id=?', (client_id,)
        ).fetchone()[0]
        if invoice_count > 0:
            conn.close()
            flash(
                f'"{client["name"]}" has {invoice_count} invoice(s) and cannot be deleted. '
                'Archive them instead to preserve billing history.',
                'error'
            )
            return redirect(url_for('clients'))
        conn.execute('DELETE FROM clients WHERE id=?', (client_id,))
        conn.commit()
        log.info('Student deleted: %s (id=%d)', client['name'], client_id)
        flash(f'Student "{client["name"]}" deleted.', 'success')
    conn.close()
    return redirect(url_for('clients'))
