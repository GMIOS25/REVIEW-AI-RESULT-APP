# -*- mode: python ; coding: utf-8 -*-
# Đóng gói: pyinstaller build.spec
# Kết quả sinh ra tại dist/ReviewApp.exe (Windows) hoặc dist/ReviewApp (macOS/Linux)

a = Analysis(
    ['app/main.py'],
    pathex=['.'],
    binaries=[],
    # Đóng gói kèm frontend + data mẫu vào trong file .exe.
    # Khi có DB gốc/PDF thật, có thể bỏ 'data' khỏi datas và trỏ config.py
    # ra đường dẫn network share thay vì bundle cứng vào exe.
    datas=[
        ('frontend', 'frontend'),
        ('data', 'data'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ReviewApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,   # False = không hiện cửa sổ dòng lệnh đen khi chạy
    disable_windowed_traceback=False,
    argv_emulation=False,
)
