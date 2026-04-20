# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Cadence — one-folder build, no console window.

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static',    'static'),
    ],
    hiddenimports=[
        # pystray Windows backend
        'pystray._win32',
        # Pillow
        'PIL._imaging',
        'PIL.Image',
        'PIL.ImageDraw',
        # Flask / Jinja2 / Werkzeug internals
        'jinja2.ext',
        'jinja2.loaders',
        'werkzeug.serving',
        'werkzeug.routing',
        'werkzeug.middleware.shared_data',
        # msal / requests
        'msal',
        'msal.application',
        'msal.authority',
        'msal.token_cache',
        'requests',
        'requests.adapters',
        # ReportLab
        'reportlab.platypus',
        'reportlab.lib.pagesizes',
        'reportlab.lib.units',
        'reportlab.lib.colors',
        'reportlab.lib.styles',
        'reportlab.lib.enums',
        # stdlib odds and ends
        'email.mime.multipart',
        'email.mime.base',
        'email.mime.text',
        'csv',
        'io',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'scipy'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    console=False,          # ← no command window
    icon='static\\icon.ico',
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
