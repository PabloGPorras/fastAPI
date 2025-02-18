import os
import sys
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest
from PyQt6.QtCore import QUrl
import uvicorn
from core.get_table_name import get_table_name
from main import app

# 1) Custom QThread to run Uvicorn in a non-blocking way
class UvicornThread(QThread):
    server_stopped = pyqtSignal()  # Signal to indicate the server has stopped

    def run(self):
        """
        Start the FastAPI server asynchronously.
        """
        config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="info")
        self.server = uvicorn.Server(config)
        self.server.run()

    def stop(self):
        """
        Gracefully shut down the FastAPI server.
        """
        if hasattr(self, 'server'):
            self.server.should_exit = True  # Signal Uvicorn to stop
        self.quit()  # Exit the QThread


# 2) Define the PyQt6 Window containing a QWebEngineView
class MainWindow(QMainWindow):
    def __init__(self, server_thread):
        super().__init__()
        self.setWindowTitle("RMS")

        self.server_thread = server_thread  # Store reference to the server thread

        # Create QWebEngineView
        self.web_view = QWebEngineView()

        # Load the local FastAPI page
        self.web_view.load(QUrl(f"http://127.0.0.1:8000/table/{get_table_name('requests')}"))

        # Connect the downloadRequested signal
        profile = self.web_view.page().profile()
        profile.downloadRequested.connect(self.on_downloadRequested)

        self.setCentralWidget(self.web_view)

    def on_downloadRequested(self, download: QWebEngineDownloadRequest):
        # Specify a download directory and filename
        download.setDownloadDirectory(fr"C:\Users\{os.getlogin()}\Downloads")
        download.setDownloadFileName(download.downloadFileName())
        download.accept()

    def closeEvent(self, event):
        """
        Ensures the Uvicorn server stops when the application closes.
        """
        self.server_thread.stop()
        event.accept()  # Proceed with closing the window


def main():
    # 3) Create the PyQt Application
    qt_app = QApplication(sys.argv)

    # 4) Start the Uvicorn server in a separate PyQt thread
    server_thread = UvicornThread()
    server_thread.start()

    # 5) Create the main window
    window = MainWindow(server_thread)
    window.show()

    # 6) Start the PyQt event loop
    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
