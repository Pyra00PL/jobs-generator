@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_COMMAND="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON_COMMAND=py -3.13"

if not defined PYTHON_COMMAND (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_COMMAND=python"
)

if not defined PYTHON_COMMAND (
    echo Nie znaleziono Pythona potrzebnego do zbudowania aplikacji.
    echo Gotowy plik EXE w folderze dist nie wymaga Pythona.
    pause
    exit /b 1
)

if not exist ".build_venv\Scripts\python.exe" (
    echo Tworzenie odizolowanego srodowiska budowania...
    %PYTHON_COMMAND% -m venv .build_venv
    if errorlevel 1 goto build_error
)

call ".build_venv\Scripts\activate.bat"

echo Instalowanie narzedzi budowania...
python -m pip install --disable-pip-version-check -r requirements-build.txt
if errorlevel 1 goto build_error

echo Budowanie RestrictionGenerator.exe...
python -m PyInstaller --noconfirm --clean RestrictionGenerator.spec
if errorlevel 1 goto build_error

echo.
echo Gotowe:
echo %CD%\dist\RestrictionGenerator.exe
pause
exit /b 0

:build_error
echo.
echo Budowanie nie powiodlo sie. Szczegoly bledu znajduja sie powyzej.
pause
exit /b 1
