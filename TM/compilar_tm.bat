@echo off
rem Compila el simulador TM de la materia (tm.c, extendido para reales) con gcc de MinGW.
rem Uso: compilar_tm.bat   (desde esta carpeta o desde cualquier otra)
gcc -O2 -static -o "%~dp0tm.exe" "%~dp0tm.c" -lm
if errorlevel 1 (
  echo No se pudo compilar tm.c. Revisa que gcc este en el PATH.
  exit /b 1
)
echo Listo: %~dp0tm.exe
