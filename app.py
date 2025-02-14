import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest
from PyQt6.QtCore import QUrl
import threading
import uvicorn
from database import get_table_name
from main import app

# 2) Function to run Uvicorn in a thread
def run_server():
    """
    This function starts the uvicorn server with our FastAPI 'app'.
    We'll run it in a separate thread so it doesn't block the GUI.
    """
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


# 3) Define the PyQt6 Window containing a QWebEngineView
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RMS")

        # Create QWebEngineView
        self.web_view = QWebEngineView()

        # Load the local FastAPI page
        self.web_view.load(QUrl(f"http://127.0.0.1:8000/table/{get_table_name('requests')}"))

        # Connect the downloadRequested signal
        profile = self.web_view.page().profile()
        profile.downloadRequested.connect(self.on_downloadRequested)

        self.setCentralWidget(self.web_view)

    def on_downloadRequested(self, download: QWebEngineDownloadRequest):
        # For example, specify a file path or directory
        download.setDownloadDirectory(r"C:\Users\pablo\Downloads")
        download.setDownloadFileName(download.downloadFileName())
        download.accept()  


def main():
    # 4) Spin up the FastAPI server in a background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 5) Create the PyQt Application
    qt_app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    # 6) Start the PyQt event loop
    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()