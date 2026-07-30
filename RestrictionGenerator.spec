from pathlib import Path


project_root = Path.cwd()

analysis = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / "assets"), "assets"),
        (str(project_root / "config"), "config"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

python_archive = PYZ(analysis.pure)

executable = EXE(
    python_archive,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="RestrictionGenerator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(
        project_root
        / "packaging"
        / "windows_version_info.txt"
    ),
)
