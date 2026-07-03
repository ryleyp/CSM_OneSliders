# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for EA Slide Builder.
# Build on the TARGET platform (build the .exe on Windows):
#     pyinstaller packaging/ea-slide-builder.spec
# from the project root, with the venv active. See packaging/BUILD_EXE.md.

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

project = Path(SPECPATH).parent

datas = [
    (str(project / "app.py"), "."),
    (str(project / "data_processor.py"), "."),
    (str(project / "screenshot_reader.py"), "."),
    (str(project / "slide_builder.py"), "."),
    (str(project / "insights.py"), "."),
    (str(project / "preview.py"), "."),
    (str(project / "profiles.py"), "."),
    (str(project / ".streamlit"), ".streamlit"),
]
# Streamlit needs its static frontend + package metadata inside the bundle.
datas += collect_data_files("streamlit")
for pkg in ("streamlit", "pandas", "python-pptx", "openpyxl", "pytesseract",
            "Pillow", "altair", "pyarrow"):
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

hiddenimports = [
    "streamlit.runtime.scriptrunner.magic_funcs",
    "pandas", "openpyxl", "pptx", "pytesseract", "PIL",
]

a = Analysis(
    [str(project / "packaging" / "run_app.py")],
    pathex=[str(project)],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="EA Slide Builder",
    console=True,   # keep the console: it shows status and holds the server
    icon=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="EA Slide Builder",
)
