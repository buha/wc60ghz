# This Python file uses the following encoding: utf-8
import sys

from PyQt6 import QtWidgets

from controller import Controller
from window import MainWindow

if __name__ == "__main__":
    controller = Controller()

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(controller)
    window.show()

    app.exec()
    exit()
