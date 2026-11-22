# -*- mode: python ; coding: utf-8 -*-
# Specifica PyInstaller di KILLA NEWS.
# Uso (dalla cartella principale del progetto):
#   pyinstaller --clean -y installer/killa_news.spec                      -> dist/KillaNews/  (per l'installatore)
#   set KILLANEWS_ONEFILE=1 && pyinstaller --clean -y installer/killa_news.spec  -> dist/KillaNews_Portatile.exe
import glob
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
ONEFILE = os.environ.get("KILLANEWS_ONEFILE") == "1"

datas = [
    (os.path.join(ROOT, "data", "*.json"), "data"),
    (os.path.join(ROOT, "data", "novita.md"), "data"),
    (os.path.join(ROOT, "assets", "*.ico"), "assets"),
    (os.path.join(ROOT, "assets", "*.png"), "assets"),
]
binaries = [(dll, "lib") for dll in glob.glob(os.path.join(ROOT, "lib", "*.dll"))]
hiddenimports = ["win32com", "win32com.client", "pythoncom", "pywintypes", "wx.adv", "wx.html"]
for pkg in ("trafilatura", "justext", "htmldate", "courlan"):
    try:
        datas += collect_data_files(pkg)
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "numpy.tests", "PIL.ImageQt"],
    noarchive=False,
)
pyz = PYZ(a.pure)

common = dict(
    name="KillaNews_Portatile" if ONEFILE else "KillaNews",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.join(ROOT, "assets", "killa_news.ico"),
    version=os.path.join(ROOT, "installer", "version_info.txt"),
)

if ONEFILE:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], runtime_tmpdir=None, **common)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **common)
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="KillaNews")
