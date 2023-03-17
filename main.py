# This Python file uses the following encoding: utf-8
import sys
import traceback

from PyQt6 import QtWidgets

from controller import Controller
from logger import *
from window import MainWindow

if __name__ == "__main__":
    logger = Logger()
    controller = Controller(logger)

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(controller, logger)
    window.show()

    try:
        app.exec()
    except Exception as e:
        logger.write(LogType.ERROR, traceback.format_exc())

    exit()
