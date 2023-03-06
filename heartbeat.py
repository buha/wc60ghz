from PyQt6.QtCore import QThread, pyqtSignal
import time


class Heartbeat(QThread):
    pulse = pyqtSignal()

    def __init__(self, str_id: str, seconds: float):
        super().__init__()
        self.seconds = seconds
        self.str_id = str_id

    def run(self):
        while True:
            print("Thread " + self.str_id)
            self.pulse.emit()
            time.sleep(self.seconds)
