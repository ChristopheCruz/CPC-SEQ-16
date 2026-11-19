@echo off
rem ---------------------------------------------------------------
rem  SEQ-16 : assemble le programme et fabrique build\seq16.dsk
rem  Il faut tools\rasm.exe (voir README.fr.md).
rem ---------------------------------------------------------------
if not exist tools\rasm.exe (
  echo Il manque tools\rasm.exe - voir README.fr.md
  exit /b 1
)
if not exist build mkdir build
if exist build\seq16.dsk del build\seq16.dsk
rem -s : fichier des etiquettes build\seq16.sym (pour les tests)
tools\rasm.exe src\main.asm -o build\seq16 -s
if errorlevel 1 (
  echo.
  echo *** ERREUR D'ASSEMBLAGE ***
  exit /b 1
)
rem Ajoute les banques de samples (.SMP) et d'instruments (.INS)
rem (il faut Python 3)
python tools\amsdsk.py build\seq16.dsk samples\DRUMS.SMP samples\VOIX.SMP samples\BATTERI2.SMP samples\PERCUS.SMP samples\EFFETS.SMP samples\BASSES.SMP samples\NOTES.SMP samples\CHIFFRES.SMP samples\MOTS.SMP
if errorlevel 1 goto pas_python
python tools\amsdsk.py build\seq16.dsk instruments\USINE.INS instruments\BATTERIE.INS instruments\BASSES.INS instruments\LEADS.INS instruments\NAPPES.INS instruments\ARPEGES.INS instruments\EFFETS.INS instruments\BUZZER.INS instruments\CLAVIERS.INS instruments\CHIPTUNE.INS instruments\PERCUS.INS instruments\GLISSES.INS instruments\BRUITS.INS
if errorlevel 1 goto pas_python
rem Versions anglaise et espagnole : build\seq16-en.dsk, build\seq16-es.dsk
python tools\lang.py en es --rasm tools\rasm.exe
if errorlevel 1 (
  echo.
  echo *** VERSIONS ANGLAISE ET ESPAGNOLE NON FABRIQUEES ***
  exit /b 1
)
rem Disquettes de banques seules : build\seq16-sons.dsk, build\seq16-samples.dsk
python tools\bank_disks.py
if errorlevel 1 goto pas_python
rem Motifs d'usine (.PAT) : build\seq16-motifs-mono.dsk, seq16-motifs-poly.dsk
python tools\gen_patterns.py
if errorlevel 1 goto pas_python
echo.
echo OK : build\seq16.dsk (francais), seq16-en.dsk (English), seq16-es.dsk (espanol).
echo      build\seq16-sons.dsk et seq16-samples.dsk : les banques seules.
echo      build\seq16-motifs-mono.dsk et seq16-motifs-poly.dsk : les motifs (f3 P).
echo Sur le CPC : RUN"SEQ16
exit /b 0
:pas_python
echo.
echo *** BANQUES NON AJOUTEES : Python 3 est-il installe ? ***
exit /b 1
