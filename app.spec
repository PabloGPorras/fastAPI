# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules
from pathlib import Path

# Base directory of your project
import os
base_dir = Path(os.getcwd()).resolve()

# List of template/component directories (source path, destination path inside the bundle)
template_dirs = [
    ("templates", "templates"),
    ("features/bulk_upload/components", "features/bulk_upload/components"),
    ("features/darkmode/components", "features/darkmode/components"),
    ("features/performance_metrics/components", "features/performance_metrics/components"),
    ("features/form/components", "features/form/components"),
    ("features/comment_item/components", "features/comment_item/components"),
    ("features/form_comments/components", "features/form_comments/components"),
    ("features/form_field_search/components", "features/form_field_search/components"),
    ("features/form_checklist/components", "features/form_checklist/components"),
    ("features/form_fields/components", "features/form_fields/components"),
    ("features/form_subtable/components", "features/form_subtable/components"),
    ("features/form_headers/components", "features/form_headers/components"),
    ("features/table/components", "features/table/components"),
    ("features/table_filters/components", "features/table_filters/components"),
    ("features/table_manage_columns/components", "features/table_manage_columns/components"),
]

# Only include directories that actually exist
datas = [
    (str(base_dir / src), dst)
    for src, dst in template_dirs
    if (base_dir / src).exists()
]

a = Analysis(
    ['app.py'],  # Your FastAPI entry point
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
