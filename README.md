# 📺 Ytdaily
[![License: Unlicense](https://img.shields.io/badge/license-Unlicense-blue.svg)](http://unlicense.org/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Windows%20%7C%20Linux%20%7C%20macOS-blue.svg)](https://www.python.org/)

**Ytdaily** is a high-performance, interactive YouTube automation engine designed for creators and enthusiasts. It transforms your local machine into a smart media server that monitors your favorite channels and playlists, downloading content in crystal-clear quality while applying professional-grade filtering and optimization.

---

## 🖼️ Visual Tour

### 🖥️ Core Interface
| Main Menu | Statistics Dashboard |
| :---: | :---: |
| ![Main Menu](screenshots/main_menu.png) | ![Statistics](screenshots/statistics.png) |

### 🚀 Smart Tracking & Downloads
| Configuration Scan | Scan Results |
| :---: | :---: |
| ![Config Scan](screenshots/config_scan.png) | ![Scan Results](screenshots/scan_results.png) |

### ⚡ Advanced Features
| Parallel Download Progress | Detailed Download Info |
| :---: | :---: |
| ![Parallel Progress](screenshots/parallel_download.png) | ![Download Info](screenshots/download_info.png) |

| Customizable Settings | Playlist Management |
| :---: | :---: |
| ![Settings](screenshots/settings.png) | ![Playlist Management](screenshots/playlist_mgmt.png) |

---

## 🛠️ How it Works: The Architecture

![Workflow Architecture](screenshots/workflow_architecture.png)

`Ytdaily` is built on a "Silent Automation" philosophy. It uses a **State-Based Tracking System** to ensure you never miss a video and never download a duplicate.

### 1. The Intelligent Monitor
The engine maintains a local JSON database of every video it has ever encountered. When a scan starts, it fetches the latest activity from your monitored channels and compares signatures to identify "Gaps" in your collection.

### 2. Parallel Processing Engine
![Parallel Processing Engine](screenshots/parallel_processing_engine.png)

Unlike traditional downloaders that process one file at a time, `Ytdaily` utilizes a multi-threaded parallel downloader. It intelligently distributes your bandwidth across multiple streams to finish your daily queue in minutes rather than hours.

### 3. The SponsorBlock Integration
Every download is automatically scrubbed of non-content segments (Sponsors, Intros, Outros, Interaction Reminders) using the SponsorBlock API, saving you hours of watch time.

---

## 🚀 One-Click Installation

Designed to work across **Arch, Debian, Ubuntu, and Fedora** based distributions. The installer handles system dependencies, Python environment isolation (PEP 668), and shell integration.

```bash
git clone https://github.com/DevXtechnic/Ytdaily.git
cd Ytdaily
chmod +x install.sh
./install.sh
```

### What the installer does:
- Checks for and installs `yt-dlp`, `ffmpeg`, and `python-rich` using your native package manager.
- Sets up a robust directory structure in `~/.local/share/Ytdaily/`.
- Injects `Ytdaily` aliases into your shell (`bash`, `zsh`, or `fish`).
- **Initializes the Automation Engine (Systemd).**

---

## ⏰ The Automation Engine (Systemd)

After installation, `Ytdaily` operates as a silent background service. 

- **Trigger**: The service runs once every 24 hours.
- **Boot Safety**: It includes a **5-minute delay** after your system boots to ensure network stability before starting the scan.
- **Resource Management**: Uses `Nice=19` and `IOSchedulingClass=idle` to ensure it never slows down your PC while you are working.

You can check the status of your automated downloader at any time:
```bash
systemctl --user status Ytdaily.service
```

---

## 🖥️ Desktop GUI and Windows

The new PySide6 desktop application works on Windows, Linux, and macOS. It provides a dashboard, channel and playlist management, one-off MP4/MP3 downloads with live progress and cancellation, history search, configurable folders, and a system-tray menu.

### Windows quick start

1. Install Python 3.9+ and select **Add Python to PATH** during installation.
2. Clone this repository, then run `install_windows.bat`.
3. Install [FFmpeg](https://ffmpeg.org/download.html) and ensure `ffmpeg` and `ffprobe` are on `PATH`.
4. Run `py -m ytdaily.main --gui`.

Windows state and logs are kept in `%LOCALAPPDATA%\Ytdaily`; download folders are configurable in the GUI. To make a portable `.exe` from Windows, run `powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1`. Every push to `main` also creates a Windows build artifact through GitHub Actions.

On Linux or macOS, after installing the Python requirements, use `python -m ytdaily.main --gui` (or the installed `ytdaily-gui` command).

---

## ✨ Key Features

- 🎯 **Multi-Quality Support**: Target any resolution from 360p to 4K (2160p).
- 📻 **Podcast Automation**: Automatically converts specific sources to high-fidelity 320kbps MP3s.
- 🍪 **Smart Cookie Auth**: Auto-detects your browser (Brave, Chrome, Chromium, Firefox, Edge, Opera, Vivaldi) and uses its cookies to bypass YouTube's bot detection. Fully configurable — set a specific browser or disable via `none`.
- 🧹 **Dynamic Cleanup**: Set a retention policy (e.g., 60 days) to keep your storage lean.
- 🌍 **Subtitles & Metadata**: Embeds official and auto-generated subtitles, thumbnails, and metadata into the MP4 container.

---

## 📜 Technical Stack

- **Logic**: Python 3
- **UI**: Rich terminal UI and PySide6 desktop GUI
- **Engine**: yt-dlp & FFmpeg
- **Scheduling**: Systemd User Timers
- **Package Management**: Native Linux Bridge (Pacman/Apt/Dnf)

---

## ⚖️ License

[Unlicense](LICENSE) (Public Domain) - Free to use, modify, and distribute for any purpose.
