# PyInstaller-Spec fuer den Dialekt-Vokabel-Manager.
# Aus dem app/-Verzeichnis aufrufen:  pyinstaller --clean --noconfirm dialekt-app.spec
# Erzeugt eine einzelne, fensterbasierte Windows-.exe in app/dist/.

block_cipher = None

a = Analysis(
    ['dialekt_app.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=['core', 'core.model', 'core.importer', 'core.site'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='dialekt-vokabel-manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,   # keine Konsole - reine GUI
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
