import os
import json
from flask import Flask, jsonify, request, send_from_directory
from YT_daily import YouTubeFeedDownloader, Config
from pathlib import Path
from datetime import datetime
import threading

app = Flask(__name__, static_folder='.', static_url_path='')

@app.route('/')
def index():
    # Serve index.html which will be the modified prototype.html
    return app.send_static_file('index.html')

@app.route('/api/dashboard')
def dashboard_api():
    config = Config()
    downloader = YouTubeFeedDownloader(config)
    
    # Calculate some metrics
    videos_dir = config.base_video_dir
    total_size = 0
    if videos_dir.exists():
        for f in videos_dir.rglob('*'):
            if f.is_file():
                total_size += f.stat().st_size
    
    storage_gb = round(total_size / (1024**3), 2)
    
    history = downloader.channel_history
    downloaded_today = 0
    recent_videos = []
    
    today_str = datetime.now().isoformat()[:10]
    
    for ch, data in history.get('channels', {}).items():
        for vid in data.get('downloaded_videos', []):
            vid_date = vid.get('downloaded_at', '')[:10]
            if vid_date == today_str:
                downloaded_today += 1
            recent_videos.append({
                'title': vid.get('title', 'Unknown'),
                'channel': ch,
                'date': vid.get('downloaded_at', ''),
            })
            
    recent_videos.sort(key=lambda x: x['date'], reverse=True)
    recent_videos = recent_videos[:5]
    
    return jsonify({
        'downloaded_today': downloaded_today,
        'active_queue': 0, 
        'storage_allocated': f"{storage_gb} GB",
        'recent_downloads': recent_videos
    })

@app.route('/api/library')
def library_api():
    config = Config()
    downloader = YouTubeFeedDownloader(config)
    library = []
    for ch, data in downloader.channel_history.get('channels', {}).items():
        for vid in data.get('downloaded_videos', []):
            library.append({
                'title': vid.get('title', 'Unknown'),
                'channel': ch,
                'date': vid.get('downloaded_at', '')
            })
    return jsonify(library)

@app.route('/api/sync', methods=['POST'])
def sync_api():
    # Run sync in background to avoid blocking
    def run_sync():
        config = Config()
        downloader = YouTubeFeedDownloader(config)
        downloader.run_auto_download()
    
    thread = threading.Thread(target=run_sync)
    thread.start()
    return jsonify({'status': 'Sync started'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
