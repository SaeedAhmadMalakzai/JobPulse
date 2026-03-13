# PyInstaller spec for JobPulse (GUI + bot). Build: pyinstaller jobpulse.spec
# Use a clean venv with only requirements.txt (PySide6-Essentials) to avoid full PySide6 (~126 MB).

import sys

block_cipher = None

# Exclude unused stdlib and heavy optional deps (do not exclude distutils — setuptools hook needs it)
_excludes_stdlib = [
    'tkinter', 'test', 'unittest', 'ensurepip', 'lib2to3',
    'pydoc', 'idlelib',
    'IPython', 'numpy', 'pygments', 'pytest', 'sphinx', 'PIL', 'matplotlib', 'pandas',
]

a = Analysis(
    ['src/gui/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('.env.example', '.'),
    ],
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
    excludes=_excludes_stdlib,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Drop unused Qt libs (we only need Core, Gui, Widgets, Network for SSL/QProcess)
_qt_skip = (
    'Qt6Svg', 'Qt6Sql', 'Qt6Test', 'Qt6Xml', 'Qt6Help', 'Qt6Designer', 'Qt6Qml', 'Qt6Quick',
    'Qt63D', 'Qt6Multimedia', 'Qt6Positioning', 'Qt6Location', 'Qt6Sensors', 'Qt6SerialPort',
    'Qt6WebEngine', 'Qt6Charts', 'Qt6DataVisualization', 'Qt6Bluetooth', 'Qt6Nfc',
    'Qt6RemoteObjects', 'Qt6Scxml', 'Qt6StateMachine', 'Qt6Pdf', 'Qt6ShaderTools', 'Qt6UiTools',
    'Qt6WebChannel', 'Qt6WebSockets', 'Qt6HttpServer',
)
def _keep_binary(bin_item):
    dest = bin_item[0] if isinstance(bin_item[0], str) else ''
    return not any(skip in dest for skip in _qt_skip)
a.binaries = [x for x in a.binaries if _keep_binary(x)]

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
    strip=True,
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
