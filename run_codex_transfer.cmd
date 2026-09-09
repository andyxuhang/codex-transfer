@echo off
setlocal
set "APP=%~dp0codex_transfer.py"
set "BUNDLED=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
set "PYTHON_EXE="
if exist "%BUNDLED%" set "PYTHON_EXE=%BUNDLED%"
if not defined PYTHON_EXE where pythonw.exe >nul 2>nul && set "PYTHON_EXE=pythonw.exe"
if not defined PYTHON_EXE where python.exe >nul 2>nul && set "PYTHON_EXE=python.exe"
if not defined PYTHON_EXE where pyw.exe >nul 2>nul && set "PYTHON_EXE=pyw.exe"
if not defined PYTHON_EXE (
  echo Python 3.9 or newer was not found.
  echo Install Python from https://www.python.org/downloads/windows/
  pause
  exit /b 2
)
start "Codex Transfer" "%PYTHON_EXE%" "%APP%"
