@echo off
rem ============================================================
rem  Construit l'executable Windows de l'editeur de banques
rem  SEQ-16 (seq16-sampler.exe) depuis un PC Windows.
rem
rem  Pre-requis : Python 3.10+ (avec tkinter) depuis python.org
rem  L'executable est genere dans tools\dist\
rem  Lance depuis la racine du depot, il y propose samples\ et
rem  build\seq16.dsk par defaut (dossier courant).
rem ============================================================

cd /d "%~dp0"
python -m pip install --upgrade pyinstaller
python -m PyInstaller --onefile --windowed --clean --name seq16-sampler smp_gui.py --add-data "fonts;fonts"

if exist dist\seq16-sampler.exe (
    echo.
    echo OK : executable genere dans tools\dist\seq16-sampler.exe
) else (
    echo.
    echo ECHEC : la generation a echoue, voyez le journal plus haut.
)
pause
