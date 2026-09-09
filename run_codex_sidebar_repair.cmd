@echo off
setlocal
cd /d "%~dp0"
set "PYTHON_EXE="
for %%P in (py.exe python.exe) do if not defined PYTHON_EXE for /f "delims=" %%I in ('where %%P 2^>nul') do if not defined PYTHON_EXE set "PYTHON_EXE=%%I"
if not defined PYTHON_EXE (
  echo Python 3.9 or later is required for the source version.
  echo Please download the portable EXE from GitHub Releases instead.
  pause
  exit /b 2
)
"%PYTHON_EXE%" "%~dp0codex_sidebar_repair.py"
if errorlevel 1 pause
