@echo off
setlocal

where py >nul 2>nul
if errorlevel 1 (
  echo Python 3.9 or newer is required. Install it from https://www.python.org/downloads/windows/
  exit /b 1
)

py -m pip install --upgrade pip
py -m pip install -r requirements.txt
echo.
echo Installation complete. Run this command to start the desktop app:
echo   py -m ytdaily.main --gui
echo.
echo yt-dlp, ffmpeg and ffprobe must be available on PATH for downloads.
endlocal
