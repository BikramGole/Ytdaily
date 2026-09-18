$ErrorActionPreference = "Stop"

# Build a portable desktop executable from a clean Windows checkout.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --clean --windowed --name Ytdaily --collect-all PySide6 --collect-all yt_dlp ytdaily/gui/main.py

Write-Host "Built dist\\Ytdaily\\Ytdaily.exe"
Write-Host "Install ffmpeg and ffprobe alongside the executable or add them to PATH."
