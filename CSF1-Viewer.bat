@echo off
set CSF1_VIEWER_EDITION=Windows
cd /d "%~dp0"
where py >nul 2>&1 && set PY=py && goto run
where python >nul 2>&1 && set PY=python && goto run
echo Python 3 is required. Install from https://www.python.org/downloads/
echo Check tcl/tk during setup.
pause
exit /b 1
:run
%PY% jck_version.py
%PY% -c "import tkinter" >nul 2>&1
if %ERRORLEVEL%==0 (
  %PY% csf1_viewer.py --tk %*
) else (
  %PY% csf1_viewer.py --web %*
)
