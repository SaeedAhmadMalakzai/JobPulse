# PyInstaller spec for JobPulse (GUI + bot). Build: pyinstaller jobpulse.spec
# Output: dist/JobPulse/ (Windows/Linux) or dist/JobPulse.app (macOS). One-folder so Playwright can install Chromium next to app.

import sys

block_cipher = None

# Collect all of src so that --run-bot (same executable) can import src.main and all adapters
a = Analysis(
    ['src/gui/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('.env.example', '.'),
    ] + Tree('src', prefix='src', excludes=['__pycache__', '*.pyc']),
    hiddenimports=[
        'src.main',
        'src.config',
        'src.runner',
        'src.log',
        'src.applied_store',
        'src.job_utils',
        'src.cover_letter',
        'src.email_utils',
        'src.alerts',
        'src.form_filler',
        'src.captcha_solver',
        'src.job_page_utils',
        'src.apply_helper',
        'dotenv',
        'playwright',
        'requests',
        'bs4',
        'lxml',
        'PySide6',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='JobPulse',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='JobPulse',
)

# macOS: wrap in .app bundle so users get JobPulse.app to double-click (BUNDLE is a spec-file global)
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='JobPulse.app',
        icon=None,
        bundle_identifier='af.jobpulse.app',
        version='1.0.0',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'CFBundleName': 'JobPulse',
            'CFBundleDisplayName': 'JobPulse',
        },
    )
