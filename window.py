# This Python file uses the following encoding: utf-8
from PyQt6 import QtWidgets, uic
from PySide6.QtSerialPort import QSerialPortInfo
from PyQt6.QtCore import QThread, pyqtSignal
import iio
import sys
import glob
import serial
import time

class Heartbeat(QThread):
    pulse = pyqtSignal()

    def __init__(self, id, seconds):
        super().__init__()
        self.seconds = seconds
        self.id = id

    def run(self):
        while True:
            # print("Thread " + self.id)
            self.pulse.emit()
            time.sleep(self.seconds)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.heartbeat_thread = Heartbeat("heartbeat", 2)
        self.heartbeat_thread.pulse.connect(self.update_ui)
        self.context_thread = Heartbeat("context", 5)
        self.context_thread.pulse.connect(self.update_contexts)
        self.ui = uic.loadUi("design.ui", self)

        # Add contexts combo box
        self.ui.cb_available_contexts.clear()
        self.ui.cb_available_contexts.addItems(["Select..."])
        self.context_thread.start()

        # Populate combobox values with human-readable/meaningful strings
        self.populate_ifvga(self.ui.cb_tx_ifvga)
        self.populate_ifvga(self.ui.cb_rx_ifvga)
        self.populate_rflna(self.ui.cb_rx_rflna)
        self.populate_rfvga(self.ui.cb_tx_rfvga)
        self.populate_bbcoarse(self.ui.cb_rx_bbcoarse1)
        self.populate_bbcoarse(self.ui.cb_rx_bbcoarse2)
        self.populate_bbfine(self.ui.cb_rx_bbfine)

        # Connect slot to update context labels
        self.ui.cb_available_contexts.currentIndexChanged.connect(self.ctx_changed)

        # Connect slots to enable/disable device configuration and monitoring
        self.ui.gb_transmitter.clicked.connect(self.tx_power_switch)
        self.ui.gb_receiver.clicked.connect(self.rx_power_switch)

        # Connect slots to enable/disable tuning options
        self.ui.chk_tx_autotuning.stateChanged.connect(self.tx_autotuning_switch)
        self.ui.chk_rx_autotuning.stateChanged.connect(self.rx_autotuning_switch)
        self.ui.chk_tx_auto_ifvga.stateChanged.connect(self.tx_auto_ifvga_switch)
        self.ui.chk_rx_auto_ifvga_rflna.stateChanged.connect(self.rx_auto_ifvga_rflna_switch)

        # Connect slots to refresh registers buttons
        self.ui.btn_tx_refresh_regs.clicked.connect(self.tx_read_regs)
        self.ui.btn_rx_refresh_regs.clicked.connect(self.rx_read_regs)

        # Connect slots to reset device button
        self.ui.btn_reset_device.clicked.connect(self.reset_device)

        # Connect slots to combo boxes and spin boxes
        self.ui.cb_tx_vco.currentIndexChanged.connect(self.tx_vco_changed)
        self.ui.cb_rx_vco.currentIndexChanged.connect(self.rx_vco_changed)
        self.ui.cb_tx_ifvga.currentIndexChanged.connect(self.tx_ifvga_changed)
        self.ui.cb_rx_ifvga.currentIndexChanged.connect(self.rx_ifvga_changed)
        self.ui.cb_rx_rflna.currentIndexChanged.connect(self.rx_rflna_changed)
        self.ui.cb_tx_rfvga.currentIndexChanged.connect(self.tx_rfvga_changed)
        self.ui.cb_rx_bbcoarse1.currentIndexChanged.connect(self.rx_bbcoarse1_changed)
        self.ui.cb_rx_bbcoarse2.currentIndexChanged.connect(self.rx_bbcoarse2_changed)
        self.ui.cb_rx_bbfine.currentIndexChanged.connect(self.rx_bbfine_changed)
        self.ui.sb_tx_target.valueChanged.connect(self.tx_target_changed)
        self.ui.sb_rx_target.valueChanged.connect(self.rx_target_changed)

        # Connect slots to register maps
        self.ui.tb_tx_registers.cellChanged.connect(self.update_cell_tx)
        self.ui.tb_rx_registers.cellChanged.connect(self.update_cell_rx)

        # Connect slots to load/save buttons
        self.ui.btn_tx_load_regs.clicked.connect(self.tx_load_regs)
        self.ui.btn_rx_load_regs.clicked.connect(self.rx_load_regs)
        self.ui.btn_tx_save_regs.clicked.connect(self.tx_save_regs)
        self.ui.btn_rx_save_regs.clicked.connect(self.rx_save_regs)

    def update_ui(self):
        # Firmware
        mwc_attrs = self.iio_ctx.find_device("mwc").attrs

        checked = False if mwc_attrs.get("tx_autotuning").value == "0" else True
        self.ui.chk_tx_autotuning.blockSignals(True)
        self.ui.chk_tx_autotuning.setChecked(checked)
        self.ui.chk_tx_autotuning.blockSignals(False)
        self.ui.cb_tx_rfvga.setEnabled(not checked)

        checked = False if mwc_attrs.get("rx_autotuning").value == "0" else True
        self.ui.chk_rx_autotuning.blockSignals(True)
        self.ui.chk_rx_autotuning.setChecked(checked)
        self.ui.chk_rx_autotuning.blockSignals(False)
        self.ui.cb_rx_bbcoarse1.setEnabled(not checked)
        self.ui.cb_rx_bbcoarse2.setEnabled(not checked)
        self.ui.cb_rx_bbfine.setEnabled(not checked)

        checked = False if mwc_attrs.get("tx_auto_ifvga").value == "0" else True
        self.ui.chk_tx_auto_ifvga.blockSignals(True)
        self.ui.chk_tx_auto_ifvga.setChecked(checked)
        self.ui.chk_tx_auto_ifvga.blockSignals(False)
        self.ui.cb_tx_ifvga.setEnabled(not checked)

        checked = False if mwc_attrs.get("rx_auto_ifvga_rflna").value == "0" else True
        self.ui.chk_rx_auto_ifvga_rflna.blockSignals(True)
        self.ui.chk_rx_auto_ifvga_rflna.setChecked(checked)
        self.ui.chk_rx_auto_ifvga_rflna.blockSignals(False)
        self.ui.cb_rx_ifvga.setEnabled(not checked)
        self.ui.cb_rx_rflna.setEnabled(not checked)

        tx_target = int(mwc_attrs.get("tx_target").value)
        self.ui.sb_tx_target.blockSignals(True)
        self.ui.sb_tx_target.setValue(tx_target)
        self.ui.sb_tx_target.blockSignals(False)
        rx_target = int(mwc_attrs.get("rx_target").value)
        self.ui.sb_rx_target.blockSignals(True)
        self.ui.sb_rx_target.setValue(rx_target)
        self.ui.sb_rx_target.blockSignals(False)
        raw = self.iio_ctx.find_device("mwc").find_channel("tx_det").attrs.get("raw").value
        scale = self.iio_ctx.find_device("mwc").find_channel("tx_det").attrs.get("scale").value
        tx_det_out = int(float(raw) * float(scale))
        self.ui.lbl_tx_det_dyn.setText(str(tx_det_out) + " mV")
        raw = self.iio_ctx.find_device("mwc").find_channel("rx_det").attrs.get("raw").value
        scale = self.iio_ctx.find_device("mwc").find_channel("rx_det").attrs.get("scale").value
        rx_det_out = int(float(raw) * float(scale))
        self.ui.lbl_rx_det_dyn.setText(str(rx_det_out) + " mV")
        tx_diff = tx_det_out - tx_target
        self.ui.lbl_tx_autotuning.setText("{0:+d} mV".format(tx_diff))
        if abs(tx_diff) > self.ui.sb_tx_tolerance.value():
            self.ui.lbl_tx_autotuning.setStyleSheet("font-weight: bold")
        else:
            self.ui.lbl_tx_autotuning.setStyleSheet("font-weight: normal")
        rx_diff = rx_det_out - rx_target
        self.ui.lbl_rx_autotuning.setText("{0:+d} mV".format(rx_diff))
        if abs(rx_diff) > self.ui.sb_rx_tolerance.value():
            self.ui.lbl_rx_autotuning.setStyleSheet("font-weight: bold")
        else:
            self.ui.lbl_rx_autotuning.setStyleSheet("font-weight: normal")

        # Tx
        tx_attrs = self.iio_ctx.find_device("hmc6300").attrs
        freq = tx_attrs.get("vco").value
        freq = str(float(int(freq) / 1000000))
        self.ui.cb_tx_vco.blockSignals(True)
        self.ui.cb_tx_vco.setCurrentText(freq)
        self.ui.cb_tx_vco.blockSignals(False)
        tx_enabled = tx_attrs.get("enabled").value
        txen = False if tx_enabled == "0" else True
        self.ui.gb_transmitter.setChecked(txen)
        ifvga = tx_attrs.get("if_attn").value
        self.cb_tx_ifvga.blockSignals(True)
        self.cb_tx_ifvga.setCurrentIndex(int(ifvga))
        self.cb_tx_ifvga.blockSignals(False)
        rfvga = tx_attrs.get("rf_attn").value
        self.cb_tx_rfvga.blockSignals(True)
        self.cb_tx_rfvga.setCurrentIndex(int(rfvga))
        self.cb_tx_rfvga.blockSignals(False)
        temp = self.iio_ctx.find_device("hmc6300").find_channel("temp").attrs.get("raw").value
        self.ui.lbl_tx_temp_dyn.setText(str(temp) + " " + self.temp_range(int(temp)))
        gain = 32 - float(ifvga) * 1.3 - float(rfvga) * 1.3
        self.ui.lbl_tx_gain_dyn.setText("{:.1f} dB".format(gain))

        # Rx
        rx_attrs = self.iio_ctx.find_device("hmc6301").attrs
        freq = rx_attrs.get("vco").value
        freq = str(float(int(freq) / 1000000))
        self.ui.cb_rx_vco.blockSignals(True)
        self.ui.cb_rx_vco.setCurrentText(freq)
        self.ui.cb_rx_vco.blockSignals(False)
        rx_enabled = rx_attrs.get("enabled").value
        rxen = False if rx_enabled == "0" else True
        self.ui.gb_receiver.blockSignals(True)
        self.ui.gb_receiver.setChecked(rxen)
        self.ui.gb_receiver.blockSignals(False)
        ifvga = rx_attrs.get("if_attn").value
        self.cb_rx_ifvga.blockSignals(True)
        self.cb_rx_ifvga.setCurrentIndex(int(ifvga))
        self.cb_rx_ifvga.blockSignals(False)
        rflna = rx_attrs.get("rf_lna_gain").value
        self.cb_rx_rflna.blockSignals(True)
        self.cb_rx_rflna.setCurrentIndex(int(rflna))
        self.cb_rx_rflna.blockSignals(False)
        temp = self.iio_ctx.find_device("hmc6301").find_channel("temp").attrs.get("raw").value
        self.ui.lbl_rx_temp_dyn.setText(str(temp) + " " + self.temp_range(int(temp)))
        bbcoarse1 = rx_attrs.get("bb_attn1").value
        self.ui.cb_rx_bbcoarse1.blockSignals(True)
        self.ui.cb_rx_bbcoarse1.setCurrentIndex(self.ui.cb_rx_bbcoarse1.findData(int(bbcoarse1)))
        self.ui.cb_rx_bbcoarse1.blockSignals(False)
        bbcoarse2 = rx_attrs.get("bb_attn2").value
        self.ui.cb_rx_bbcoarse2.blockSignals(True)
        self.ui.cb_rx_bbcoarse2.setCurrentIndex(self.ui.cb_rx_bbcoarse2.findData(int(bbcoarse2)))
        self.ui.cb_rx_bbcoarse2.blockSignals(False)
        bbfine = rx_attrs.get("bb_attni_fine").value
        self.ui.cb_rx_bbfine.blockSignals(True)
        self.ui.cb_rx_bbfine.setCurrentIndex(self.ui.cb_rx_bbfine.findData(int(bbfine)))
        self.ui.cb_rx_bbfine.blockSignals(False)
        gain = 69 - float(ifvga) * 1.3 - float(rflna) * 6 + \
                int(self.ui.cb_rx_bbcoarse1.currentText().split()[0]) + \
                int(self.ui.cb_rx_bbcoarse2.currentText().split()[0]) + \
                int(self.ui.cb_rx_bbfine.currentText().split()[0])
        self.ui.lbl_rx_gain_dyn.setText("{:.1f} dB".format(gain))

    def init_ui(self):
        # Tabs
        self.ui.transceiver_tab.setEnabled(False)
        self.ui.phy_tab.setEnabled(False)
        self.ui.serdes_tab.setEnabled(False)
        self.ui.lbl_hw_model_dyn.setText("-")
        self.ui.lbl_hw_version_dyn.setText("-")
        self.ui.lbl_hw_serial_dyn.setText("-")
        self.ui.lbl_carrier_model_dyn.setText("-")
        self.ui.lbl_carrier_version_dyn.setText("-")
        self.ui.lbl_carrier_serial_dyn.setText("-")
        self.ui.lbl_firmware_dyn.setText("-")

    def update_contexts(self):
        cb = self.ui.cb_available_contexts
        available_ports = QSerialPortInfo.availablePorts()
        ports = [port.portName() for port in available_ports]
        options_in_cb = [cb.itemText(i) for i in range(1, cb.count())]
        for port in ports:
            index = cb.findText(port)
            if index <= 0:
                cb.addItems([port])

        # Check if the selected device is still connected
        if (cb.currentIndex() > 0):
            try:
                ctx = iio.Context("serial:" + cb.currentText() + ",115200,8n2n")
                # Do something here: window.iio_ctx = ctx
            except Exception as e:
                if str(e).__contains__("[Errno 2]"):
                    print(e)
                    cb.currentIndexChanged.emit(cb.currentIndex())
                else:
                    pass

        for port in options_in_cb:
            if port not in ports:
                cb.removeItem(cb.findText(port))

    def populate_vco_frequencies(self, cb, freqs = []):
        cb.blockSignals(True)
        cb.clear()
        frequencies = []
        for freq in freqs:
            if freq != '0' and freq != '':
                text = str(int(freq) / 1000000)
                frequencies.append(text)
        cb.addItems(frequencies)
        cb.blockSignals(False)

    ifvga = {
        "0 dB": 0,
        "-1.3 dB": 1,
        "-2.6 dB": 2,
        "-3.9 dB": 3,
        "-5.2 dB": 4,
        "-6.5 dB": 5,
        "-7.8 dB": 6,
        "-9.1 dB": 7,
        "-10.4 dB": 8,
        "-11.7 dB": 9,
        "-13 dB": 10,
        "-14.3 dB": 11,
        "-15.6 dB": 12,
        "-16.9 dB": 13,
    }

    def populate_ifvga(self, cb):
        cb.clear()
        for key, value in self.ifvga.items():
            cb.addItem(key, value)

    rflna = {
        "0 dB": 0,
        "-6 dB": 1,
        "-12 dB": 2,
        "-18 dB": 3,
    }

    def populate_rflna(self, cb):
        cb.clear()
        for key, value in self.rflna.items():
            cb.addItem(key, value)

    rfvga = {
        "0 dB": 0,
        "-1.3 dB": 1,
        "-2.6 dB": 2,
        "-3.9 dB": 3,
        "-5.2 dB": 4,
        "-6.5 dB": 5,
        "-7.8 dB": 6,
        "-9.1 dB": 7,
        "-10.4 dB": 8,
        "-11.7 dB": 9,
        "-13 dB": 10,
        "-14.3 dB": 11,
        "-15.6 dB": 12,
        "-16.9 dB": 13,
        "-18.2 dB": 14,
        "-19.5 dB": 15,
    }
    def populate_rfvga(self, cb):
        cb.clear()
        for key, value in self.rfvga.items():
            cb.addItem(key, value)

    bbcoarse = {
        "0 dB": 0,
        "-6 dB": 2,
        "-12 dB": 1,
        "-18 dB": 3,
    }
    def populate_bbcoarse(self, cb):
        cb.clear()
        for key, value in self.bbcoarse.items():
            cb.addItem(key, value)

    bbfine = {
        "0 dB": 0,
        "-1 dB": 4,
        "-2 dB": 2,
        "-3 dB": 6,
        "-4 dB": 1,
        "-5 dB": 5,
    }

    def populate_bbfine(self, cb):
        cb.clear()
        for key, value in self.bbfine.items():
            cb.addItem(key, value)

    def get_serial_ports(self):
        platform = sys.platform
        if platform.startswith("win"):
            ports = ['COM%s' % (i+1) for i in range (256)]
        elif platform.startswith("linux"):
            ports = glob.glob("/dev/tty[A-Za-z]*")
        else:
            raise EnvironmentError("Unsuported platform")
        
        result = []
        for port in ports:
            try: 
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result

    def update_cell_tx(self, row, column):
        # Get reg address and value to write
        reg = int(self.ui.tb_tx_registers.item(row, 0).text().split("x")[1], 16)
        value = self.ui.tb_tx_registers.item(row, 1).text()

        value = int(value.split("x")[1], 16) if value.__contains__("0x") else int(value, 16)
        value &= 0xff
        self.iio_ctx.find_device("hmc6300").reg_write(reg, value)

        self.ui.tb_tx_registers.blockSignals(True)
        self.ui.tb_tx_registers.setItem(row, column, QtWidgets.QTableWidgetItem(hex(value)))
        self.ui.tb_tx_registers.blockSignals(False)

    def update_cell_rx(self, row, column):
        reg = int(self.ui.tb_rx_registers.item(row, 0).text().split("x")[1], 16)
        value = self.ui.tb_rx_registers.item(row, 1).text()

        value = int(value.split("x")[1], 16) if value.__contains__("0x") else int(value, 16)
        value &= 0xff
        self.iio_ctx.find_device("hmc6301").reg_write(reg, value)

        self.ui.tb_rx_registers.blockSignals(True)
        self.ui.tb_rx_registers.setItem(row, column, QtWidgets.QTableWidgetItem(hex(value)))
        self.ui.tb_rx_registers.blockSignals(False)

    def ctx_changed(self):
        text = self.ui.cb_available_contexts.currentText()
        index = self.ui.cb_available_contexts.findText(text)
        
        if text == "Select context...":
            return
        
        if sys.platform.startswith("linux"):
            text = "/dev/" + text

        # Disable "Select context..." option
        self.ui.cb_available_contexts.model().item(0).setEnabled(False)

        try:
            self.iio_ctx = iio.Context("serial:" + text + ",115200,8n2n")

            # Context attributes
            ctx_attrs = self.iio_ctx.attrs
            self.ui.lbl_hw_model_dyn.setText(ctx_attrs.get("hw_model"))
            self.ui.lbl_hw_version_dyn.setText(ctx_attrs.get("hw_version"))
            self.ui.lbl_hw_serial_dyn.setText(ctx_attrs.get("hw_serial"))
            self.ui.lbl_carrier_model_dyn.setText(ctx_attrs.get("carrier_model"))
            self.ui.lbl_carrier_version_dyn.setText(ctx_attrs.get("carrier_version"))
            self.ui.lbl_carrier_serial_dyn.setText(ctx_attrs.get("carrier_serial"))
            self.ui.lbl_firmware_dyn.setText(self.iio_ctx.description)

            self.ui.transceiver_tab.setEnabled(True)
            self.ui.phy_tab.setEnabled(True)
            self.ui.serdes_tab.setEnabled(True)
            freqs = self.iio_ctx.find_device("hmc6300").attrs.get("vco_available").value.split(' ')
            self.populate_vco_frequencies(self.ui.cb_tx_vco, freqs)
            vco = self.iio_ctx.find_device("hmc6300").attrs.get("vco").value
            self.ui.cb_tx_vco.setCurrentText(vco)
            self.ui.cb_tx_vco.blockSignals(False)
            freqs = self.iio_ctx.find_device("hmc6301").attrs.get("vco_available").value.split(' ')
            self.populate_vco_frequencies(self.ui.cb_rx_vco, freqs)
            vco = self.iio_ctx.find_device("hmc6301").attrs.get("vco").value
            self.ui.cb_rx_vco.blockSignals(True)
            self.ui.cb_rx_vco.setCurrentText(vco)
            self.ui.cb_rx_vco.blockSignals(False)
            self.tx_read_regs()
            self.rx_read_regs()
            self.heartbeat_thread.start()
        except Exception as e:
            if str(e).__contains__("[Errno 5]"):
                # Context already created
                pass
            elif str(e).__contains__("[Errno 2]"):
                # Device not connected
                # Used when disconnecting a device
                self.iio_ctx = None
                self.ui.cb_available_contexts.removeItem(index)
                self.ui.cb_available_contexts.setCurrentIndex(0)
                self.init_ui()
            elif str(e).__contains__("[Errno 1460]") or str(e).__contains__("Errno 110"):
                # Not an IIO device
                self.iio_ctx = None
                self.init_ui()
            elif str(e).__contains__("[Errno 16]"):
                self.iio_ctx = None
                QtWidgets.QMessageBox.critical(
                    self,
                    "Device busy",
                    "Cannot create context on port " + text + ". The device might already be in use.",
                    buttons = QtWidgets.QMessageBox.Ok,
                    defaultButton = QtWidgets.QMessageBox.Ok
                )
            return

    def temp_range(self, temp):
        r1 = range(0, 2)
        r2 = range(3, 6)
        r3 = range(7, 15)
        if temp in r1:
            return "(below -20 °C)"
        elif temp in r2:
            return "(-20...+10 °C)"
        elif temp in r3:
            return "(+10...+45 °C)"
        else:
            return "(above +45 °C)"

    def tx_power_switch(self, value):
        self.iio_ctx.find_device("hmc6300").attrs.get("enabled").value = "1" if value == True else "0"

    def rx_power_switch(self, value):
        self.iio_ctx.find_device("hmc6301").attrs.get("enabled").value = "1" if value == True else "0"

    def tx_autotuning_switch(self):
        if self.ui.chk_tx_autotuning.isChecked():
            val = "1"
        else:
            val = "0"
        self.iio_ctx.find_device("mwc").attrs.get("tx_autotuning").value = val
        self.ui.cb_tx_rfvga.setEnabled(not int(val))

    def rx_autotuning_switch(self):
        if self.ui.chk_rx_autotuning.isChecked():
            val = "1"
        else:
            val = "0"
        self.iio_ctx.find_device("mwc").attrs.get("rx_autotuning").value = val
        self.ui.cb_rx_bbcoarse1.setEnabled(not int(val))
        self.ui.cb_rx_bbcoarse2.setEnabled(not int(val))
        self.ui.cb_rx_bbfine.setEnabled(not int(val))

    def tx_auto_ifvga_switch(self, state):
        if self.ui.chk_tx_auto_ifvga.isChecked():
            val = "1"
        else:
            val = "0"
        self.iio_ctx.find_device("mwc").attrs.get("tx_auto_ifvga").value = val
        self.ui.cb_tx_ifvga.setEnabled(not int(val))

    def rx_auto_ifvga_rflna_switch(self, state):
        if self.ui.chk_rx_auto_ifvga_rflna.isChecked():
            val = "1"
        else:
            val = "0"
        self.iio_ctx.find_device("mwc").attrs.get("rx_auto_ifvga_rflna").value = val
        self.ui.cb_rx_ifvga.setEnabled(not int(val))
        self.ui.cb_rx_rflna.setEnabled(not int(val))

    def tx_read_regs(self):
        self.ui.tb_tx_registers.blockSignals(True)
        row = 0
        for i in range(28):
            if i == 0 or (i > 12 and i < 16):
                continue
            reg_value = hex(self.iio_ctx.find_device("hmc6300").reg_read(i))
            self.ui.tb_tx_registers.setItem(row, 1, QtWidgets.QTableWidgetItem(str(reg_value)))
            row = row + 1
        self.ui.tb_tx_registers.blockSignals(False)

    def rx_read_regs(self):
        self.ui.tb_rx_registers.blockSignals(True)
        row = 0
        for i in range(28):
            if i > 9 and i < 16:
                continue
            reg_value = hex(self.iio_ctx.find_device("hmc6301").reg_read(i))
            self.ui.tb_rx_registers.setItem(row, 1, QtWidgets.QTableWidgetItem(str(reg_value)))
            row = row + 1
        self.ui.tb_rx_registers.blockSignals(False)

    def reset_device(self):
        q = QtWidgets.QMessageBox()
        q.setText("Do you want to reset the device?")
        q.setWindowTitle("Reset device")
        q.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes |
                             QtWidgets.QMessageBox.StandardButton.No)

        reply = q.exec()
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.iio_ctx.find_device("mwc").attrs.get("reset").value = '1'
        else:
            return

        self.tx_read_regs()
        self.rx_read_regs()

    def tx_vco_changed(self):
        text = self.ui.cb_tx_vco.currentText()
        freq = str(int(float(text) * 1000000))
        self.iio_ctx.find_device("hmc6300").attrs.get("vco").value = freq

    def rx_vco_changed(self):
        text = self.ui.cb_rx_vco.currentText()
        freq = str(int(float(text) * 1000000))
        self.iio_ctx.find_device("hmc6301").attrs.get("vco").value = freq

    def tx_ifvga_changed(self, index):
        attn = self.ui.cb_tx_ifvga.itemData(index)
        self.iio_ctx.find_device("hmc6300").attrs.get("if_attn").value = str(attn)

    def rx_ifvga_changed(self, index):
        attn = self.ui.cb_rx_ifvga.itemData(index)
        self.iio_ctx.find_device("hmc6301").attrs.get("if_attn").value = str(attn)

    def rx_rflna_changed(self, index):
        rflna = self.ui.cb_rx_rflna.itemData(index)
        self.iio_ctx.find_device("hmc6301").attrs.get("rf_lna_gain").value = str(rflna)

    def tx_rfvga_changed(self, index):
        rfvga = self.ui.cb_tx_rfvga.itemData(index)
        self.iio_ctx.find_device("hmc6300").attrs.get("rf_attn").value = str(rfvga)

    def rx_bbcoarse1_changed(self, index):
        bbcoarse1 = self.ui.cb_rx_bbcoarse1.itemData(index)
        self.iio_ctx.find_device("hmc6301").attrs.get("bb_attn1").value = str(bbcoarse1)

    def rx_bbcoarse2_changed(self, index):
        bbcoarse2 = self.ui.cb_rx_bbcoarse2.itemData(index)
        self.iio_ctx.find_device("hmc6301").attrs.get("bb_attn2").value = str(bbcoarse2)

    def rx_bbfine_changed(self, index):
        bbfine = self.ui.cb_rx_bbfine.itemData(index)
        self.iio_ctx.find_device("hmc6301").attrs.get("bb_attni_fine").value = str(bbfine)

    def tx_target_changed(self, index):
        target = self.ui.sb_tx_target.value()
        self.iio_ctx.find_device("mwc").attrs.get("tx_target").value = str(target)

    def rx_target_changed(self, index):
        target = self.ui.sb_rx_target.value()
        self.iio_ctx.find_device("mwc").attrs.get("rx_target").value = str(target)

    def tx_load_regs(self):
        fileName, type = QtWidgets.QFileDialog.getOpenFileName(self, "Open TX registers file", "Text files (*.txt)")
        if fileName == "":
            return
        with open(fileName, 'r') as infile:
            infile.readline()
            for i in range(28):
                if i == 0 or (i > 12 and i < 16):
                    continue
                line = infile.readline()
                reg = int(line.split(',')[0].strip('"'))
                value = int(str(line.split(',')[1]).strip('"\n'))

                self.iio_ctx.find_device("hmc6300").reg_write(reg, value)
        self.tx_read_regs()

    def rx_load_regs(self):
        fileName, type = QtWidgets.QFileDialog.getOpenFileName(self, "Open RX registers file", "Text files (*.txt)")
        if fileName == "":
            return
        with open(fileName, 'r') as infile:
            infile.readline()
            for i in range(28):
                if i > 9 and i < 16:
                    continue
                line = infile.readline()
                reg = int(line.split(',')[0].strip('"'))
                value = int(str(line.split(',')[1]).strip('"\n'))

                self.iio_ctx.find_device("hmc6301").reg_write(reg, value)
        self.rx_read_regs()

    def tx_save_regs(self):
        fileName, type = QtWidgets.QFileDialog.getSaveFileName(self, "Save TX registers content", "tx_regs_content.txt", "Text files (*.txt)")
        if fileName == "":
            return
        with open(fileName, 'w') as outfile:
            outfile.write("\"Address\",\"Data\"\n")
            for i in range(28):
                if i == 0 or (i > 12 and i < 16):
                    continue
                reg_value = self.iio_ctx.find_device("hmc6300").reg_read(i)
                outfile.write("\"" + str(i) + "\",")
                outfile.write("\"" + str(int(reg_value)) + "\"\n")

    def rx_save_regs(self):
        fileName, type = QtWidgets.QFileDialog.getSaveFileName(self, "Save RX registers content", "rx_regs_content.txt", "Text files (*.txt)")
        if fileName == "":
            return
        with open(fileName, 'w') as outfile:
            outfile.write("\"Address\",\"Data\"\n")
            for i in range(28):
                if i > 9 and i < 16:
                    continue
                reg_value = self.iio_ctx.find_device("hmc6301").reg_read(i)
                outfile.write("\"" + str(i) + "\",")
                outfile.write("\"" + str(int(reg_value, base = 16)) + "\"\n")
