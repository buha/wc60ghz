import glob
import sys

import iio
import serial
from PySide6.QtSerialPort import QSerialPortInfo
from iio import Context

from resouces import TEST_DEVICE, TEST_ATTR


class Controller:
    __iio_ctx = None

    def __init__(self) -> None:
        self.__iio_ctx: Context()
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

    def valid_ctx(self) -> (bool, str):
        if self.__iio_ctx is None:
            return False, ""

        try:
            self.__iio_ctx.find_device(TEST_DEVICE).attrs.get(TEST_ATTR).value
        except Exception as e:
            return False, str(e)

        return True, ""

    def remove_ctx(self):
        print(" ----  try to DELETE CTX")
        if self.__iio_ctx is not None:
            print(" ----  DELETED CTX")
            del self.__iio_ctx
            self.__iio_ctx = None
            self.__ctx_config = ""

    def get_device_attrs(self, device: str) -> {}:
        try:
            return self.__iio_ctx.find_device(device).attrs
        except:
            if not self.valid_ctx()[0]:
                self.remove_ctx()

    def get_device_ch_attr(self, device: str, ch: str, attr: str) -> iio.ChannelAttr:
        try:
            return self.__iio_ctx.find_device(device).find_channel(ch).attrs.get(attr)
        except:
            if not self.valid_ctx()[0]:
                self.remove_ctx()

    def reg_write(self, device: str, reg: int, value: int):
        try:
            self.__iio_ctx.find_device(device).reg_write(reg, value)
        except:
            if not self.valid_ctx()[0]:
                self.remove_ctx()

    def set_device_attr(self, device: str, reg: str, value: str):
        try:
            self.get_device_attrs(device).get(reg).value = value
        except:
            if not self.valid_ctx()[0]:
                self.remove_ctx()

    def reg_read(self, device: str, i: int) -> int:
        try:
            return self.__iio_ctx.find_device(device).reg_read(i)
        except:
            if not self.valid_ctx()[0]:
                self.remove_ctx()

    def get_all_attrs(self) -> {}:
        try:
            return self.__iio_ctx.attrs
        except:
            if not self.valid_ctx()[0]:
                self.remove_ctx()

    def get_desc(self) -> str:
        try:
            return self.__iio_ctx.description
        except:
            if not self.valid_ctx()[0]:
                self.remove_ctx()

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
        try:
            if self.__iio_ctx is None or value is None or self.__iio_ctx.find_device(device).attrs.get(attr) is None:
                print("fail", attr, self.__iio_ctx, value, self.__iio_ctx.find_device(device).attrs)
                return

            if self.__iio_ctx.find_device(device).attrs.get(attr).value != str(value):
                self.__iio_ctx.find_device(device).attrs.get(attr).value = str(value)
                print("write", attr)
            else:
                print("no change", attr)
        except:
            if not self.valid_ctx()[0]:
                self.remove_ctx()

    def connect_to_ctx(self, ctx_config: str) -> bool:
        self.__iio_ctx = iio.Context(ctx_config)
        self.__ctx_config = ctx_config

        return self.__iio_ctx is not None
