@echo off
setlocal
cd /d "%~dp0"
title Aspect Insight

echo.
echo   Aspect Insight - runs entirely on this computer
echo   ----------------------------------------------
echo   App:        http://127.0.0.1:8000
echo   Admin:      http://127.0.0.1:8000/admin
echo   Extension:  chrome://extensions ^> Developer mode ^> Load unpacked ^> "%~dp0extension"
echo.

if not exist "frontend\dist\index.html" (
  echo   Building the web app once...
  pushd frontend
  call npm install --no-audit --no-fund || goto :error
  call npm run build || goto :error
  popd
)

start "" cmd /c "timeout /t 35 /nobreak >nul & start http://127.0.0.1:8000"
echo   Loading the models (about 30 seconds)...
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
goto :eof

:error
echo   Building the web app failed. Install Node.js 18 or newer and run Start.bat again.
pause
