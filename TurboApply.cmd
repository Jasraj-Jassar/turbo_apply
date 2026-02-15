@echo off
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

:: ── Check / Install Python ────────────────────────────────────────
echo  [1/5] Checking Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo        Python not found. Installing via winget...
    winget install --id Python.Python.3.13 --accept-source-agreements --accept-package-agreements --silent
    if %errorlevel% neq 0 (
        color 0C
        echo  [ERROR] Python installation failed.
        pause
        exit /b 1
    )
    echo        Python installed. Refreshing PATH...
    call refreshenv >nul 2>&1
    :: Force PATH refresh by reading from registry
    for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYSPATH=%%b"
    for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USRPATH=%%b"
    set "PATH=%SYSPATH%;%USRPATH%"
) else (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo        Found: %%v
)

:: Verify python works now
where python >nul 2>&1
if %errorlevel% neq 0 (
    color 0E
    echo.
    echo  [WARNING] Python was installed but PATH hasn't updated yet.
    echo  Please CLOSE this window, open a new terminal, and run this script again.
    echo.
    pause
    exit /b 0
)

:: ── Check / Install pip packages ──────────────────────────────────
echo  [2/5] Checking pip packages...
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo        Installing pip...
    python -m ensurepip --upgrade >nul 2>&1
)

if exist "%~dp0requirements.txt" (
    echo        Installing requirements...
    python -m pip install -r "%~dp0requirements.txt" --quiet
    echo        Done.
) else (
    echo        No requirements.txt found, skipping.
)

:: ── Check tkinter ─────────────────────────────────────────────────
echo  [3/5] Checking tkinter...
python -c "import tkinter" >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo  [ERROR] tkinter is not available.
    echo  Reinstall Python and make sure "tcl/tk and IDLE" is checked.
    echo.
    pause
    exit /b 1
) else (
    echo        tkinter OK.
)

:: ── Check / Install MiKTeX (pdflatex) ────────────────────────────
echo  [4/5] Checking pdflatex (MiKTeX)...
where pdflatex >nul 2>&1
if %errorlevel% neq 0 (
    echo        pdflatex not found. Installing MiKTeX via winget...
    winget install --id MiKTeX.MiKTeX --accept-source-agreements --accept-package-agreements --silent
    if %errorlevel% neq 0 (
        color 0E
        echo  [WARNING] MiKTeX installation failed. LaTeX PDF compilation won't work.
        echo           You can install it manually from https://miktex.org/download
        echo           Continuing without it...
    ) else (
        echo        MiKTeX installed.
        :: Refresh PATH for pdflatex
        for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYSPATH=%%b"
        for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USRPATH=%%b"
        set "PATH=%SYSPATH%;%USRPATH%"
    )
) else (
    echo        pdflatex OK.
)

:: ── Launch GUI ────────────────────────────────────────────────────
echo  [5/5] Launching Turbo Apply...
echo.
echo  ========================================
echo    All checks passed - starting GUI!
echo  ========================================
echo.

cd /d "%~dp0"
start "" python gui.py

:: Keep window open briefly so user can read output
timeout /t 3 >nul
exit /b 0
