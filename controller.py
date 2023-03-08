import glob
import sys

import iio
import serial
from PySide6.QtSerialPort import QSerialPortInfo
from iio import Context


class Controller:
    __iio_ctx = None

    def __init__(self) -> None:
        self.__iio_ctx: Context()

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

    @staticmethod
    def __get_serial_ports() -> list[str]:
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
                pass
        return result

    @staticmethod
    def get_ports() -> list:
        return [port.portName() for port in QSerialPortInfo.availablePorts()]

    def valid_ctx(self) -> bool:
        return self.__iio_ctx is not None

    def remove_ctx(self):
        self.__iio_ctx = None

    def get_device_attrs(self, device: str) -> {}:
        return self.__iio_ctx.find_device(device).attrs

    def get_device_ch_attr(self, device: str, ch: str, attr: str) -> iio.ChannelAttr:
        return self.__iio_ctx.find_device(device).find_channel(ch).attrs.get(attr)

    def reg_write(self, device: str, reg: int, value: int):
        self.__iio_ctx.find_device(device).reg_write(reg, value)

    def reg_read(self, device: str, i: int) -> int:
        return self.__iio_ctx.find_device(device).reg_read(i)

    def get_all_attrs(self) -> {}:
        return self.__iio_ctx.attrs

    def get_desc(self) -> str:
        return self.__iio_ctx.description

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
        if self.__iio_ctx is None or value is None or self.__iio_ctx.find_device(device).attrs.get(attr) is None:
            print("fail", attr, self.__iio_ctx, value, self.__iio_ctx.find_device(device).attrs)
            return

        if self.__iio_ctx.find_device(device).attrs.get(attr).value != str(value):
            self.__iio_ctx.find_device(device).attrs.get(attr).value = str(value)
            print("write", attr)
        else:
            print("no change", attr)

    def connect_to_ctx(self, ctx_config: str):
        self.__iio_ctx = iio.Context(ctx_config)
