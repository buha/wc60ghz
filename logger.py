import os
from datetime import datetime


class LogType:
    DEFAULT = 0
    IIO_DEVICE = 1
    WARNING = 2
    ERROR = 3
    UI = 4


class Logger:
    def __init__(self):
        self.file_name = self.__get_name("logs")
        self.max_file_size = 5  # size in MB

    @staticmethod
    def __get_name(default_name: str) -> str:
        return "logs/" + default_name + ".txt"

    @staticmethod
    def __make_log_info(log_type: LogType) -> str:
        info: str
        if log_type == LogType.IIO_DEVICE:
            info = "--- IIO Device: "
        elif log_type == LogType.WARNING:
            info = "--- Warning: "
        elif log_type == LogType.ERROR:
            info = "--- Error: "
        elif log_type == LogType.UI:
            info = "--- UI: "
        else:
            info = "--- Message: "

        info += datetime.now().strftime("%d-%m-%Y  %H:%M:%S:%f") + "\n"
        return info

    def __check_file_size(self):
        size = os.stat(self.file_name).st_size / (1024 * 1024)
        if size > self.max_file_size:
            tmp_file = self.file_name + ".tmp"
            lines_to_remove = int((size - self.max_file_size) * 0.1 / self.max_file_size *
                                  sum(1 for _ in open(self.file_name)))
            lines = []

            with open(self.file_name) as f, open(tmp_file, "w") as out:
                for x in range(lines_to_remove):
                    lines.append(next(f))
                for line in f:
                    out.write(line)

            os.replace(tmp_file, self.file_name)

    def write(self, log_type: LogType = None, log: str = ""):
        file = open(self.file_name, "a")

        file.write(self.__make_log_info(log_type) + log + "\n\n\n")
        file.close()

        self.__check_file_size()
