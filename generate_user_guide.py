"""
generate_user_guide.py
Run this script to regenerate Cadence_User_Guide.pdf from scratch.
Usage:  python generate_user_guide.py
"""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, PageBreak, KeepTogether, ListFlowable,
    ListItem,
)
from reportlab.platypus.tableofcontents import TableOfContents

# ── Brand colours ──────────────────────────────────────────────────────────────
PRIMARY      = colors.HexColor('#2563EB')
PRIMARY_DARK = colors.HexColor('#1E2D3D')
ACCENT       = colors.HexColor('#F0F4FF')
TEXT         = colors.HexColor('#1F2937')
MUTED        = colors.HexColor('#6B7280')
SUCCESS      = colors.HexColor('#15803D')
WARNING      = colors.HexColor('#D97706')
BORDER       = colors.HexColor('#E5E7EB')
WHITE        = colors.white
CODE_BG      = colors.HexColor('#F3F4F6')

PAGE_W, PAGE_H = letter
MARGIN = 0.85 * inch

# ── Styles ─────────────────────────────────────────────────────────────────────
BASE = getSampleStyleSheet()

def _sty(name, parent='Normal', **kw):
    s = ParagraphStyle(name, parent=BASE[parent], **kw)
    return s

H1  = _sty('H1',  'Heading1', fontSize=22, textColor=PRIMARY_DARK, spaceAfter=8,
            spaceBefore=18, fontName='Helvetica-Bold', leading=26)
H2  = _sty('H2',  'Heading2', fontSize=15, textColor=PRIMARY,      spaceAfter=6,
            spaceBefore=14, fontName='Helvetica-Bold', leading=18,
            borderPad=4, borderColor=PRIMARY, borderWidth=0,
            leftIndent=0)
H3  = _sty('H3',  'Heading3', fontSize=12, textColor=PRIMARY_DARK, spaceAfter=4,
            spaceBefore=10, fontName='Helvetica-Bold', leading=15)
BODY = _sty('BODY', 'Normal',  fontSize=10, textColor=TEXT, spaceAfter=5,
             leading=15, fontName='Helvetica')
BODY_SMALL = _sty('BODY_SMALL', 'Normal', fontSize=9, textColor=MUTED,
                   leading=13, fontName='Helvetica')
CODE  = _sty('CODE', 'Normal', fontSize=9, fontName='Courier', textColor=TEXT,
              backColor=CODE_BG, leftIndent=8, rightIndent=8,
              spaceBefore=4, spaceAfter=4, leading=13)
TIP   = _sty('TIP',  'Normal', fontSize=9.5, fontName='Helvetica-Oblique',
              textColor=colors.HexColor('#1E40AF'), leftIndent=10,
              backColor=ACCENT, spaceAfter=6, leading=14)
LABEL = _sty('LABEL', 'Normal', fontSize=9, fontName='Helvetica-Bold',
              textColor=TEXT, leading=13)
VAL   = _sty('VAL',   'Normal', fontSize=9, fontName='Helvetica',
              textColor=TEXT, leading=13)
TOC_1 = _sty('TOC_1', 'Normal', fontSize=10, fontName='Helvetica',
              textColor=PRIMARY, leftIndent=0, leading=16)
TOC_2 = _sty('TOC_2', 'Normal', fontSize=9.5, fontName='Helvetica',
              textColor=TEXT, leftIndent=16, leading=15)

# ── Helpers ────────────────────────────────────────────────────────────────────
def p(text, style=BODY): return Paragraph(text, style)
def h1(text):            return Paragraph(text, H1)
def h2(text):            return Paragraph(text, H2)
def h3(text):            return Paragraph(text, H3)
def sp(n=6):             return Spacer(1, n)
def hr():                return HRFlowable(width='100%', thickness=1, color=BORDER,
                                           spaceAfter=8, spaceBefore=4)
def tip(text):           return Paragraph(f'<b>Tip:</b> {text}', TIP)
def note(text):          return Paragraph(f'<b>Note:</b> {text}', TIP)
def code(text):          return Paragraph(text.replace(' ', '&nbsp;').replace('\n', '<br/>'), CODE)
def bullet(items, style=BODY):
    return ListFlowable(
        [ListItem(p(i, style), leftIndent=16, bulletIndent=6) for i in items],
        bulletType='bullet', leftIndent=18, bulletFontSize=8,
        bulletColor=PRIMARY, spaceBefore=4, spaceAfter=4,
    )

def two_col_table(rows, col_widths=(2.1*inch, 4.3*inch)):
    """Simple two-column definition table."""
    data = [[p(f'<b>{r[0]}</b>', LABEL), p(r[1], VAL)] for r in rows]
    t = Table(data, colWidths=col_widths, repeatRows=0)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0),  ACCENT),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [WHITE, ACCENT]),
        ('GRID',        (0, 0), (-1, -1), 0.4, BORDER),
        ('VALIGN',      (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING',   (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 5),
    ]))
    return t

def header_table(rows, headers, col_widths=None):
    """Multi-column table with a styled header row."""
    if col_widths is None:
        n = len(headers)
        col_widths = [(PAGE_W - 2*MARGIN) / n] * n
    data = [[p(f'<b>{h}</b>', LABEL) for h in headers]] + \
           [[p(c, VAL) for c in row] for row in rows]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, 0),  PRIMARY_DARK),
        ('TEXTCOLOR',    (0, 0), (-1, 0),  WHITE),
        ('FONTNAME',     (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [WHITE, ACCENT]),
        ('GRID',         (0, 0), (-1, -1), 0.4, BORDER),
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING',   (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 5),
    ]))
    return t

# ── Page templates ─────────────────────────────────────────────────────────────
class CadenceDoc(BaseDocTemplate):
    def __init__(self, filename):
        super().__init__(
            filename,
            pagesize=letter,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=MARGIN + 0.3*inch,
        )
        body_frame = Frame(
            MARGIN, MARGIN + 0.3*inch,
            PAGE_W - 2*MARGIN, PAGE_H - 2*MARGIN - 0.3*inch,
            id='body',
        )
        cover_frame = Frame(
            MARGIN, MARGIN,
            PAGE_W - 2*MARGIN, PAGE_H - 2*MARGIN,
            id='cover',
        )
        self.addPageTemplates([
            PageTemplate(id='cover', frames=[cover_frame],
                         onPage=self._cover_page),
            PageTemplate(id='body',  frames=[body_frame],
                         onPage=self._body_page),
        ])

    @staticmethod
    def _cover_page(canvas, doc):
        pass  # cover draws its own content via story

    @staticmethod
    def _body_page(canvas, doc):
        canvas.saveState()
        # Header bar
        canvas.setFillColor(PRIMARY_DARK)
        canvas.rect(0, PAGE_H - 0.38*inch, PAGE_W, 0.38*inch, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont('Helvetica-Bold', 9)
        canvas.drawString(MARGIN, PAGE_H - 0.25*inch, 'CADENCE')
        canvas.setFont('Helvetica', 9)
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.25*inch, 'User Guide')
        # Footer
        canvas.setFillColor(MUTED)
        canvas.setFont('Helvetica', 8)
        canvas.drawString(MARGIN, 0.45*inch,
                          'Cadence — Your consulting rhythm. All data stays on your machine.')
        canvas.drawRightString(PAGE_W - MARGIN, 0.45*inch, f'Page {doc.page}')
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, 0.6*inch, PAGE_W - MARGIN, 0.6*inch)
        canvas.restoreState()


# ── Content ────────────────────────────────────────────────────────────────────
def build_story():
    story = []

    # ── COVER PAGE ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.6*inch))
    cover_title = Paragraph(
        '<font color="#2563EB"><b>Cadence</b></font>',
        ParagraphStyle('CT', fontSize=52, fontName='Helvetica-Bold',
                       alignment=TA_CENTER, leading=58))
    story.append(cover_title)
    story.append(Spacer(1, 0.18*inch))
    story.append(Paragraph('Your consulting rhythm.',
        ParagraphStyle('CS', fontSize=18, fontName='Helvetica',
                       alignment=TA_CENTER, textColor=MUTED, leading=22)))
    story.append(Spacer(1, 0.35*inch))
    # Diamond icon placeholder (drawn with canvas)
    story.append(Spacer(1, 0.2*inch))
    story.append(HRFlowable(width='60%', thickness=2, color=PRIMARY,
                             hAlign='CENTER', spaceAfter=24))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph('User Guide &amp; Reference',
        ParagraphStyle('CU', fontSize=13, fontName='Helvetica',
                       alignment=TA_CENTER, textColor=TEXT)))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph('Version 1.0',
        ParagraphStyle('CV', fontSize=10, fontName='Helvetica',
                       alignment=TA_CENTER, textColor=MUTED)))
    story.append(Spacer(1, 2.5*inch))
    story.append(Paragraph(
        'Invoice &amp; scheduling for Educational Therapists and solo practitioners.',
        ParagraphStyle('CB', fontSize=11, fontName='Helvetica-Oblique',
                       alignment=TA_CENTER, textColor=MUTED)))
    story.append(PageBreak())

    # ── Switch to body template ────────────────────────────────────────────────
    from reportlab.platypus import NextPageTemplate
    story.append(NextPageTemplate('body'))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # 1. WHAT IT DOES
    # ═══════════════════════════════════════════════════════════════════════════
    story += [h1('1. What It Does'), hr()]
    story.append(p(
        'Cadence is a local desktop app built for Educational Therapists and other '
        'solo practitioners. It connects to your Microsoft 365 calendar, finds student '
        'sessions by matching appointment titles, and generates professional PDF invoices '
        'automatically. Everything runs on your own PC — no subscription, no cloud, '
        'no data leaves your machine.'))
    story.append(sp(6))
    story.append(bullet([
        '<b>Reads your Microsoft 365 calendar</b> via the Graph API — Outlook does not need to be open',
        '<b>Finds student sessions</b> by matching appointment titles against each student\'s initials',
        '<b>Generates professional PDF invoices</b> with every session as a line item at your configured rate',
        '<b>Sends invoices by email</b> directly through your Microsoft 365 account — saved to Sent Items',
        '<b>Tracks payment status</b> and produces a full annual income summary for tax reporting',
        '<b>Bulk-imports students</b> from a pre-formatted Excel spreadsheet',
    ]))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # 2. REQUIREMENTS
    # ═══════════════════════════════════════════════════════════════════════════
    story += [h1('2. Requirements'), hr()]
    story.append(header_table(
        [
            ['Windows 10 or 11 (64-bit)', 'Operating system'],
            ['Microsoft 365 account',     'Any personal or organizational account with Outlook calendar access'],
            ['Azure app registration',    'Free, one-time setup — instructions in Section 4'],
        ],
        ['Requirement', 'Details'],
        col_widths=[2.5*inch, 4.0*inch],
    ))
    story.append(sp(10))
    story.append(note(
        'Python is <b>not</b> required when using the one-click installer. '
        'Python 3.10+ is only needed to run from source (developer mode).'))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # 3. INSTALLATION
    # ═══════════════════════════════════════════════════════════════════════════
    story += [h1('3. Installation'), hr()]

    story += [h2('Option A — One-Click Installer (Recommended)')]
    story.append(p(
        'The installer requires no Python, no command prompt, and no technical setup. '
        'It installs Cadence per-user — no administrator password needed.'))
    story.append(sp(6))

    steps_a = [
        ('<b>Download the installer</b>',
         'Get <b>Cadence_Setup_1.0.0.exe</b> from the releases page or from whoever provided your copy.'),
        ('<b>Run the installer</b>',
         'Double-click <b>Cadence_Setup_1.0.0.exe</b>. The installer will:<br/>'
         '&nbsp;&nbsp;• Ask where to install (default: <i>%LOCALAPPDATA%\\Cadence</i>)<br/>'
         '&nbsp;&nbsp;• Offer an optional Desktop shortcut<br/>'
         '&nbsp;&nbsp;• Offer an optional "Launch on Windows startup" shortcut<br/>'
         '&nbsp;&nbsp;• Complete in under 30 seconds'),
        ('<b>Launch Cadence</b>',
         'Click <b>Launch Cadence now</b> on the final installer screen, or use the Start Menu shortcut. '
         'Your browser opens automatically and a blue diamond icon appears in the Windows system tray.'),
    ]
    for i, (title, body) in enumerate(steps_a, 1):
        row = Table(
            [[p(f'<b>{i}</b>', ParagraphStyle('NUM', fontSize=12, fontName='Helvetica-Bold',
                textColor=WHITE, alignment=TA_CENTER)),
              p(f'{title}<br/>{body}', VAL)]],
            colWidths=[0.35*inch, PAGE_W - 2*MARGIN - 0.35*inch - 12],
        )
        row.setStyle(TableStyle([
            ('BACKGROUND',   (0, 0), (0, 0), PRIMARY),
            ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING',  (0, 0), (-1, -1), 6),
            ('TOPPADDING',   (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 6),
            ('ROUNDEDCORNERS', [4]),
        ]))
        story.append(row)
        story.append(sp(6))

    story.append(sp(4))
    story.append(tip(
        'Right-click the blue diamond in the system tray at any time to <b>Open Cadence</b> '
        'or <b>Stop Cadence</b>.'))

    story += [h2('Option B — Portable Build')]
    story.append(p(
        'Builds a self-contained folder you can copy anywhere — including OneDrive or a USB drive. '
        'Requires Python 3.10+ to be installed.'))
    story.append(bullet([
        'Copy the <b>cadence</b> source folder to your PC',
        'Double-click <b>setup.bat</b> — installs Python dependencies (runs once)',
        'Double-click <b>build.bat</b> — builds the .exe (~60–120 sec) and, if '
        '<a href="https://jrsoftware.org/isdl.php">Inno Setup 6</a> is installed, also creates the installer',
    ]))
    story.append(sp(4))
    story.append(code(
        'dist\\Cadence\\Cadence.exe          ← portable, run directly\n'
        'dist\\Cadence_Setup_1.0.0.exe      ← installer (requires Inno Setup)'
    ))

    story += [h2('Option C — Developer Mode')]
    story.append(p(
        'Run directly from source without building. Use this if you are making code changes.'))
    story.append(bullet([
        'Run <b>setup.bat</b> to install packages',
        'Double-click <b>launch.bat</b> — browser opens at http://127.0.0.1:5000',
    ]))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # 4. AZURE APP REGISTRATION
    # ═══════════════════════════════════════════════════════════════════════════
    story += [h1('4. Azure App Registration (One-Time Setup)'), hr()]
    story.append(p(
        'Cadence connects to Microsoft 365 using the <b>Microsoft Graph API</b>. '
        'This requires a free app registration in the Azure portal. You only do this once.'))
    story.append(sp(6))

    azure_steps = [
        ('Create the registration',
         'Open <b>portal.azure.com</b>, search for <b>App registrations</b>, click '
         '<b>+ New registration</b>. Set the name to <i>Cadence</i>, set Supported account '
         'types to <i>"Accounts in any organizational directory and personal Microsoft accounts"</i>, '
         'leave Redirect URI blank, and click <b>Register</b>.'),
        ('Enable public client flows',
         'In your new registration → <b>Authentication</b> → scroll to <b>Advanced settings</b> → '
         'set <b>Allow public client flows</b> to <b>Yes</b> → click <b>Save</b>.'),
        ('Add API permissions',
         'Click <b>API permissions → + Add a permission → Microsoft Graph → Delegated permissions</b>. '
         'Search for and add <b>Calendars.ReadWrite</b>. Repeat and add <b>Mail.Send</b>. '
         'Click <b>Add permissions</b>. '
         '<i>You do not need to grant admin consent for personal accounts.</i>'),
        ('Copy your Client ID',
         'Click <b>Overview</b> in the left menu. Copy the '
         '<b>Application (client) ID</b> — it looks like: '
         '<i>xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx</i>. '
         'You will paste this into Cadence → Settings → Microsoft 365 tab.'),
    ]
    for i, (title, body) in enumerate(azure_steps, 1):
        story.append(KeepTogether([
            p(f'<b>Step {i} — {title}</b>', H3),
            p(body),
            sp(4),
        ]))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # 5. FIRST TIME CONFIGURATION
    # ═══════════════════════════════════════════════════════════════════════════
    story += [h1('5. First Time Configuration'), hr()]
    story.append(p(
        'Open Cadence and click <b>Settings</b> in the sidebar. '
        'Settings are organised into tabs — work through them in order.'))

    story += [h2('Business Tab')]
    story.append(two_col_table([
        ('Your Name',                'Your full name as it should appear on invoices.'),
        ('Title / Credentials',      'e.g. Educational Therapist, M.Ed. — printed below your name.'),
        ('Email',                    'Your business email address.'),
        ('Phone',                    'Your business phone number.'),
        ('Street Address / City / State / Zip', 'Printed in the invoice header and payment instructions.'),
        ('Per-Session Rate ($)',      'Your standard flat rate per session, e.g. 150.00.'),
        ('Venmo Handle',             'e.g. @Your-Name — printed in payment instructions on invoices.'),
        ('Idle Timeout',             'Auto-close Cadence after inactivity. Recommended: 30 min for two-PC setups.'),
    ]))
    story.append(sp(6))
    story.append(p('Click <b>Save Settings</b> when done.'))

    story += [h2('Microsoft 365 Tab')]
    story.append(bullet([
        'Paste your <b>Azure App Client ID</b> into the field',
        'Select your <b>Timezone</b> from the dropdown',
        'Click <b>Save</b>',
        'Click <b>Connect Microsoft 365</b> — a browser tab opens with a sign-in code. '
        'Enter the code when prompted, sign in, and Cadence detects the completion automatically.',
    ]))

    story += [h2('Calendars Tab')]
    story.append(bullet([
        'Click <b>Refresh from Outlook</b> — Cadence lists all your calendars',
        'Toggle <b>Scan</b> on for calendars that contain student appointments',
        'Optionally mark one as <b>Default</b>',
        'Click <b>Save Calendar Preferences</b>',
    ]))

    story += [h2('Storage Tab')]
    story.append(two_col_table([
        ('Database File (.db)',  'Full path to cadence.db. Changing this copies your data automatically. Restart Cadence after saving.'),
        ('Invoice PDF Folder',   'Root folder for saved PDFs. Cadence creates month subfolders automatically (e.g. April 2026\\).'),
    ]))
    story.append(sp(6))
    story.append(tip(
        'Point both paths to a shared OneDrive folder to keep data in sync across two PCs. '
        'See Section 11.'))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # 6. IMPORTING STUDENTS FROM EXCEL
    # ═══════════════════════════════════════════════════════════════════════════
    story += [h1('6. Importing Students from Excel'), hr()]
    story.append(p(
        'If you have many students to add, the Excel import is the fastest method. '
        'It supports all student fields and validates service keys and grade values automatically.'))

    story += [h2('Step 1 — Download the Template')]
    story.append(p(
        'Go to <b>Settings → Import tab</b> and click '
        '<b>cadence_students_template.xlsx</b>. Open the file in Excel.'))
    story.append(sp(4))
    story.append(header_table(
        [
            ['Row 1', 'Column headers (blue = required, dark = optional)'],
            ['Row 2', 'Field hints — what to enter in each column'],
            ['Row 3', 'Sample student — delete before importing'],
            ['Services Reference sheet', 'Lists all valid service key values'],
        ],
        ['Row / Sheet', 'Contents'],
        col_widths=[2.0*inch, 4.5*inch],
    ))

    story += [h2('Step 2 — Fill In Your Students')]
    story.append(p('Start entering data from <b>row 3</b> (or row 4 if you keep the sample). '
                   'Only <b>Name</b> and <b>Initials</b> are required per student.'))
    story.append(sp(6))
    story.append(two_col_table([
        ('Name *',               'Full student name. Must be unique.'),
        ('Initials *',           '2–3 letters matching exactly what appears in calendar appointment titles.'),
        ('Grade',                'Use the dropdown: K, 1st–12th, College, Other.'),
        ('Birthday',             'Format: YYYY-MM-DD (e.g. 2015-03-22).'),
        ('Services',             'Comma-separated keys from the Services Reference sheet '
                                 '(e.g. reading,spelling,grammar).'),
        ('Intake / ROI Complete','Type YES or NO — or use the dropdown.'),
        ('Per-Session Rate',     'Leave blank to inherit the global rate from Settings.'),
    ]))

    story += [h2('Step 3 — Upload')]
    story.append(bullet([
        'Go back to <b>Settings → Import tab</b>',
        'Click <b>Choose File</b> and select your completed .xlsx file',
        'Click <b>Import Students</b>',
        'A summary shows how many students were added, skipped (already exist), or had errors',
    ]))
    story.append(sp(4))
    story.append(note(
        'Students whose names already exist in Cadence are skipped — re-importing the same '
        'file multiple times is safe.'))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # 7. ADDING STUDENTS MANUALLY
    # ═══════════════════════════════════════════════════════════════════════════
    story += [h1('7. Adding Students Manually'), hr()]
    story.append(p('Go to <b>Students</b> in the sidebar and click <b>+ Add Student</b>.'))
    story.append(sp(6))
    story.append(two_col_table([
        ('Full Name',            'Used on invoices and PDF filenames.'),
        ('Initials',             'Must match exactly what appears in calendar appointment titles — case-sensitive.'),
        ('Parent 1 &amp; 2 Name','Printed in the "Bill To" block on invoices.'),
        ('Parent Address / City / State / Zip', 'Printed on invoices.'),
        ('Email',                'Required to enable the Send via Email button.'),
        ('Per-Session Rate ($)', 'Leave blank to use the global rate. Enter a value to override for this student only.'),
        ('Services',             'Check all applicable service areas — internal record only, not printed.'),
        ('Diagnosis',            'Clinical notes — not printed on invoices.'),
        ('Intake / ROI Complete','Administrative checkboxes.'),
    ]))
    story.append(sp(8))
    story.append(p('Click <b>Save Student</b>.'))
    story.append(sp(8))
    story.append(tip(
        '<b>Initials are case-sensitive.</b> Open a real calendar appointment and copy the '
        'initials exactly — <i>AJ</i> and <i>A.J.</i> are different to Cadence.'))
    story.append(sp(4))
    story.append(tip(
        'Use <b>Archive</b> instead of Delete when a student is no longer active. '
        'Their invoice history is preserved and they can be restored later.'))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # 8. CREATING AN INVOICE
    # ═══════════════════════════════════════════════════════════════════════════
    story += [h1('8. Creating an Invoice'), hr()]

    story += [h2('Step 1 — Select Student and Period')]
    story.append(bullet([
        'Click <b>New Invoice</b> in the sidebar',
        'Choose the <b>Student</b>, <b>Month</b>, and <b>Year</b>',
        'Click <b>Find Sessions in Outlook</b>',
    ]))
    story.append(sp(4))
    story.append(p(
        'Cadence scans all enabled calendars for appointments whose title contains the '
        'student\'s initials. Results appear within a few seconds.'))

    story += [h2('Step 2 — Review Sessions')]
    story.append(p(
        'Each matching appointment shows date, start time, end time, duration, rate, and total. '
        '<b>Uncheck any sessions you do not want to bill</b> — for example, a cancelled '
        'appointment. The running total updates instantly.'))

    story += [h2('Step 3 — Adjustments (Optional)')]
    story.append(two_col_table([
        ('Add Late Fee', 'Adds a dollar amount as a separate line item on the invoice.'),
        ('Add Credit',   'Subtracts an amount and shows it in green on the invoice.'),
    ]))

    story += [h2('Step 4 — Generate')]
    story.append(p('Click <b>Generate Invoice &amp; Save PDF</b>. Cadence:'))
    story.append(bullet([
        'Assigns the next sequential invoice number (starting at 5550)',
        'Saves the invoice record to the database',
        'Generates a PDF in your configured folder under a month subfolder '
        '(e.g. <i>April 2026\\Alex Jones.pdf</i>)',
        'Opens the Invoice Detail page',
    ]))
    story.append(sp(4))
    story.append(note(
        'If an invoice already exists for that student and month, Cadence warns you '
        'before creating a second one.'))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # 9. MANAGING INVOICES
    # ═══════════════════════════════════════════════════════════════════════════
    story += [h1('9. Managing Invoices'), hr()]

    story += [h2('Invoice History')]
    story.append(p(
        'Click <b>Invoice History</b> in the sidebar to see all invoices.'))
    story.append(sp(4))
    story.append(bullet([
        '<b>Filter</b> by student, year, or status using the dropdowns',
        '<b>Sort</b> any column by clicking the column header (arrows show direction)',
        '<b>Totals row</b> at the bottom shows aggregate hours and amount for visible rows',
        '<b>⋯ menu</b> on each row — click to View, Open PDF, or Open Folder',
    ]))

    story += [h2('Invoice Detail Page')]
    story.append(header_table(
        [
            ['Mark as Paid / ✓ Paid', 'Toggles paid status. Shows a toast confirmation.'],
            ['Send via Email',        'Sends the PDF via Microsoft 365. Shows success or error toast. Requires an email address on file for the student.'],
            ['Save PDF',              'Opens the saved PDF in your default viewer.'],
            ['Open Folder',           'Opens the PDF folder in Windows Explorer.'],
            ['Delete',                'Removes the invoice record. Does not delete the PDF file from disk.'],
        ],
        ['Action', 'Description'],
        col_widths=[1.8*inch, 4.65*inch],
    ))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # 10. ANNUAL SUMMARY
    # ═══════════════════════════════════════════════════════════════════════════
    story += [h1('10. Annual Summary & CSV Export'), hr()]
    story.append(p('Click <b>Summary</b> in the sidebar.'))
    story.append(sp(6))
    story.append(header_table(
        [
            ['Total Billed',  'Sum of all invoice totals for the year.'],
            ['Collected',     'Total from paid invoices (green). Progress bar shows % of billed collected.'],
            ['Outstanding',   'Unpaid balance (amber).'],
        ],
        ['Stat Card', 'What It Shows'],
        col_widths=[1.8*inch, 4.65*inch],
    ))
    story.append(sp(8))
    story.append(p(
        'The <b>Monthly Breakdown</b> and <b>By Student</b> tables show invoices, hours, '
        'billed, collected, and outstanding for each period.'))
    story.append(sp(4))
    story.append(p(
        'Use the <b>year dropdown</b> to switch years. '
        'Click <b>Export CSV</b> to download all invoice data for tax preparation.'))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # 11. TWO PCS WITH ONEDRIVE
    # ═══════════════════════════════════════════════════════════════════════════
    story += [h1('11. Using Two PCs with OneDrive'), hr()]
    story.append(p(
        'Share one Cadence database between a home PC and an office PC using OneDrive.'))

    story += [h2('Setup')]
    story.append(bullet([
        'On PC 1, go to <b>Settings → Storage tab</b>',
        'Set the <b>Database File</b> path to a OneDrive folder, e.g.:<br/>'
        '<i>C:\\Users\\You\\OneDrive\\Cadence\\cadence.db</i>',
        'Set the <b>Invoice PDF Folder</b> similarly, e.g.:<br/>'
        '<i>C:\\Users\\You\\OneDrive\\Invoices</i>',
        'Click <b>Save Storage Paths</b> — data is copied automatically',
        'Repeat on PC 2 using the exact same paths',
    ]))

    story += [h2('Important Rules')]
    story.append(bullet([
        '<b>Never run Cadence on both PCs at the same time</b> — SQLite is not '
        'designed for concurrent multi-machine access',
        'Set an <b>Idle Timeout</b> (30 minutes recommended) so Cadence auto-closes '
        'when you leave one PC',
    ]))
    story.append(sp(6))
    story.append(header_table(
        [
            ['Never',    'Single PC only'],
            ['15 min',   'Frequent switching'],
            ['30 min',   'Recommended for two-PC setups'],
            ['1 hour',   'Occasional switching'],
            ['2 hours',  'Long sessions'],
        ],
        ['Idle Timeout', 'Best For'],
        col_widths=[1.5*inch, 4.95*inch],
    ))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # 12. SETTINGS REFERENCE
    # ═══════════════════════════════════════════════════════════════════════════
    story += [h1('12. Settings Reference'), hr()]
    story.append(header_table(
        [
            ['Business',      'Name, title, contact info, per-session rate, Venmo handle, idle timeout'],
            ['Storage',       'Database file path and invoice PDF folder path'],
            ['Microsoft 365', 'Azure Client ID, timezone, connect/disconnect'],
            ['Calendars',     'Enable/disable calendars, set default calendar'],
            ['Backup',        'One-click timestamped database backup'],
            ['Import',        'Download Excel template, upload student spreadsheet'],
        ],
        ['Tab', 'What\'s Here'],
        col_widths=[1.5*inch, 4.95*inch],
    ))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # 13. DATABASE BACKUP
    # ═══════════════════════════════════════════════════════════════════════════
    story += [h1('13. Database Backup'), hr()]
    story.append(p(
        'Regular backups protect against accidental data loss. '
        'Cadence stores everything in a single SQLite file — backing up takes one click.'))

    story += [h2('Creating a Backup')]
    story.append(bullet([
        'Go to <b>Settings → Backup tab</b>',
        'Click <b>Back Up Now</b>',
        'A file named <b>cadence_backup_YYYYMMDD_HHMMSS.db</b> is saved beside your database',
    ]))
    story.append(sp(4))
    story.append(tip('Back up weekly, or immediately after generating a batch of invoices.'))

    story += [h2('Restoring from a Backup')]
    story.append(bullet([
        'Right-click the tray icon → <b>Stop Cadence</b>',
        'In File Explorer, rename <b>cadence.db</b> → <b>cadence_old.db</b>',
        'Rename the backup file → <b>cadence.db</b>',
        'Reopen Cadence',
    ]))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # 14. TROUBLESHOOTING
    # ═══════════════════════════════════════════════════════════════════════════
    story += [h1('14. Troubleshooting'), hr()]

    issues = [
        ('"Microsoft 365 is not configured"',
         'Go to <b>Settings → Microsoft 365 tab</b> → enter your Azure App Client ID → '
         'click Save → click <b>Connect Microsoft 365</b> and complete the browser sign-in.'),
        ('"Could not reach Microsoft 365" / sessions not loading',
         'Your authentication token may have expired. Go to <b>Settings → Microsoft 365</b> — '
         'if it shows Disconnected, click <b>Connect Microsoft 365</b> to re-authenticate. '
         'Ensure your PC has an active internet connection.'),
        ('"No sessions found"',
         'Check that the student\'s <b>Initials</b> in Cadence match <b>exactly</b> what appears '
         'in the calendar appointment title (case-sensitive: AJ ≠ A.J.). Confirm the correct '
         'calendars have Scan toggled on. Verify appointments fall within the selected month.'),
        ('"Send via Email" is greyed out',
         'The student has no email address. Go to <b>Students → Edit</b> → add the parent email → '
         'click Save Student.'),
        ('Browser does not open automatically',
         'Open your browser manually and go to <b>http://127.0.0.1:5000</b>. '
         'Check the tray icon is visible in the system tray.'),
        ('App closes on its own',
         'Normal behaviour when the Idle Timeout fires. Simply reopen Cadence from the Start Menu or tray.'),
        ('Database locked / save errors',
         'Cadence is running on two PCs simultaneously. Close it on one PC first. Enable Idle Timeout.'),
        ('Installer won\'t run',
         'Try right-clicking <b>Cadence_Setup_1.0.0.exe → Run as administrator</b>. '
         'Alternatively, use the portable build: copy <b>dist\\Cadence\\Cadence.exe</b> directly.'),
    ]
    for title, body in issues:
        story.append(KeepTogether([
            p(f'<b>{title}</b>', H3),
            p(body),
            sp(6),
        ]))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # 15. FILE OVERVIEW
    # ═══════════════════════════════════════════════════════════════════════════
    story += [h1('15. File Overview'), hr()]
    story.append(header_table(
        [
            ['Cadence_Setup_1.0.0.exe', 'One-click installer (produced by build.bat)'],
            ['build.bat',               'Builds the .exe and installer'],
            ['setup.bat',               'First-time dev setup (installs Python packages)'],
            ['launch.bat',              'Developer mode — run from source'],
            ['cadence.spec',            'PyInstaller build configuration'],
            ['cadence.iss',             'Inno Setup installer script'],
            ['file_version_info.txt',   'Windows .exe version metadata'],
            ['main.py',                 'Entry point: starts Flask + system tray'],
            ['app.py',                  'All page routes and business logic'],
            ['database.py',             'SQLite database layer'],
            ['config.py',               'Paths and settings loader'],
            ['graph_auth.py',           'Microsoft 365 OAuth (MSAL device flow)'],
            ['outlook.py',              'Calendar and email via Microsoft Graph API'],
            ['pdf_generator.py',        'ReportLab PDF invoice builder'],
            ['create_icon.py',          'Generates static/icon.ico'],
            ['generate_user_guide.py',  'Regenerates this PDF'],
            ['requirements.txt',        'Python package list'],
            ['cadence.db',              'Created automatically on first launch'],
            ['templates/',              'Jinja2 HTML pages'],
            ['static/',                 'CSS, JavaScript, icons'],
        ],
        ['File / Folder', 'Purpose'],
        col_widths=[2.4*inch, 4.05*inch],
    ))
    story.append(sp(16))
    story.append(HRFlowable(width='100%', thickness=1, color=BORDER))
    story.append(sp(6))
    story.append(Paragraph(
        'Cadence runs entirely on your local machine. '
        'Your data is never sent to any third party.',
        ParagraphStyle('FOOTER_NOTE', fontSize=9, fontName='Helvetica-Oblique',
                       textColor=MUTED, alignment=TA_CENTER)))

    return story


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       'Cadence_User_Guide.pdf')
    doc = CadenceDoc(out)
    story = build_story()
    doc.multiBuild(story)
    print(f'Guide saved to: {out}')
