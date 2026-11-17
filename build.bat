@echo off
rem ---------------------------------------------------------------
rem  SEQ-16 : assemble le programme et fabrique build\seq16.dsk
rem  Il faut tools\rasm.exe (voir LISEZMOI.md).
rem ---------------------------------------------------------------
if not exist tools\rasm.exe (
  echo Il manque tools\rasm.exe - voir LISEZMOI.md
  exit /b 1
)
if not exist build mkdir build
if exist build\seq16.dsk del build\seq16.dsk
tools\rasm.exe src\main.asm -o build\seq16
if errorlevel 1 (
  echo.
  echo *** ERREUR D'ASSEMBLAGE ***
  exit /b 1
)
echo.
echo OK : build\seq16.dsk est pret.  Sur le CPC : RUN"SEQ16
