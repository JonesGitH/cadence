# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Cadence  —  one-folder build, no console window.
# Requires PyInstaller >= 6.0  (block_cipher removed, PYZ signature updated).

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# openpyxl ships XML style-sheets and other data files that must travel with it.
openpyxl_datas = collect_data_files('openpyxl')

# ReportLab embeds font metrics as package data.
reportlab_datas = collect_data_files('reportlab', includes=['**/*.afm', '**/*.pfb',
                                                             '**/*.ttf', '**/*.xml'])

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static',    'static'),
    ] + openpyxl_datas + reportlab_datas,
    hiddenimports=[
        # ── pystray (Windows tray backend) ──────────────────────────────────
        'pystray._win32',
        # ── Pillow ───────────────────────────────────────────────────────────
        'PIL._imaging',
        'PIL.Image',
        'PIL.ImageDraw',
        # ── Flask / Jinja2 / Werkzeug ────────────────────────────────────────
        'jinja2.ext',
        'jinja2.loaders',
        'werkzeug.serving',
        'werkzeug.routing',
        'werkzeug.middleware.shared_data',
        # ── MSAL / requests ──────────────────────────────────────────────────
        'msal',
        'msal.application',
        'msal.authority',
        'msal.token_cache',
        'requests',
        'requests.adapters',
        'requests.packages.urllib3',
        # ── ReportLab ────────────────────────────────────────────────────────
        'reportlab.platypus',
        'reportlab.lib.pagesizes',
        'reportlab.lib.units',
        'reportlab.lib.colors',
        'reportlab.lib.styles',
        'reportlab.lib.enums',
        'reportlab.graphics',
        # ── openpyxl ─────────────────────────────────────────────────────────
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.styles.stylesheet',
        'openpyxl.styles.fills',
        'openpyxl.styles.fonts',
        'openpyxl.styles.borders',
        'openpyxl.styles.alignment',
        'openpyxl.styles.numbers',
        'openpyxl.reader.excel',
        'openpyxl.writer.excel',
        'openpyxl.worksheet.datavalidation',
        'openpyxl.utils',
        'et_xmlfile',
        # ── stdlib extras ────────────────────────────────────────────────────
        'email.mime.multipart',
        'email.mime.base',
        'email.mime.text',
        'csv',
        'io',
        'json',
        'sqlite3',
        'threading',
        'webbrowser',
        'socket',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'scipy', 'IPython',
              'notebook', 'pytest'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Cadence',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # no console window
    icon='static\\icon.ico',
    # Windows version / metadata resource
    version='file_version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Cadence',
)
