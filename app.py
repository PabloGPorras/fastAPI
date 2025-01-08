import sys
from threading import Thread
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl  # Import QUrl
from uvicorn import Config, Server

# Import your FastAPI app
from main import app  # Replace 'main' with your FastAPI app module


class FastAPIServer(Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True  # Ensure the thread exits when the main program exits

    def run(self):
        config = Config(app=app, host="127.0.0.1", port=8000, log_level="info")
        server = Server(config)
        server.run()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FastAPI in PyQt6")

        # WebEngineView to load the FastAPI app
        self.web_view = QWebEngineView()
        self.web_view.setUrl(QUrl("http://127.0.0.1:8000/table/requests"))

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.web_view)

        # Set central widget
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)


if __name__ == "__main__":
    # Start FastAPI server in a separate thread
    fastapi_server = FastAPIServer()
    fastapi_server.start()

    # Start the PyQt6 application
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
