from PyQt6.QtCore import QThread, pyqtSignal
from core.downloader import CoreDownloader

class DownloadSyncWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.core = CoreDownloader()
        
    def run(self):
        try:
            self.core.run_auto_download()
            self.finished.emit("Sync completed successfully.")
        except Exception as e:
            self.error.emit(str(e))

class DirectDownloadWorker(QThread):
    finished = pyqtSignal(bool, str)
    
    def __init__(self, url: str, media_type: str = "video"):
        super().__init__()
        self.url = url
        self.media_type = media_type
        self.core = CoreDownloader()
        
    def run(self):
        try:
            success, msg = self.core.download_direct_url(self.url, self.media_type)
            self.finished.emit(success, msg)
        except Exception as e:
            self.finished.emit(False, str(e))
