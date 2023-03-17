# This Python file uses the following encoding: utf-8
import traceback

from PyQt6 import QtWidgets, uic

from controller import Controller
from heartbeat import Heartbeat
from logger import *
from resouces import *


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, controller: Controller, logger: Logger, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.controller = controller
        self.__logger = logger

        # Load Qt ui
        self.ui = uic.loadUi("design.ui", self)

        # init threads
        self.__ui_thread = Heartbeat("ui", 2)
        self.__context_thread = Heartbeat("context", 5)
        self.__ping_thread = Heartbeat("ping", 2)

        self.populate_objects()
        self.connect_slots()

        self.__ui_thread.start()
        self.__context_thread.start()
        self.__ping_thread.start()

    @staticmethod
    def populate_cb(cb: QtWidgets.QComboBox, items: dict | list):
        cb.blockSignals(True)
        cb.clear()

        for item in items:
            if item is None:
                items.remove(item)

        if isinstance(items, dict):
            for key, value in items.items():
                cb.addItem(key, value)
        elif isinstance(items, list):
            cb.addItems(items)
        else:
            print("wrong type !!!")

        cb.blockSignals(False)

    def populate_objects(self):
        # Add contexts combo box
        self.ui.cb_available_contexts.clear()
        self.ui.cb_available_contexts.addItems([NO_DEVICE_OPTION])

        # Populate combobox values with human-readable/meaningful strings
        self.populate_cb(self.ui.cb_tx_ifvga, IFVGA)
        self.populate_cb(self.ui.cb_rx_ifvga, IFVGA)
        self.populate_cb(self.ui.cb_rx_rflna, RFLNA)
        self.populate_cb(self.ui.cb_tx_rfvga, RFVGA)
        self.populate_cb(self.ui.cb_rx_bbcoarse1, BBCOARSE)
        self.populate_cb(self.ui.cb_rx_bbcoarse2, BBCOARSE)
        self.populate_cb(self.ui.cb_rx_bbfine, BBFINE)

    def connect_slots(self):
        # Connect threads
        self.__ui_thread.pulse.connect(self.update_ui)
        self.__context_thread.pulse.connect(self.update_contexts)
        self.__ping_thread.pulse.connect(self.ping)

        # Connect slot to update context labels
        self.ui.cb_available_contexts.currentIndexChanged.connect(self.ctx_changed)

        # Connect slots to enable/disable device configuration and monitoring
        self.ui.gb_transmitter.clicked.connect(
            lambda checked: self.device_power_switch(TX_DEVICE, checked))
        self.ui.gb_receiver.clicked.connect(
            lambda checked: self.device_power_switch(RX_DEVICE, checked))

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
        self.ui.cb_tx_vco.currentIndexChanged.connect(
            lambda _: self.controller.write_to_iio(TX_DEVICE, "vco", self.controller.from_GHz_to_Hz(
                self.ui.cb_tx_vco.currentText())))
        self.ui.cb_rx_vco.currentIndexChanged.connect(
            lambda _: self.controller.write_to_iio(RX_DEVICE, "vco",
                                                   self.controller.from_GHz_to_Hz(self.ui.cb_rx_vco.currentText())))
        self.ui.cb_tx_ifvga.currentIndexChanged.connect(
            lambda index: self.controller.write_to_iio(TX_DEVICE, "if_attn", self.ui.cb_tx_ifvga.itemData(index)))
        self.ui.cb_rx_ifvga.currentIndexChanged.connect(
            lambda index: self.controller.write_to_iio(RX_DEVICE, "if_attn", self.ui.cb_rx_ifvga.itemData(index)))
        self.ui.cb_rx_rflna.currentIndexChanged.connect(
            lambda index: self.controller.write_to_iio(RX_DEVICE, "rf_lna_gain", self.ui.cb_rx_rflna.itemData(index)))
        self.ui.cb_tx_rfvga.currentIndexChanged.connect(
            lambda index: self.controller.write_to_iio(TX_DEVICE, "rf_attn", self.ui.cb_tx_rfvga.itemData(index)))
        self.ui.cb_rx_bbcoarse1.currentIndexChanged.connect(
            lambda index: self.controller.write_to_iio(RX_DEVICE, "bb_attn1", self.ui.cb_rx_bbcoarse1.itemData(index)))
        self.ui.cb_rx_bbcoarse2.currentIndexChanged.connect(
            lambda index: self.controller.write_to_iio(RX_DEVICE, "bb_attn2", self.ui.cb_rx_bbcoarse2.itemData(index)))
        self.ui.cb_rx_bbfine.currentIndexChanged.connect(
            lambda index: self.controller.write_to_iio(RX_DEVICE, "bb_attni_fine",
                                                       self.ui.cb_rx_bbfine.itemData(index)))
        self.ui.sb_tx_target.valueChanged.connect(
            lambda _: self.controller.write_to_iio(MWC, "tx_target", self.ui.sb_tx_target.value()))
        self.ui.sb_rx_target.valueChanged.connect(
            lambda _: self.controller.write_to_iio(MWC, "rx_target", self.ui.sb_rx_target.value()))

        # Connect slots to register maps
        self.ui.tb_tx_registers.cellChanged.connect(
            lambda row, col: self.update_register_cell(self.ui.tb_tx_registers, TX_DEVICE, row, col))

        self.ui.tb_rx_registers.cellChanged.connect(
            lambda row, col: self.update_register_cell(self.ui.tb_rx_registers, RX_DEVICE, row, col))

        # Connect slots to load/save buttons
        self.ui.btn_tx_load_regs.clicked.connect(lambda: self.load_regs(TX_DEVICE))
        self.ui.btn_rx_load_regs.clicked.connect(lambda: self.load_regs(RX_DEVICE))
        self.ui.btn_tx_save_regs.clicked.connect(lambda: self.save_regs(self.ui.tb_tx_registers, "tx_regs_content.txt"))
        self.ui.btn_rx_save_regs.clicked.connect(lambda: self.save_regs(self.ui.tb_rx_registers, "rx_regs_content.txt"))

        # Connect tolerances
        self.ui.sb_tx_tolerance.valueChanged.connect(
            lambda value: self.__logger.write(LogType.UI, "Set TX tolerance to {}".format(value)))
        self.ui.sb_rx_tolerance.valueChanged.connect(
            lambda value: self.__logger.write(LogType.UI, "Set RX tolerance to {}".format(value)))

    def ping(self):
        exception = self.controller.valid_ctx()[1]
        if len(exception) != 0:
            self.__logger.write(LogType.IIO_DEVICE, "Failed to access device {} \n {}"
                                .format(self.controller.get_uri(), traceback.format_exc()))
            QtWidgets.QMessageBox.critical(self, "Failed to access device", exception)
            self.forget_ctx()

    def set_vco_ui(self, cb: QtWidgets.QComboBox, value: str):
        null_value = "0"

        if value == null_value:
            cb.blockSignals(True)
            if cb.findText(null_value) == -1:
                cb.addItem(null_value)
            cb.setCurrentText(null_value)
            cb.blockSignals(False)
        else:
            null_value_index = cb.findText(null_value)
            if null_value_index != -1:
                cb.removeItem(null_value_index)

            cb.setCurrentText(self.controller.from_Hz_to_GHz(value))

    def update_ui(self):
        # Firmware
        valid, exception = self.controller.valid_ctx()
        if not valid:
            if len(exception) != 0:
                self.__logger.write(LogType.IIO_DEVICE, "Failed to access device {}".format(self.controller.get_uri()))
            return

        try:
            mwc_attrs = self.controller.get_device_attrs(MWC)

            # tx_autotuning
            checked = mwc_attrs.get("tx_autotuning").value != "0"
            self.ui.chk_tx_autotuning.setChecked(checked)
            enabled = not checked and self.ui.gb_transmitter.isChecked()
            self.ui.cb_tx_rfvga.setEnabled(enabled)

            # rx_autotuning
            checked = mwc_attrs.get("rx_autotuning").value != "0"
            self.ui.chk_rx_autotuning.setChecked(checked)
            enabled = not checked and self.ui.gb_receiver.isChecked()
            self.ui.cb_rx_bbcoarse1.setEnabled(enabled)
            self.ui.cb_rx_bbcoarse2.setEnabled(enabled)
            self.ui.cb_rx_bbfine.setEnabled(enabled)

            # tx_auto_ifvga
            checked = mwc_attrs.get("tx_auto_ifvga").value != "0"
            self.ui.chk_tx_auto_ifvga.setChecked(checked)
            enabled = not checked and self.ui.gb_transmitter.isChecked()
            self.ui.cb_tx_ifvga.setEnabled(enabled)

            # rx_auto_ifvga_rflna
            checked = mwc_attrs.get("rx_auto_ifvga_rflna").value != "0"
            self.ui.chk_rx_auto_ifvga_rflna.setChecked(checked)
            enabled = not checked and self.ui.gb_receiver.isChecked()
            self.ui.cb_rx_ifvga.setEnabled(enabled)
            self.ui.cb_rx_rflna.setEnabled(enabled)

            # set sb_tx_target
            tx_target = int(mwc_attrs.get("tx_target").value)
            self.ui.sb_tx_target.setValue(tx_target)

            # set sb_rx_target
            rx_target = int(mwc_attrs.get("rx_target").value)
            self.ui.sb_rx_target.setValue(rx_target)

            # set lbl_tx_det_dyn
            raw = self.controller.get_device_ch_attr(MWC, "tx_det", "raw").value
            scale = self.controller.get_device_ch_attr(MWC, "tx_det", "scale").value
            tx_det_out = int(float(raw) * float(scale))
            self.ui.lbl_tx_det_dyn.setText(str(tx_det_out) + " mV")

            # set lbl_rx_det_dyn
            raw = self.controller.get_device_ch_attr(MWC, "rx_det", "raw").value
            scale = self.controller.get_device_ch_attr(MWC, "rx_det", "scale").value
            rx_det_out = int(float(raw) * float(scale))
            self.ui.lbl_rx_det_dyn.setText(str(rx_det_out) + " mV")

            # set lbl_tx_autotuning
            tx_diff = tx_det_out - tx_target
            self.ui.lbl_tx_autotuning.setText("{0:+d} mV".format(tx_diff))
            self.ui.lbl_tx_autotuning.setStyleSheet(
                "font-weight: bold" if abs(tx_diff) > self.ui.sb_tx_tolerance.value() else "font-weight: normal")

            # set lbl_rx_autotuning
            rx_diff = rx_det_out - rx_target
            self.ui.lbl_rx_autotuning.setText("{0:+d} mV".format(rx_diff))
            self.ui.lbl_rx_autotuning.setStyleSheet(
                "font-weight: bold" if abs(rx_diff) > self.ui.sb_rx_tolerance.value() else "font-weight: normal")

            # Tx
            tx_attrs = self.controller.get_device_attrs(TX_DEVICE)
            self.set_vco_ui(self.ui.cb_tx_vco, str(int(tx_attrs.get("vco").value)))
            self.ui.gb_transmitter.setChecked(tx_attrs.get("enabled").value != "0")

            ifvga_val = tx_attrs.get("if_attn").value
            rfvga_val = tx_attrs.get("rf_attn").value
            self.ui.cb_tx_ifvga.setCurrentIndex(int(ifvga_val))
            self.ui.cb_tx_rfvga.setCurrentIndex(int(rfvga_val))

            gain = 32 - float(ifvga_val) * 1.3 - float(rfvga_val) * 1.3
            self.ui.lbl_tx_gain_dyn.setText("{:.1f} dB".format(gain))

            temp = self.controller.get_device_ch_attr(TX_DEVICE, "temp", "raw").value
            self.ui.lbl_tx_temp_dyn.setText(str(temp) + " " + self.controller.temp_range(int(temp)))

            # Rx
            rx_attrs = self.controller.get_device_attrs(RX_DEVICE)
            self.set_vco_ui(self.ui.cb_rx_vco, str(int(rx_attrs.get("vco").value)))

            self.ui.gb_receiver.setChecked(rx_attrs.get("enabled").value != "0")
            self.ui.cb_rx_ifvga.setCurrentIndex(int(rx_attrs.get("if_attn").value))
            self.ui.cb_rx_rflna.setCurrentIndex(int(rx_attrs.get("rf_lna_gain").value))

            temp = self.controller.get_device_ch_attr(RX_DEVICE, "temp", "raw").value
            self.ui.lbl_rx_temp_dyn.setText(str(temp) + " " + self.controller.temp_range(int(temp)))

            self.ui.cb_rx_bbcoarse1.setCurrentIndex(
                self.ui.cb_rx_bbcoarse1.findData(int(rx_attrs.get("bb_attn1").value)))
            self.ui.cb_rx_bbcoarse2.setCurrentIndex(
                self.ui.cb_rx_bbcoarse2.findData(int(rx_attrs.get("bb_attn2").value)))
            self.ui.cb_rx_bbfine.setCurrentIndex(
                self.ui.cb_rx_bbfine.findData(int(rx_attrs.get("bb_attni_fine").value)))

            gain = 69 - float(ifvga_val) * 1.3 - float(rx_attrs.get("rf_lna_gain").value) * 6 + int(
                self.ui.cb_rx_bbcoarse1.currentText().split()[0]) + int(
                self.ui.cb_rx_bbcoarse2.currentText().split()[0]) + int(
                self.ui.cb_rx_bbfine.currentText().split()[0])
            self.ui.lbl_rx_gain_dyn.setText("{:.1f} dB".format(gain))
        except:
            self.__logger.write(LogType.ERROR, "Update UI failed \n {}".format(traceback.format_exc()))

    def init_ctx_ui(self):
        # Tabs
        self.ui.transceiver_tab.setEnabled(False)
        self.ui.phy_tab.setEnabled(False)
        self.ui.serdes_tab.setEnabled(False)
        self.ui.tabWidget.setTabText(1, "Transceiver")
        self.ui.lbl_hw_model_dyn.setText(EMPTY_VALUE)
        self.ui.lbl_hw_version_dyn.setText(EMPTY_VALUE)
        self.ui.lbl_hw_serial_dyn.setText(EMPTY_VALUE)
        self.ui.lbl_carrier_model_dyn.setText(EMPTY_VALUE)
        self.ui.lbl_carrier_version_dyn.setText(EMPTY_VALUE)
        self.ui.lbl_carrier_serial_dyn.setText(EMPTY_VALUE)
        self.ui.lbl_firmware_dyn.setText(EMPTY_VALUE)

    def update_contexts(self):
        cb = self.ui.cb_available_contexts
        ports = self.controller.get_ports()
        options_in_cb = [cb.itemText(i) for i in range(1, cb.count())]
        removed_item = False

        for port in ports:
            index = cb.findText(port)
            if index <= 0:
                cb.addItems([port])

        for option in options_in_cb:
            if option not in ports:
                removed_item = True

                cb.blockSignals(True)
                cb.removeItem(cb.findText(option))
                cb.blockSignals(False)

        if removed_item:
            self.ui.cb_available_contexts.setCurrentText(NO_DEVICE_OPTION)

    def update_register_cell(self, register: QtWidgets.QTableWidget, device: str, row: int, col: int):
        reg = int(register.item(row, 0).text().split("x")[1], 16)
        value = register.item(row, 1).text()
        self.__logger.write(LogType.UI, "Set device {}, reg {}, to {}".format(device, reg, value))

        value = int(value.split("x")[1], 16) if value.__contains__("0x") else int(value, 16)
        value &= 0xff
        self.controller.reg_write(device, reg, value)

        register.blockSignals(True)
        register.setItem(row, col, QtWidgets.QTableWidgetItem(hex(value)))
        register.blockSignals(False)

    def ctx_changed(self):
        text = self.ui.cb_available_contexts.currentText()
        self.__logger.write(LogType.UI, "Set context to {}".format(text))

        if text == NO_DEVICE_OPTION:
            self.controller.remove_ctx()
            self.init_ctx_ui()
            return

        text = self.controller.make_ctx_string(text)
        uri = CONNECTION_TYPE + ":" + text + SERIAL_CONFIG

        try:
            print(uri)
            self.controller.connect_to_ctx(uri)

            # Context attributes
            ctx_attrs = self.controller.get_all_attrs()
            hw_model = ctx_attrs.get("hw_model")
            self.ui.tabWidget.setTabText(1, hw_model)
            self.ui.lbl_hw_model_dyn.setText(hw_model)
            self.ui.lbl_hw_version_dyn.setText(ctx_attrs.get("hw_version"))
            self.ui.lbl_hw_serial_dyn.setText(ctx_attrs.get("hw_serial"))
            self.ui.lbl_carrier_model_dyn.setText(ctx_attrs.get("carrier_model"))
            self.ui.lbl_carrier_version_dyn.setText(ctx_attrs.get("carrier_version"))
            self.ui.lbl_carrier_serial_dyn.setText(ctx_attrs.get("carrier_serial"))
            self.ui.lbl_firmware_dyn.setText(self.controller.get_desc())

            self.ui.transceiver_tab.setEnabled(True)
            self.ui.phy_tab.setEnabled(True)
            # self.ui.serdes_tab.setEnabled(True)

            self.populate_cb(self.ui.cb_tx_vco, self.controller.get_device_freqs(TX_DEVICE, "vco_available"))
            self.ui.cb_tx_vco.setCurrentText(self.controller.get_device_attrs(TX_DEVICE).get("vco").value)

            self.populate_cb(self.ui.cb_rx_vco, self.controller.get_device_freqs(RX_DEVICE, "vco_available"))
            self.ui.cb_rx_vco.setCurrentText(self.controller.get_device_attrs(RX_DEVICE).get("vco").value)

            self.tx_read_regs()
            self.rx_read_regs()
        except Exception as e:
            self.__logger.write(LogType.IIO_DEVICE, "Failed to connect device {} \n {}"
                                .format(uri, traceback.format_exc()))
            self.update_contexts()
            self.forget_ctx()

            QtWidgets.QMessageBox.critical(self, "Failed to connect to device", str(e))

    def forget_ctx(self):
        self.controller.remove_ctx()
        self.init_ctx_ui()
        self.ui.cb_available_contexts.setCurrentText(NO_DEVICE_OPTION)

    def device_power_switch(self, device: str, checked: bool):
        self.__logger.write(LogType.UI, "Set device {}, attr {}, to {}"
                            .format(device, "enabled", "1" if checked else "0"))
        self.controller.set_device_attr(device, "enabled", "1" if checked else "0")

    def tx_autotuning_switch(self, checked: bool):
        self.__logger.write(LogType.UI, "Set device {}, attr {}, to {}"
                            .format(MWC, "tx_autotuning", "1" if checked else "0"))
        self.controller.set_device_attr(MWC, "tx_autotuning", "1" if checked else "0")
        self.ui.cb_tx_rfvga.setEnabled(not checked)

    def rx_autotuning_switch(self, checked: bool):
        self.__logger.write(LogType.UI, "Set device {}, attr {}, to {}"
                            .format(MWC, "rx_autotuning", "1" if checked else "0"))
        self.controller.set_device_attr(MWC, "rx_autotuning", "1" if checked else "0")
        self.ui.cb_rx_bbcoarse1.setEnabled(not checked)
        self.ui.cb_rx_bbcoarse2.setEnabled(not checked)
        self.ui.cb_rx_bbfine.setEnabled(not checked)

    def tx_auto_ifvga_switch(self, checked: bool):
        self.__logger.write(LogType.UI, "Set device {}, attr {}, to {}"
                            .format(MWC, "tx_auto_ifvga", "1" if checked else "0"))
        self.controller.set_device_attr(MWC, "tx_auto_ifvga", "1" if checked else "0")
        self.ui.cb_tx_ifvga.setEnabled(not checked)

    def rx_auto_ifvga_rflna_switch(self, checked: bool):
        self.__logger.write(LogType.UI, "Set device {}, attr {}, to {}"
                            .format(MWC, "rx_auto_ifvga_rflna", "1" if checked else "0"))
        self.controller.set_device_attr(MWC, "rx_auto_ifvga_rflna", "1" if checked else "0")
        self.ui.cb_rx_ifvga.setEnabled(not checked)
        self.ui.cb_rx_rflna.setEnabled(not checked)

    def tx_read_regs(self):
        self.__logger.write(LogType.UI, "Refresh TX registers")

        row = 0
        for i in range(28):
            if i == 0 or (12 < i < 16):
                continue
            reg_value = hex(self.controller.reg_read(TX_DEVICE, i))
            self.ui.tb_tx_registers.blockSignals(True)
            self.ui.tb_tx_registers.setItem(row, 1, QtWidgets.QTableWidgetItem(str(reg_value)))
            self.ui.tb_tx_registers.blockSignals(False)
            row = row + 1

    def rx_read_regs(self):
        self.__logger.write(LogType.UI, "Refresh RX registers")

        row = 0
        for i in range(28):
            if 9 < i < 16:
                continue
            reg_value = hex(self.controller.reg_read(RX_DEVICE, i))
            self.ui.tb_rx_registers.blockSignals(True)
            self.ui.tb_rx_registers.setItem(row, 1, QtWidgets.QTableWidgetItem(str(reg_value)))
            self.ui.tb_rx_registers.blockSignals(False)
            row = row + 1

    def reset_device(self):
        q = QtWidgets.QMessageBox()
        q.setText("Do you want to reset the device?")
        q.setWindowTitle("Reset device")
        q.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes |
                             QtWidgets.QMessageBox.StandardButton.No)

        reply = q.exec()
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.__logger.write(LogType.UI, "Reset device")
            self.controller.set_device_attr(MWC, "reset", "1")
        else:
            return

        self.__logger.write(LogType.IIO_DEVICE, "Reset device {}".format(MWC))

        self.tx_read_regs()
        self.rx_read_regs()

    def load_regs(self, device: str):
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open registers file", "Text files (*.txt)")
        if file_name == "":
            return

        with open(file_name, 'r') as infile:
            for line in infile.readlines()[1:]:
                reg_index = int(line.split(',')[0].strip('"'))
                reg_value = int(str(line.split(',')[1]).strip('"\n'))

                self.controller.reg_write(device, reg_index, reg_value)

        if device == RX_DEVICE:
            self.rx_read_regs()
        elif device == TX_DEVICE:
            self.tx_read_regs()

        self.__logger.write(LogType.DEFAULT, "Registers saved to file {}, for device {}".format(file_name, device))

    def save_regs(self, tb: QtWidgets.QTableWidget, file_name: str):
        file_name, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save registers content", file_name,
                                                             "Text files (*.txt)")

        if file_name != "":
            with open(file_name, 'w') as outfile:
                outfile.write("\"Address\",\"Data\"\n")
                for i in range(tb.rowCount()):
                    reg_index = str(int(tb.item(i, 0).text(), 0))
                    reg_value = str(int(tb.item(i, 1).text(), 0))

                    outfile.write("\"" + reg_index + "\",")
                    outfile.write("\"" + reg_value + "\"\n")

                self.__logger.write(LogType.DEFAULT, "Registers saved to file {}".format(file_name))
