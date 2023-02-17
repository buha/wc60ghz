# This Python file uses the following encoding: utf-8
import sys
from PyQt6 import QtWidgets
from window import MainWindow

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()

    app.exec()
