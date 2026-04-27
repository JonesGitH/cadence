"""Calendar view routes."""
import logging
import calendar as cal_module
from collections import defaultdict
from datetime import date, datetime, timedelta
from flask import render_template, request, jsonify
from app import app
from database import get_enabled_calendars, get_clients_initials_map
from outlook import get_all_calendar_items, get_calendar_items_range, update_calendar_item
from helpers import _match_initials

log = logging.getLogger(__name__)

_HOUR_PX = 65   # pixels per hour in the week time-grid
_DAY_START = 7  # 7 AM
_DAY_END   = 20 # 8 PM  (13 hours visible)


@app.route('/calendar')
def calendar_view():
    now  = datetime.now()
    view = request.args.get('view', 'week')

    enabled      = get_enabled_calendars()
    initials_map = get_clients_initials_map()
    error        = None

    if view == 'week':
        date_str = request.args.get('date', now.date().isoformat())
        try:
            anchor = date.fromisoformat(date_str)
        except ValueError:
            anchor = now.date()

        monday    = anchor - timedelta(days=anchor.weekday())
        friday    = monday + timedelta(days=4)
        week_days = [monday + timedelta(days=i) for i in range(5)]

        s_mon = monday.strftime('%b')
        e_mon = friday.strftime('%b')
        if s_mon == e_mon:
            week_label = f'{s_mon} {monday.day}–{friday.day}, {friday.year}'
        else:
            week_label = f'{s_mon} {monday.day} – {e_mon} {friday.day}, {friday.year}'

        cal_items = []
        if enabled:
            try:
                start_iso = f'{monday.isoformat()}T00:00:00'
                end_iso   = f'{friday.isoformat()}T23:59:59'
                cal_items = get_calendar_items_range(start_iso, end_iso, enabled)
                for item in cal_items:
                    item['student'] = _match_initials(item['subject'], initials_map)
            except RuntimeError as e:
                error = str(e)

        by_date = defaultdict(list)
        for item in cal_items:
            by_date[item['date']].append(item)

        return render_template('calendar.html',
            view='week',
            week_days=week_days,
            week_label=week_label,
            by_date=by_date,
            prev_week_date=(monday - timedelta(days=7)).isoformat(),
            next_week_date=(monday + timedelta(days=7)).isoformat(),
            today_date=now.date(),
            hour_px=_HOUR_PX,
            day_start=_DAY_START,
            day_end=_DAY_END,
            enabled=enabled,
            error=error,
            month=now.month, year=now.year,
        )

    else:
        # Month view
        try:
            month = int(request.args.get('month', now.month))
            year  = int(request.args.get('year',  now.year))
        except (ValueError, TypeError):
            month, year = now.month, now.year
        if month < 1:  month, year = 12, year - 1
        if month > 12: month, year = 1,  year + 1

        cal_items = []
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

        _, days_in_month = cal_module.monthrange(year, month)

        first_of_month = date(year, month, 1)
        last_of_month  = date(year, month, days_in_month)
        start_monday   = first_of_month - timedelta(days=first_of_month.weekday())
        weeks = []
        d = start_monday
        while d <= last_of_month:
            week = [
                (d + timedelta(days=i)).day if (d + timedelta(days=i)).month == month else None
                for i in range(5)
            ]
            weeks.append(week)
            d += timedelta(days=7)

        prev_month = month - 1 if month > 1 else 12
        prev_year  = year      if month > 1 else year - 1
        next_month = month + 1 if month < 12 else 1
        next_year  = year      if month < 12 else year + 1
        today_day  = now.day if (now.month == month and now.year == year) else None

        return render_template('calendar.html',
            view='month',
            month=month, year=year,
            month_name_str=cal_module.month_name[month],
            weeks=weeks,
            by_day=by_day,
            enabled=enabled,
            error=error,
            prev_month=prev_month, prev_year=prev_year,
            next_month=next_month, next_year=next_year,
            today_day=today_day,
            today_date=now.date(),
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
