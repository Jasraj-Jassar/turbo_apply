@echo off
setlocal EnableDelayedExpansion
title Turbo Apply - Setup ^& Launch
color 0B
echo.
echo  ========================================
echo    Turbo Apply - One-Click Setup
echo  ========================================
echo.

:: ── Check for winget ──────────────────────────────────────────────
where winget >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo  [ERROR] winget not found.
    echo  Please install "App Installer" from the Microsoft Store:
    echo  https://aka.ms/getwinget
    echo.
    pause
    exit /b 1
)

:: ── Refresh PATH from registry ────────────────────────────────────
:refreshpath
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYSPATH=%%b"
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USRPATH=%%b"
set "PATH=%SYSPATH%;%USRPATH%;%SystemRoot%;%SystemRoot%\System32"

:: ── Check / Install Python ────────────────────────────────────────
echo  [1/5] Checking Python...

:: Try to find python in PATH or common locations
set "PYTHON="
where python >nul 2>&1 && set "PYTHON=python"
if not defined PYTHON (
    if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
)
if not defined PYTHON (
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)
if not defined PYTHON (
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
)
if not defined PYTHON (
    if exist "C:\Python313\python.exe" set "PYTHON=C:\Python313\python.exe"
)
if not defined PYTHON (
    if exist "C:\Python312\python.exe" set "PYTHON=C:\Python312\python.exe"
)

if not defined PYTHON (
    echo        Python not found. Installing...
    echo        This may take a few minutes, please wait...
    winget install --id Python.Python.3.13 --accept-source-agreements --accept-package-agreements --silent
    if !errorlevel! neq 0 (
        color 0C
        echo  [ERROR] Python installation failed.
        pause
        exit /b 1
    )
    echo        Python installed successfully.
    :: Refresh PATH and find the new Python
    call :refreshpath
    where python >nul 2>&1 && set "PYTHON=python"
    if not defined PYTHON (
        if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    )
    if not defined PYTHON (
        color 0C
        echo  [ERROR] Python installed but cannot be found.
        echo  Please close this window, reopen it, and try again.
        pause
        exit /b 1
    )
)

:: Show which Python we're using
for /f "tokens=*" %%v in ('"%PYTHON%" --version 2^>^&1') do echo        Using: %%v

:: ── Check / Install pip packages ──────────────────────────────────
echo  [2/5] Installing pip packages...
"%PYTHON%" -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    "%PYTHON%" -m ensurepip --upgrade >nul 2>&1
)

if exist "%~dp0requirements.txt" (
    "%PYTHON%" -m pip install -r "%~dp0requirements.txt" --quiet 2>nul
    echo        Done.
) else (
    echo        No requirements.txt found, skipping.
)

:: ── Check tkinter ─────────────────────────────────────────────────
echo  [3/5] Checking tkinter...
"%PYTHON%" -c "import tkinter" >nul 2>&1
if %errorlevel% neq 0 (
    color 0E
    echo  [WARNING] tkinter not available.
    echo  Reinstalling Python with tkinter support...
    winget install --id Python.Python.3.13 --accept-source-agreements --accept-package-agreements --silent --force
    call :refreshpath
    "%PYTHON%" -c "import tkinter" >nul 2>&1
    if !errorlevel! neq 0 (
        color 0C
        echo  [ERROR] tkinter still not available. Reinstall Python manually
        echo  and make sure "tcl/tk and IDLE" is checked during install.
        pause
        exit /b 1
    )
)
echo        tkinter OK.

:: ── Check / Install MiKTeX (pdflatex) ────────────────────────────
echo  [4/5] Checking pdflatex (MiKTeX)...

set "PDFLATEX="
where pdflatex >nul 2>&1 && set "PDFLATEX=found"
if not defined PDFLATEX (
    if exist "%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe" set "PDFLATEX=found"
)
if not defined PDFLATEX (
    if exist "C:\Program Files\MiKTeX\miktex\bin\x64\pdflatex.exe" set "PDFLATEX=found"
)

if not defined PDFLATEX (
    echo        pdflatex not found. Installing MiKTeX...
    echo        This may take several minutes, please wait...
    winget install --id MiKTeX.MiKTeX --accept-source-agreements --accept-package-agreements --silent
    if !errorlevel! neq 0 (
        color 0E
        echo  [WARNING] MiKTeX install failed. LaTeX PDF compilation won't work.
        echo           Install manually: https://miktex.org/download
    ) else (
        echo        MiKTeX installed successfully.
    )
) else (
    echo        pdflatex OK.
)

:: ── Launch GUI ────────────────────────────────────────────────────
echo  [5/5] Launching Turbo Apply...
echo.
color 0A
echo  ========================================
echo    All set! Starting Turbo Apply...
echo  ========================================
echo.

cd /d "%~dp0"
start "" "%PYTHON%" gui.py

timeout /t 3 >nul
exit /b 0
