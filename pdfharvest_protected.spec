# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

tqjnphnu = Analysis(
    ['main.py'],  # Main script
    pathex=[],
    binaries=[],
    datas=[('invoice_templates.db', '.'), ('*.json', '.'), ('user_management.db.enc', '.'), ('.db_salt', '.'), ('.license_salt', '.')],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'pandas',
        'numpy',
        'fitz',
        'pypdf_table_extraction',
        'sqlite3',
        'json',
        'datetime',
        'uuid',
        'hashlib',
        'platform',
        'socket',
        'requests',
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'base64',
        'shutil',
        'zlib',
        'binascii',
        'activation_dialog',
        'license_manager',
        'db_protection',
        'license_generator'
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

mvkgxvqj = PYZ(tqjnphnu.pure, tqjnphnu.zipped_data, cipher=block_cipher)

jottyfjn = EXE(
    mvkgxvqj,
    tqjnphnu.scripts,
    [],
    exclude_binaries=True,
    name='PDFHarvest',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to False for GUI applications
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

scaasooj = COLLECT(
    jottyfjn,
    tqjnphnu.binaries,
    tqjnphnu.zipfiles,
    tqjnphnu.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PDFHarvest',
)
