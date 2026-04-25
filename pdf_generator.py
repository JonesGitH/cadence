import os
import calendar as cal_module
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable, KeepTogether
)

BLUE_HEX  = '#2563eb'
MUTED_HEX = '#64748b'
GREEN_HEX = '#15803d'

BLUE    = colors.HexColor(BLUE_HEX)
MUTED   = colors.HexColor(MUTED_HEX)
GREEN   = colors.HexColor(GREEN_HEX)
BORDER  = colors.HexColor('#e2e8f0')
TEXT    = colors.HexColor('#1e293b')
BLUE_BG = colors.HexColor('#eff6ff')


def _style(name, **kw):
    base = dict(fontName='Helvetica', fontSize=10, textColor=TEXT, leading=14)
    base.update(kw)
    return ParagraphStyle(name, **base)


def _addr_lines(street, city, state, zip_):
    lines = []
    if street:
        lines.append(street)
    city_state = ', '.join(filter(None, [city, state]))
    if city_state:
        lines.append(city_state + (' ' + zip_ if zip_ else ''))
    return lines


def _ordinal(n):
    v = n % 100
    if 11 <= v <= 13:
        return str(n) + 'th'
    return str(n) + {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')


def _fmt_session_label(date_str, start_time, end_time):
    try:
        d = datetime.strptime(date_str, '%B %d, %Y')
        day_label = f"{d.strftime('%A')}, {_ordinal(d.day)}"
    except Exception:
        day_label = date_str
    return f"{day_label}\n{start_time} – {end_time}"


def build_pdf(invoice, lines, business, parent=None, pdf_folder=None):
    if pdf_folder is None:
        pdf_folder = r'C:\invoice'
    period   = f"{cal_module.month_name[invoice['month']]} {invoice['year']}"
    folder   = os.path.join(pdf_folder, period)
    os.makedirs(folder, exist_ok=True)
    pdf_path = os.path.join(folder, f"{invoice.get('student_name', invoice['client_name'])}.pdf")

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
    )

    story = []
    W = letter[0] - 1.3 * inch

    # ── Header: name/address block left | INVOICE + number right ─────────────
    biz_lines   = _addr_lines(business.get('address',''), business.get('city',''),
                               business.get('state',''), business.get('zip',''))
    biz_contact = '<br/>'.join(filter(None, [business.get('phone',''), business.get('email','')]))
    addr_html    = ('<br/>' + '<br/>'.join(biz_lines)) if biz_lines else ''
    contact_html = ('<br/>' + biz_contact) if biz_contact else ''

    header_tbl = Table([[
        Paragraph(
            f'<font size="18" color="{BLUE_HEX}"><b>{business["name"]}</b></font>'
            + (f'<br/><font size="10" color="{MUTED_HEX}">{business["title"]}</font>'
               if business.get('title') else '')
            + addr_html
            + contact_html,
            _style('biz_hdr', fontSize=10, leading=16)
        ),
        Paragraph(
            f'<font size="13" color="{MUTED_HEX}">INVOICE</font><br/>'
            f'<font size="20" color="{BLUE_HEX}"><b>{invoice["invoice_number"]}</b></font>',
            _style('inv_num', fontSize=10, leading=22, alignment=TA_RIGHT)
        ),
    ]], colWidths=[W * 0.60, W * 0.40])
    header_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(header_tbl)

    # Double rule
    story.append(HRFlowable(width=W, thickness=2.5, color=BLUE, spaceAfter=2))
    story.append(HRFlowable(width=W, thickness=0.8, color=BLUE, spaceAfter=14))

    # ── Bill-to block: parent left | date + student right ────────────────────
    if parent and parent.get('name'):
        parent_lines   = _addr_lines(parent.get('address',''), parent.get('city',''),
                                     parent.get('state',''), parent.get('zip',''))
        bill_addr_html = ('<br/>' + '<br/>'.join(parent_lines)) if parent_lines else ''
        bill_block = (
            f'<font size="9" color="{MUTED_HEX}">BILL TO</font><br/>'
            f'<b>{parent["name"]}</b>' + bill_addr_html
        )
    else:
        bill_block = (
            f'<font size="9" color="{MUTED_HEX}">BILL TO</font><br/>'
            f'<b>{invoice["client_name"]}</b>'
        )

    meta_block = (
        f'<font size="9" color="{MUTED_HEX}">DATE</font><br/>'
        f'{invoice.get("invoice_date", "")}<br/><br/>'
        f'<font size="9" color="{MUTED_HEX}">STUDENT</font><br/>'
        f'<b>{invoice.get("student_name", invoice["client_name"])}</b>'
    )

    bill_tbl = Table([[
        Paragraph(bill_block, _style('bill', fontSize=10, leading=16)),
        Paragraph(meta_block, _style('meta', fontSize=10, leading=16, alignment=TA_RIGHT)),
    ]], colWidths=[W * 0.55, W * 0.45])
    bill_tbl.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story.append(bill_tbl)
    story.append(Spacer(1, 18))

    # ── Session table ─────────────────────────────────────────────────────────
    # Columns: Month | Session Date+Time | Session Price | Total
    col_w = [W * 0.18, W * 0.46, W * 0.18, W * 0.18]

    th  = _style('th',  fontSize=9, fontName='Helvetica-Bold', textColor=MUTED)
    th_r = _style('th_r', fontSize=9, fontName='Helvetica-Bold', textColor=MUTED, alignment=TA_RIGHT)
    td   = _style('td',  fontSize=10, leading=15)
    td_r = _style('td_r', fontSize=10, alignment=TA_RIGHT)
    td_mo = _style('td_mo', fontSize=11, fontName='Helvetica-Bold', textColor=BLUE,
                   alignment=TA_CENTER, leading=14)

    session_lines = [l for l in lines if l.get('line_type') == 'session']
    adj_lines     = [l for l in lines if l.get('line_type') in ('late_fee', 'credit')]
    rate          = float(invoice['hourly_rate'])

    # header row
    table_data = [[
        Paragraph('MONTH',   th),
        Paragraph('SESSION', th),
        Paragraph('PRICE',   th_r),
        Paragraph('TOTAL',   th_r),
    ]]

    span_cmds = []
    first_session_row = 1  # data starts at row 1 (after header)

    for i, s in enumerate(session_lines):
        label = _fmt_session_label(s['session_date'], s['start_time'], s['end_time'])
        month_cell = Paragraph(cal_module.month_name[invoice['month']], td_mo) if i == 0 else Paragraph('', td)
        table_data.append([
            month_cell,
            Paragraph(label, td),
            Paragraph(f'${rate:,.2f}', td_r),
            Paragraph('', td_r),
        ])

    last_session_row = len(table_data) - 1  # 0-indexed; last session row index

    # span month column across all session rows
    if len(session_lines) > 1:
        span_cmds.append(('SPAN', (0, first_session_row), (0, last_session_row)))

    # adjustment lines (late fee, credit)
    for adj in adj_lines:
        ri = len(table_data)
        if adj['line_type'] == 'late_fee':
            note = adj.get('note') or 'Late fee'
            table_data.append([
                Paragraph('', td),
                Paragraph(f'<i>{note}</i>', _style('adj', fontSize=10, textColor=MUTED, leading=14)),
                Paragraph('', td),
                Paragraph(f'${adj["line_total"]:,.2f}', td_r),
            ])
        else:
            note = adj.get('note') or 'Credit'
            table_data.append([
                Paragraph('', td),
                Paragraph(f'<i>{note}</i>', _style('cr', fontSize=10, textColor=GREEN, leading=14)),
                Paragraph('', td),
                Paragraph(f'<font color="#15803d">-${adj["line_total"]:,.2f}</font>', td_r),
            ])
        span_cmds.append(('SPAN', (0, ri), (1, ri)))

    # total row
    total_row = len(table_data)
    table_data.append([
        Paragraph('', td),
        Paragraph('', td),
        Paragraph('<b>TOTAL</b>', _style('tot_lbl', fontSize=10, fontName='Helvetica-Bold',
                                         textColor=BLUE, alignment=TA_RIGHT)),
        Paragraph(f'<b>${invoice["total_amount"]:,.2f}</b>',
                  _style('tot_val', fontSize=11, fontName='Helvetica-Bold',
                         textColor=BLUE, alignment=TA_RIGHT)),
    ])
    span_cmds.append(('SPAN', (0, total_row), (1, total_row)))

    tbl_style = [
        ('BACKGROUND',    (0, 0),  (-1, 0),             colors.HexColor('#f1f5f9')),
        ('TOPPADDING',    (0, 0),  (-1, 0),              8),
        ('BOTTOMPADDING', (0, 0),  (-1, 0),              8),
        ('LINEBELOW',     (0, 0),  (-1, 0),              1.5, BLUE),
        ('TOPPADDING',    (0, 1),  (-1, total_row - 1),  8),
        ('BOTTOMPADDING', (0, 1),  (-1, total_row - 1),  8),
        ('LINEBELOW',     (0, 1),  (-1, total_row - 1),  0.5, BORDER),
        ('VALIGN',        (0, 0),  (-1, -1),             'MIDDLE'),
        ('VALIGN',        (0, first_session_row), (0, last_session_row), 'MIDDLE'),
        ('TOPPADDING',    (0, total_row), (-1, total_row), 10),
        ('BOTTOMPADDING', (0, total_row), (-1, total_row), 10),
        ('LINEABOVE',     (0, total_row), (-1, total_row), 1.5, BLUE),
        ('BACKGROUND',    (0, total_row), (-1, total_row), BLUE_BG),
    ] + [('SPAN',) + cmd[1:] for cmd in span_cmds]

    tbl = Table(table_data, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle(tbl_style))
    story.append(tbl)
    story.append(Spacer(1, 20))

    # ── Late fee notice box ───────────────────────────────────────────────────
    next_m = invoice['month'] + 1 if invoice['month'] < 12 else 1
    next_y = invoice['year'] if invoice['month'] < 12 else invoice['year'] + 1
    late_notice = (
        f"<b>Late fee applies</b> if payment is not received by "
        f"{next_m}/1/{next_y}."
    )
    notice_tbl = Table([[
        Paragraph(late_notice, _style('late_notice', fontSize=9, textColor=BLUE, leading=13)),
    ]], colWidths=[W])
    notice_tbl.setStyle(TableStyle([
        ('BOX',           (0, 0), (-1, -1), 1, BLUE),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING',   (0, 0), (-1, -1), 12),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
        ('BACKGROUND',    (0, 0), (-1, -1), BLUE_BG),
    ]))
    story.append(notice_tbl)
    story.append(Spacer(1, 20))

    # ── Payment instructions ──────────────────────────────────────────────────
    story.append(HRFlowable(width=W, thickness=0.5, color=BORDER, spaceAfter=10))

    venmo    = business.get('venmo_handle', '')
    phone    = business.get('phone', '')
    email    = business.get('email', '')
    biz_name = business.get('name', '')
    check_lines = [biz_name] + _addr_lines(business.get('address',''), business.get('city',''),
                                            business.get('state',''), business.get('zip',''))

    pay_hdr = _style('pay_hdr', fontSize=9, fontName='Helvetica-Bold', textColor=MUTED,
                     leading=12, alignment=TA_CENTER)
    pay_td  = _style('pay_td',  fontSize=9, textColor=TEXT, leading=13, alignment=TA_CENTER)

    def _pay_cell(label, content):
        return [Paragraph(label, pay_hdr), Spacer(1, 4), Paragraph(content or '—', pay_td)]

    pay_tbl = Table([[
        _pay_cell('VENMO',           '<br/>'.join(filter(None, [venmo, phone, email]))),
        _pay_cell('ZELLE',           email),
        _pay_cell('CHECK PAYABLE TO','<br/>'.join(filter(None, check_lines))),
    ]], colWidths=[W / 3, W / 3, W / 3])
    pay_tbl.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LINEBEFORE',    (1, 0), (1, -1),  0.5, BORDER),
        ('LINEBEFORE',    (2, 0), (2, -1),  0.5, BORDER),
    ]))
    story.append(pay_tbl)

    doc.build(story)
    return pdf_path
