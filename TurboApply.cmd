@echo off
setlocal EnableDelayedExpansion
title Turbo Apply - Setup ^& Launch
color 0B
if /i "%~1"=="--check-only" set "TURBO_APPLY_CHECK_ONLY=1"
if /i "%~1"=="--no-launch" set "TURBO_APPLY_CHECK_ONLY=1"
echo.
echo  ========================================
echo    Turbo Apply - One-Click Setup
echo  ========================================
echo.

rem Check for winget
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

rem Refresh PATH with common install locations used by this launcher.
call :refreshpath
goto :after_refreshpath

:refreshpath
set "POWERSHELL_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%POWERSHELL_EXE%" set "POWERSHELL_EXE=powershell"
set "PATH=%PATH%;%APPDATA%\npm;%LOCALAPPDATA%\Programs\Python\Python313;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64;C:\Program Files\MiKTeX\miktex\bin\x64;%ProgramFiles%\Git\cmd;%ProgramFiles(x86)%\Git\cmd;%SystemRoot%;%SystemRoot%\System32;%SystemRoot%\System32\WindowsPowerShell\v1.0"
exit /b 0

:after_refreshpath

rem Check / Install Python
echo  [1/7] Checking Python...

rem Try to find python in PATH or common locations
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
    rem Refresh PATH and find the new Python
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

rem Show which Python we're using
for /f "tokens=*" %%v in ('"%PYTHON%" --version 2^>^&1') do echo        Using: %%v

rem Check / Install pip packages
echo  [2/7] Installing pip packages...
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

rem Check tkinter
echo  [3/7] Checking tkinter...
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

rem Check / Install MiKTeX (pdflatex)
echo  [4/7] Checking pdflatex (MiKTeX)...

set "PDFLATEX="
where pdflatex >nul 2>&1 && set "PDFLATEX=pdflatex"
if not defined PDFLATEX (
    if exist "%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe" set "PDFLATEX=%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"
)
if not defined PDFLATEX (
    if exist "C:\Program Files\MiKTeX\miktex\bin\x64\pdflatex.exe" set "PDFLATEX=C:\Program Files\MiKTeX\miktex\bin\x64\pdflatex.exe"
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
        call :refreshpath
        where pdflatex >nul 2>&1 && set "PDFLATEX=pdflatex"
        if not defined PDFLATEX (
            if exist "%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe" set "PDFLATEX=%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"
        )
        if not defined PDFLATEX (
            if exist "C:\Program Files\MiKTeX\miktex\bin\x64\pdflatex.exe" set "PDFLATEX=C:\Program Files\MiKTeX\miktex\bin\x64\pdflatex.exe"
        )
    )
) else (
    echo        pdflatex OK.
)

echo        Preparing LaTeX packages and fonts...
set "MPM="
where mpm >nul 2>&1 && set "MPM=mpm"
if not defined MPM (
    if exist "%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\mpm.exe" set "MPM=%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\mpm.exe"
)
if not defined MPM (
    if exist "C:\Program Files\MiKTeX\miktex\bin\x64\mpm.exe" set "MPM=C:\Program Files\MiKTeX\miktex\bin\x64\mpm.exe"
)

if defined MPM (
    for %%p in (geometry parskip enumitem hyperref ec cm-super) do (
        "%MPM%" --install=%%p --quiet >nul 2>nul
    )
) else (
    color 0E
    echo  [WARNING] MiKTeX package manager not found. PDF compilation may request packages later.
)

set "INITEXMF="
where initexmf >nul 2>&1 && set "INITEXMF=initexmf"
if not defined INITEXMF (
    if exist "%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\initexmf.exe" set "INITEXMF=%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\initexmf.exe"
)
if not defined INITEXMF (
    if exist "C:\Program Files\MiKTeX\miktex\bin\x64\initexmf.exe" set "INITEXMF=C:\Program Files\MiKTeX\miktex\bin\x64\initexmf.exe"
)

if defined INITEXMF (
    "%INITEXMF%" --set-config-value=[MPM]AutoInstall=1 >nul 2>nul
    "%INITEXMF%" --enable-installer >nul 2>nul
    "%INITEXMF%" --update-fndb >nul 2>nul
    "%INITEXMF%" --mkmaps >nul 2>nul
) else (
    color 0E
    echo  [WARNING] MiKTeX config utility not found. PDF font maps may need manual refresh.
)
echo        LaTeX package prep done.

echo        Running LaTeX smoke test...
"%PYTHON%" "%~dp0latex_to_pdf.py" --self-test >nul 2>nul
if !errorlevel! neq 0 (
    color 0E
    echo  [WARNING] LaTeX smoke test failed. PDF compilation may still fail.
    echo           Run TurboApply.cmd --check-only again, or open MiKTeX Console
    echo           and update/install packages before using Codex.
) else (
    echo        LaTeX smoke test OK.
)

rem Check / Install Git
echo  [5/7] Checking Git...

set "GIT="
where git >nul 2>&1 && set "GIT=found"
if not defined GIT (
    if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT=found"
)
if not defined GIT (
    if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" set "GIT=found"
)

if not defined GIT (
    echo        Git not found. Installing Git...
    echo        This may take a few minutes, please wait...
    winget install --id Git.Git -e --source winget --accept-source-agreements --accept-package-agreements --silent
    if !errorlevel! neq 0 (
        color 0E
        echo  [WARNING] Git install failed. Codex can still run, but diff checks may fail.
        echo           Install manually: https://git-scm.com/download/win
    ) else (
        call :refreshpath
        where git >nul 2>&1 && set "GIT=found"
        if defined GIT (
            echo        Git installed successfully.
        ) else (
            color 0E
            echo  [WARNING] Git installed, but it is not on PATH yet.
            echo           Restart Windows if Codex still says git is unavailable.
        )
    )
) else (
    echo        Git OK.
)

rem Check / Install Codex CLI
echo  [6/7] Checking Codex CLI...

set "CODEX="
where codex >nul 2>&1 && set "CODEX=found"
if not defined CODEX (
    if exist "%APPDATA%\npm\codex.cmd" set "CODEX=found"
)

if not defined CODEX (
    echo        Codex CLI not found. Installing Codex CLI...
    echo        This may take a few minutes, please wait...
    "%POWERSHELL_EXE%" -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"
    if !errorlevel! neq 0 (
        color 0E
        echo  [WARNING] Codex CLI install failed. Generated folders can still open in VS Code.
        echo           Install manually with:
        echo           "%POWERSHELL_EXE%" -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"
    ) else (
        call :refreshpath
        where codex >nul 2>&1 && set "CODEX=found"
        if not defined CODEX (
            if exist "%APPDATA%\npm\codex.cmd" set "CODEX=found"
        )
        if defined CODEX (
            echo        Codex CLI installed successfully.
        ) else (
            color 0E
            echo  [WARNING] Codex CLI installer finished, but codex is not on PATH yet.
            echo           Restart Windows or run the installer command manually if needed.
        )
    )
) else (
    echo        Codex CLI OK.
)

rem Create cookies.txt if missing
if not exist "%~dp0cookies.txt" (
    echo # Netscape HTTP Cookie File> "%~dp0cookies.txt"
    echo # https://cookie-editor.com/ - Export cookies in Netscape format and paste them here>> "%~dp0cookies.txt"
    echo # One cookie per line. Lines starting with # are comments.>> "%~dp0cookies.txt"
    echo        Created empty cookies.txt — paste your browser cookies here if needed.
)

rem Launch GUI
echo  [7/7] Launching Turbo Apply...
echo.
if defined TURBO_APPLY_CHECK_ONLY (
    color 0A
    echo  ========================================
    echo    All set. Check-only mode passed.
    echo  ========================================
    echo.
    exit /b 0
)

color 0A
echo  ========================================
echo    All set. Starting Turbo Apply...
echo  ========================================
echo.

cd /d "%~dp0"

set "PYTHON_GUI="
set "PYTHONW_CANDIDATE="
for /f "usebackq delims=" %%P in (`"%PYTHON%" -c "import pathlib, sys; print(pathlib.Path(sys.executable).with_name('pythonw.exe'))" 2^>nul`) do set "PYTHONW_CANDIDATE=%%P"
if defined PYTHONW_CANDIDATE (
    if exist "!PYTHONW_CANDIDATE!" set "PYTHON_GUI=!PYTHONW_CANDIDATE!"
)
if not defined PYTHON_GUI where pythonw >nul 2>&1 && set "PYTHON_GUI=pythonw"
if not defined PYTHON_GUI set "PYTHON_GUI=%PYTHON%"

set "TURBO_DIR=%~dp0"
set "TURBO_GUI=%~dp0gui.py"
start "" /D "%TURBO_DIR%" "%PYTHON_GUI%" "%TURBO_GUI%"
if !errorlevel! neq 0 (
    color 0C
    echo  [ERROR] Turbo Apply failed to launch.
    pause
)
exit /b 0
