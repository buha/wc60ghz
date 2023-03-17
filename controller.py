import glob
import sys
import traceback

import iio
import serial
from PySide6.QtSerialPort import QSerialPortInfo
from iio import Context

from logger import *
from resouces import TEST_DEVICE, TEST_ATTR


class Controller:
    __iio_ctx = None

    def __init__(self, logger: Logger) -> None:
        self.__iio_ctx: Context()
        self.__logger = logger
        self.__ctx_config = ""

    @staticmethod
    def from_GHz_to_Hz(value: str) -> str | None:
        try:
            return str(int(float(value) * 1000000))
        except ValueError:
            return None

    @staticmethod
    def from_Hz_to_GHz(value: str) -> str | None:
        try:
            return str(int(value) / 1000000)
        except ValueError:
            return None

    @staticmethod
    def temp_range(temp: int) -> str:
        if temp in range(0, 2):
            return "(below -20 °C)"
        elif temp in range(3, 6):
            return "(-20...+10 °C)"
        elif temp in range(7, 15):
            return "(+10...+45 °C)"
        else:
            return "(above +45 °C)"

    def __get_serial_ports(self) -> list[str]:
        platform = sys.platform
        if platform.startswith("win"):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif platform.startswith("linux"):
            ports = glob.glob("/dev/tty[A-Za-z]*")
        else:
            raise EnvironmentError("Unsupported platform")

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                self.__logger.write(LogType.ERROR, traceback.format_exc())
        return result

    def get_uri(self):
        return str(self.__ctx_config)
    @staticmethod
    def get_ports() -> list:
        return [port.portName() for port in QSerialPortInfo.availablePorts()]

    def valid_ctx(self) -> (bool, str):
        if self.__iio_ctx is None:
            return False, ""

        try:
            self.__iio_ctx.find_device(TEST_DEVICE).attrs.get(TEST_ATTR).value
        except Exception as e:
            return False, str(e)

        return True, ""

    def remove_ctx(self):
        if self.__iio_ctx is not None:
            del self.__iio_ctx
            self.__iio_ctx = None

            self.__logger.write(LogType.IIO_DEVICE, "Closed context: {}".format(self.__ctx_config))
            self.__ctx_config = ""

    def __safe_exec(self, func):
        try:
            return func()
        except:
            self.__logger.write(LogType.ERROR, traceback.format_exc())
            if not self.valid_ctx()[0]:
                self.remove_ctx()

    def get_device_attrs(self, device: str) -> {}:
        return self.__safe_exec(lambda: self.__iio_ctx.find_device(device).attrs)

    def get_device_ch_attr(self, device: str, ch: str, attr: str) -> iio.ChannelAttr:
        return self.__safe_exec(lambda: self.__iio_ctx.find_device(device).find_channel(ch).attrs.get(attr))

    def reg_write(self, device: str, reg: int, value: int):
        self.__safe_exec(lambda: self.__iio_ctx.find_device(device).reg_write(reg, value))
        self.__logger.write(LogType.IIO_DEVICE, "Write: device {}; reg {}; value {}".format(device, reg, value))

    def set_device_attr(self, device: str, attr: str, value: str):
        attribute = self.__safe_exec(lambda: self.get_device_attrs(device).get(attr))

        try:
            attribute.value = value
        except:
            self.__logger.write(LogType.ERROR, traceback.format_exc())
        self.__logger.write(LogType.IIO_DEVICE, "Write: device {}; attribute {}; value {}".format(device, attr, value))

    def reg_read(self, device: str, i: int) -> int:
        return self.__safe_exec(lambda: self.__iio_ctx.find_device(device).reg_read(i))

    def get_all_attrs(self) -> {}:
        return self.__safe_exec(lambda: self.__iio_ctx.attrs)

    def get_desc(self) -> str:
        return self.__safe_exec(lambda: self.__iio_ctx.description)

    @staticmethod
    def make_ctx_string(text: str) -> str:
        if sys.platform.startswith("linux"):
            text = "/dev/" + text

        return text

    def get_device_freqs(self, device: str, attr: str) -> list:
        freqs = []
        for freq in self.get_device_attrs(device).get(attr).value.split(' '):
            if freq != '0':
                freqs.append(self.from_Hz_to_GHz(freq))

        return freqs

    def write_to_iio(self, device: str, attr: str, value: str):
        self.__logger.write(LogType.UI, "Set device {}, attr {}, to {}".format(device, attr, value))

        try:
            if self.__iio_ctx is None or value is None or self.__iio_ctx.find_device(device).attrs.get(attr) is None:
                raise OSError("Failed to write: device {}; attribute {}; value {}".format(device, attr, value))

            if self.__iio_ctx.find_device(device).attrs.get(attr).value != str(value):
                self.__iio_ctx.find_device(device).attrs.get(attr).value = str(value)
                self.__logger.write(LogType.IIO_DEVICE, "Write: device {}; attribute {}; value {}"
                                    .format(device, attr, value))

        except:
            self.__logger.write(LogType.ERROR, traceback.format_exc())
            if not self.valid_ctx()[0]:
                self.remove_ctx()

    def connect_to_ctx(self, ctx_config: str) -> bool:
        self.__iio_ctx = iio.Context(ctx_config)
        self.__ctx_config = ctx_config

        self.__logger.write(LogType.IIO_DEVICE, "Connect to context: {} ".format(self.__ctx_config) +
                                                "Successful" if self.__iio_ctx is not None else "Failed")

        return self.__iio_ctx is not None
