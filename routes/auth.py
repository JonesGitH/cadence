"""Authentication routes: unlock screen, forced password change, security settings."""
import logging
from urllib.parse import urlparse
from flask import render_template, request, redirect, url_for, flash, session
from app import app
from database import (
    password_is_set, verify_password, set_new_password, password_in_history,
    remove_password, password_expires_in_days, is_password_expired,
)

log = logging.getLogger(__name__)


@app.route('/unlock', methods=['GET', 'POST'])
def unlock():
    if not password_is_set():
        return redirect(url_for('dashboard'))
    if session.get('authenticated') and not session.get('force_change'):
        return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        pw = request.form.get('password', '')
        if verify_password(pw):
            session['authenticated'] = True
            if is_password_expired():
                session['force_change'] = True
                log.info('Successful unlock — password expired, forcing change')
                return redirect(url_for('change_password'))
            session.pop('force_change', None)
            log.info('Successful unlock')
            next_url = request.form.get('next', '').strip()
            parsed = urlparse(next_url)
            if not next_url or parsed.netloc or parsed.scheme:
                next_url = url_for('dashboard')
            return redirect(next_url)
        log.warning('Failed unlock attempt')
        error = 'Incorrect password. Please try again.'
    return render_template('unlock.html', next=request.args.get('next', ''), error=error)


@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if not session.get('authenticated'):
        return redirect(url_for('unlock'))
    forced = session.get('force_change', False)
    days   = password_expires_in_days()
    error  = None
    if request.method == 'POST':
        current_pw = request.form.get('current_password', '')
        new_pw     = request.form.get('new_password', '').strip()
        confirm_pw = request.form.get('confirm_password', '').strip()
        if not verify_password(current_pw):
            error = 'Current password is incorrect.'
        elif len(new_pw) < 8:
            error = 'New password must be at least 8 characters.'
        elif new_pw != confirm_pw:
            error = 'New password and confirmation do not match.'
        elif password_in_history(new_pw):
            error = 'That password has been used before. Please choose a new one.'
        else:
            set_new_password(new_pw)
            session.pop('force_change', None)
            log.info('Password changed via change_password page')
            flash('Password changed successfully.', 'success')
            return redirect(url_for('settings') + '#tab-security')
    return render_template('change_password.html', forced=forced, days=days, error=error)


@app.route('/settings/security/set', methods=['POST'])
def security_set_password():
    new_pw     = request.form.get('new_password', '').strip()
    confirm_pw = request.form.get('confirm_password', '').strip()
    if len(new_pw) < 8:
        flash('Password must be at least 8 characters.', 'error')
    elif new_pw != confirm_pw:
        flash('Passwords do not match.', 'error')
    elif password_in_history(new_pw):
        flash('That password has been used before. Please choose a different one.', 'error')
    else:
        set_new_password(new_pw)
        session['authenticated'] = True
        session.pop('force_change', None)
        log.info('Password protection enabled')
        flash('Password protection enabled.', 'success')
    return redirect(url_for('settings') + '#tab-security')


@app.route('/settings/security/change', methods=['POST'])
def security_change_password():
    current_pw = request.form.get('current_password', '')
    new_pw     = request.form.get('new_password', '').strip()
    confirm_pw = request.form.get('confirm_password', '').strip()
    if not verify_password(current_pw):
        flash('Current password is incorrect.', 'error')
    elif len(new_pw) < 8:
        flash('New password must be at least 8 characters.', 'error')
    elif new_pw != confirm_pw:
        flash('New password and confirmation do not match.', 'error')
    elif password_in_history(new_pw):
        flash('That password has been used before. Please choose a different one.', 'error')
    else:
        set_new_password(new_pw)
        session.pop('force_change', None)
        log.info('Password changed via settings')
        flash('Password changed successfully.', 'success')
    return redirect(url_for('settings') + '#tab-security')


@app.route('/settings/security/remove', methods=['POST'])
def security_remove_password():
    current_pw = request.form.get('current_password', '')
    if not verify_password(current_pw):
        flash('Incorrect password — protection not removed.', 'error')
    else:
        remove_password()
        log.info('Password protection removed')
        flash('Password protection removed.', 'success')
    return redirect(url_for('settings') + '#tab-security')
