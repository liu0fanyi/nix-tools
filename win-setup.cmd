@echo off
setlocal
cd /d "%~dp0"

where nu >nul 2>nul
if errorlevel 1 (
  echo ERROR: Nushell ^(nu^) was not found in PATH.
  pause
  exit /b 1
)

nu clipboard-sync\setup-windows.nu --from-ci
if errorlevel 1 (
  echo.
  echo clipboard-sync setup failed. See the error above.
  pause
  exit /b 1
)

echo.
echo clipboard-sync setup completed successfully.
endlocal
