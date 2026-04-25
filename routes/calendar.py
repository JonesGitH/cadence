"""Calendar view routes."""
import logging
import calendar as cal_module
from collections import defaultdict
from datetime import datetime
from flask import render_template, request, jsonify
from app import app
from database import get_enabled_calendars, get_clients_initials_map
from outlook import get_all_calendar_items, update_calendar_item
from helpers import _match_initials

log = logging.getLogger(__name__)


@app.route('/calendar')
def calendar_view():
    now = datetime.now()
    try:
        month = int(request.args.get('month', now.month))
        year  = int(request.args.get('year',  now.year))
    except (ValueError, TypeError):
        month, year = now.month, now.year
    if month < 1:  month, year = 12, year - 1
    if month > 12: month, year = 1,  year + 1

    enabled      = get_enabled_calendars()
    initials_map = get_clients_initials_map()

    cal_items = []
    error     = None
    if enabled:
        try:
            cal_items = get_all_calendar_items(month, year, enabled)
            for item in cal_items:
                item['student'] = _match_initials(item['subject'], initials_map)
        except RuntimeError as e:
            error = str(e)

    by_day = defaultdict(list)
    for item in cal_items:
        by_day[item['day']].append(item)

    first_weekday, days_in_month = cal_module.monthrange(year, month)
    first_weekday = (first_weekday + 1) % 7

    prev_month = month - 1 if month > 1 else 12
    prev_year  = year      if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year  = year      if month < 12 else year + 1
    today_day  = now.day if (now.month == month and now.year == year) else None

    return render_template('calendar.html',
        month=month, year=year,
        month_name_str=cal_module.month_name[month],
        days_in_month=days_in_month,
        first_weekday=first_weekday,
        by_day=by_day,
        enabled=enabled,
        error=error,
        prev_month=prev_month, prev_year=prev_year,
        next_month=next_month, next_year=next_year,
        today_day=today_day,
    )


@app.route('/calendar/item/update', methods=['POST'])
def calendar_item_update():
    data     = request.get_json()
    entry_id = data.get('entry_id', '').strip()
    subject  = data.get('subject',  '').strip()
    date_str = data.get('date',     '').strip()
    start_t  = data.get('start',    '').strip()
    end_t    = data.get('end',      '').strip()

    if not entry_id or not subject or not date_str or not start_t or not end_t:
        return jsonify({'error': 'All fields are required.'}), 400

    try:
        new_start = datetime.strptime(f'{date_str} {start_t}', '%Y-%m-%d %H:%M')
        new_end   = datetime.strptime(f'{date_str} {end_t}',   '%Y-%m-%d %H:%M')
        if new_end <= new_start:
            return jsonify({'error': 'End time must be after start time.'}), 400
        update_calendar_item(entry_id, subject, new_start, new_end)
        return jsonify({'success': True})
    except Exception as e:
        log.error('calendar_item_update failed: %s', e)
        return jsonify({'error': f'Could not update Outlook: {e}'}), 500
