@echo off
REM ===================================================================
REM  setup-windows.bat - opsaet norma-robot-bridge paa Windows (cmd)
REM
REM  Forudsaetninger (kan ikke automatiseres - laes scripts\README.md):
REM    1. Python 2.7 + pip + virtualenv installeret
REM    2. NAOqi pynaoqi-SDK pakket ud et permanent sted
REM
REM  Brug:
REM    scripts\setup-windows.bat NAOQI_SDK [PYTHON2_EXE [PYTHONHOME_PATH]]
REM
REM  Standard Python 2.7-installation:
REM    scripts\setup-windows.bat C:\tools\pynaoqi
REM
REM  NAOqi-bundlet Python 2.7 (usaedvanligt layout):
REM    scripts\setup-windows.bat C:\tools\pynaoqi C:\tools\python27-nao\bin\python2.exe C:\tools\python27-nao\lib\python2.7
REM
REM  Idempotent: kan koeres flere gange.
REM ===================================================================

setlocal enabledelayedexpansion

REM ---------- arg-parsing ----------
if "%~1"=="" goto :usage
if /i "%~1"=="-h" goto :usage
if /i "%~1"=="--help" goto :usage
if /i "%~1"=="/?" goto :usage

set NAOQI_SDK=%~1
set PYTHON2_EXE=%~2
set PYTHONHOME_INLINE=%~3

if "%PYTHON2_EXE%"=="" set PYTHON2_EXE=python

REM ---------- validering / detect layout ----------
REM Stoetter to layouts:
REM   1. Standalone pynaoqi-SDK:    ^<sdk^>\lib\python2.7\site-packages\naoqi.py
REM   2. NAOqi-bundlet runtime:     ^<sdk^>\lib\naoqi.py  (SDK og Python i samme mappe)
if exist "%NAOQI_SDK%\lib\python2.7\site-packages\naoqi.py" (
    set NAOQI_SITE=%NAOQI_SDK%\lib\python2.7\site-packages
) else if exist "%NAOQI_SDK%\lib\naoqi.py" (
    set NAOQI_SITE=%NAOQI_SDK%\lib
) else (
    echo FEJL: naoqi.py ikke fundet i hverken:
    echo        %NAOQI_SDK%\lib\python2.7\site-packages\naoqi.py   ^(pynaoqi-SDK^)
    echo        %NAOQI_SDK%\lib\naoqi.py                           ^(NAOqi-bundlet runtime^)
    echo        Tjek at foerste argument peger paa SDK-roden eller den bundlede runtime-mappe.
    exit /b 1
)

REM Find bridge-roden (script lever i scripts\ under bridge-roden)
set BRIDGE_DIR=%~dp0..
pushd "%BRIDGE_DIR%"

echo [1/6] NAOqi-SDK: %NAOQI_SDK%
echo [1/6] Bridge-rod: %CD%
echo [1/6] Python 2.7: %PYTHON2_EXE%
if not "%PYTHONHOME_INLINE%"=="" echo [1/6] PYTHONHOME (inline): %PYTHONHOME_INLINE%
echo.

REM ---------- Python 2.7-tjek ----------
if not "%PYTHONHOME_INLINE%"=="" set PYTHONHOME=%PYTHONHOME_INLINE%

"%PYTHON2_EXE%" --version >nul 2>&1
if errorlevel 1 (
    echo FEJL: '%PYTHON2_EXE%' kan ikke koeres.
    set PYTHONHOME=
    popd
    exit /b 1
)

"%PYTHON2_EXE%" --version 2>&1 | findstr /B "Python 2.7" >nul
if errorlevel 1 (
    echo FEJL: '%PYTHON2_EXE%' er ikke Python 2.7:
    "%PYTHON2_EXE%" --version
    set PYTHONHOME=
    popd
    exit /b 1
)
echo [2/6] Python OK
echo.

REM ---------- virtualenv ----------
echo [3/6] Verificer virtualenv...
"%PYTHON2_EXE%" -m virtualenv --version >nul 2>&1
if errorlevel 1 (
    echo        virtualenv mangler - installerer...
    "%PYTHON2_EXE%" -m pip install "virtualenv<20.22"
    if errorlevel 1 (
        echo FEJL: kunne ikke installere virtualenv
        set PYTHONHOME=
        popd
        exit /b 1
    )
)
echo.

REM ---------- venv ----------
if exist ".venv27\Scripts\python.exe" (
    echo [4/6] .venv27 eksisterer allerede - genbruger.
) else (
    echo [4/6] Opretter .venv27...
    "%PYTHON2_EXE%" -m virtualenv .venv27
    if errorlevel 1 (
        echo FEJL: kunne ikke oprette virtualenv
        set PYTHONHOME=
        popd
        exit /b 1
    )
)
echo.

REM RYD PYTHONHOME - venv'en er nu paa plads og skal ikke have det.
REM Hvis vi lod det vaere sat ville senere kald i scriptet bruge det forkert.
set PYTHONHOME=

REM ---------- installer bridge ----------
echo [5/6] Installerer bridge i venv'en (pip install -e ".[test]")...
.venv27\Scripts\pip.exe install --quiet -e ".[test]"
if errorlevel 1 (
    echo FEJL: pip install fejlede
    popd
    exit /b 1
)
echo        OK
echo.

REM ---------- generer aktiverings-helper ----------
set HELPER=%CD%\activate-with-naoqi.bat
echo [6/6] Genererer %HELPER% ...
(
    echo @echo off
    echo REM Genereret af scripts\setup-windows.bat - skal IKKE commites.
    echo REM Aktiver venv og tilfoej pynaoqi til PYTHONPATH.
    echo REM Brug:  call activate-with-naoqi.bat
    echo call "%%~dp0.venv27\Scripts\activate.bat"
    echo set PYTHONPATH=%NAOQI_SITE%;%%CD%%\src
    echo echo norma-bridge venv + NAOqi klar ^(PYTHONPATH inkluderer pynaoqi^).
) > "%HELPER%"
echo        OK
echo.

REM ---------- verifikation ----------
echo Verificerer NAOqi-import...
.venv27\Scripts\python.exe -c "import sys; sys.path.insert(0, r'%NAOQI_SITE%'); from naoqi import ALProxy; print('       NAOqi-import OK')"
if errorlevel 1 (
    echo FEJL: 'from naoqi import ALProxy' fejlede - tjek SDK-installationen.
    popd
    exit /b 1
)

echo Verificerer pytest...
.venv27\Scripts\python.exe -m pytest tests\ -q
if errorlevel 1 (
    echo FEJL: pytest fejlede
    popd
    exit /b 1
)

echo.
echo ====================================================================
echo   Setup faerdig. Naeste skridt:
echo.
echo     1. copy config\default.ini config\local.ini
echo     2. Rediger config\local.ini og saet [robot] ip = ^<din-robots-IP^>
echo     3. activate-with-naoqi.bat
echo     4. python -m norma_bridge.main --config config\local.ini
echo.
echo   Smoketest mod fysisk robot: tests\manual.md
echo ====================================================================

popd
endlocal
exit /b 0

:usage
echo setup-windows.bat - opsaet norma-robot-bridge paa Windows
echo.
echo Brug:
echo   scripts\setup-windows.bat NAOQI_SDK [PYTHON2_EXE [PYTHONHOME_PATH]]
echo.
echo Argumenter:
echo   NAOQI_SDK         Sti til pynaoqi-SDK-mappen.
echo                     Skal indeholde lib\python2.7\site-packages\naoqi.py
echo   PYTHON2_EXE       Sti til python2.exe (default: 'python' paa PATH)
echo   PYTHONHOME_PATH   Inline PYTHONHOME (KUN naar python2 er NAOqi-bundlet
echo                     med usaedvanligt layout - fx C:\tools\python27-nao)
echo.
echo Eksempler:
echo   scripts\setup-windows.bat C:\tools\pynaoqi
echo   scripts\setup-windows.bat C:\tools\pynaoqi C:\tools\python27-nao\bin\python2.exe C:\tools\python27-nao\lib\python2.7
echo.
echo Se scripts\README.md for fuld kontekst og hvad der skal goeres bagefter.
exit /b 0
