"""
Tests for PDF generation.

Covers:
  - build_pdf() produces a non-empty file that starts with the PDF magic bytes
  - Output path is inside the requested pdf_folder
  - File is created even with minimal invoice data (no late fee, no credit)
  - Late-fee and credit lines are accepted without error
"""
import os
import pytest


INVOICE = {
    'invoice_number': 'INV-0001',
    'client_name':    'Jane Smith',
    'student_name':   'Jane Smith',
    'month':          3,
    'year':           2025,
    'hourly_rate':    75.0,
    'total_hours':    2.0,
    'total_amount':   150.0,
    'invoice_date':   '3/1/2025',
}

BUSINESS = {
    'name':         'Test Tutor',
    'title':        'Educational Specialist',
    'email':        'tutor@example.com',
    'phone':        '555-555-5555',
    'address':      '1 Main St',
    'city':         'Austin',
    'state':        'TX',
    'zip':          '78701',
    'venmo_handle': '@testtutor',
}

PARENT = {
    'name':    'Mary Smith',
    'address': '123 Oak St',
    'city':    'Austin',
    'state':   'TX',
    'zip':     '78702',
}

LINES_SESSIONS = [
    {
        'line_type':      'session',
        'session_date':   'Mon Mar 03',
        'start_time':     '3:00 PM',
        'end_time':       '4:00 PM',
        'duration_hours': 1.0,
        'rate':           75.0,
        'line_total':     75.0,
    },
    {
        'line_type':      'session',
        'session_date':   'Wed Mar 05',
        'start_time':     '3:00 PM',
        'end_time':       '4:00 PM',
        'duration_hours': 1.0,
        'rate':           75.0,
        'line_total':     75.0,
    },
]


def test_pdf_created(tmp_path):
    from pdf_generator import build_pdf
    path = build_pdf(INVOICE, LINES_SESSIONS, BUSINESS, PARENT,
                     pdf_folder=str(tmp_path))
    assert os.path.isfile(path), f'Expected PDF at {path}'
    assert os.path.getsize(path) > 0, 'PDF file is empty'


def test_pdf_magic_bytes(tmp_path):
    """%PDF- magic bytes must be present at the start of the file."""
    from pdf_generator import build_pdf
    path = build_pdf(INVOICE, LINES_SESSIONS, BUSINESS, PARENT,
                     pdf_folder=str(tmp_path))
    with open(path, 'rb') as fh:
        header = fh.read(5)
    assert header == b'%PDF-', f'File does not start with PDF magic bytes (got {header!r})'


def test_pdf_inside_requested_folder(tmp_path):
    from pdf_generator import build_pdf
    path = build_pdf(INVOICE, LINES_SESSIONS, BUSINESS, PARENT,
                     pdf_folder=str(tmp_path))
    assert os.path.commonpath([path, str(tmp_path)]) == str(tmp_path), \
        'PDF was created outside the requested folder'


def test_pdf_with_late_fee_and_credit(tmp_path):
    from pdf_generator import build_pdf
    lines = LINES_SESSIONS + [
        {'line_type': 'late_fee', 'note': 'Late payment', 'line_total': 20.0},
        {'line_type': 'credit',   'note': 'Overpayment',  'line_total': 5.0},
    ]
    invoice = dict(INVOICE, total_amount=165.0)
    path = build_pdf(invoice, lines, BUSINESS, PARENT, pdf_folder=str(tmp_path))
    assert os.path.isfile(path)
    assert os.path.getsize(path) > 0


def test_pdf_empty_optional_fields(tmp_path):
    """PDF must build even when optional business/parent fields are blank."""
    from pdf_generator import build_pdf
    sparse_business = {k: '' for k in BUSINESS}
    sparse_business['name'] = 'Minimal Tutor'
    sparse_parent = {k: '' for k in PARENT}
    sparse_parent['name'] = 'Parent Name'

    path = build_pdf(INVOICE, LINES_SESSIONS, sparse_business, sparse_parent,
                     pdf_folder=str(tmp_path))
    assert os.path.isfile(path)
    assert os.path.getsize(path) > 0
