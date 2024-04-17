from PyQt5 import QtCore, QtGui, QtWidgets, QtSerialPort
import Ui_mainWin
import functools
import sys
import struct
import os

VERSION_STR = "SCPI GUI Ver 0.1"


class updateTarget():
    onoff = 0
    volt = 1
    curr = 2
    power = 3
    voltLim = 4
    currLim = 5
    _total = 6


class updateStatus():
    ready = 0
    send = 1


class mainWindow(QtWidgets.QMainWindow, Ui_mainWin.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.setWindowTitle(VERSION_STR)
        self.action_about.triggered.connect(lambda: QtWidgets.QMessageBox.about(
            self, VERSION_STR, """基于串口的SCPI上位机
测试环境 Win10@22H2
by Yuejin Tan
"""))
        self.action_qt.triggered.connect(functools.partial(
            QtWidgets.QMessageBox.aboutQt, self, "about qt"))

        self.tabWidget.currentChanged.connect(self.comStaRefreshSlot)
        self.pushButton_comCtrl.clicked.connect(self.comCtrlButtonSlot)

        # 串口号记录
        self._comAllCnt = 0

        # 实例化串口信息定时更新的定时器
        self.comUpdateTimer = QtCore.QTimer(self)
        self.comUpdateTimer.timeout.connect(self.comStatusRefreshUtil)
        self._comUpdateTimerTick = 200

        self._ser1Open = False
        self._serCom = QtSerialPort.QSerialPort()
        self._serCom.setDataBits(QtSerialPort.QSerialPort.Data8)
        self._serCom.setParity(QtSerialPort.QSerialPort.NoParity)
        self._serCom.setStopBits(QtSerialPort.QSerialPort.OneStop)
        self._serCom.setFlowControl(QtSerialPort.QSerialPort.NoFlowControl)

        # 主循环定时器
        self.mainLoopTimer = QtCore.QTimer(self)
        self.mainLoopTimer.timeout.connect(self.mainLoopSlot)
        self._mainLoopTimerTick = 50
        self.mainLoopTimer.start(self._mainLoopTimerTick)

        # 接收状态
        self.recvCnt = 0
        self.recvByteArr = bytearray(b"")

        self.noRecvCnt = 0
        self.noRecvCntMax = 4

        self.noFrameCnt = 0
        self.noFrameThd = 6

        self.updateNo = updateTarget.onoff
        self.updateSta = updateStatus.ready

        self.cmdList = []

        # 发送按钮功能绑定
        self.pushButton_on.clicked.connect(
            lambda: self.cmdList.append("OUTPUT ON\r\n".encode("UTF-8")))

        self.pushButton_off.clicked.connect(
            lambda: self.cmdList.append("OUTPUT OFF\r\n".encode("UTF-8")))

        self.pushButton_vlim.clicked.connect(
            lambda: self.cmdList.append(f"VOLT {self.doubleSpinBox_V.value():.1f}\r\n".encode("UTF-8")))

        self.pushButton_Ilim.clicked.connect(
            lambda: self.cmdList.append(f"CURR {self.doubleSpinBox_I.value():.1f}\r\n".encode("UTF-8")))

        self.show()

    # 串口界面部分

    def comStatusRefreshUtil(self):
        ports_list: list = QtSerialPort.QSerialPortInfo.availablePorts()
        if (len(ports_list) != self._comAllCnt):
            self._comAllCnt = len(ports_list)
            self.comboBox_com.clear()
            if len(ports_list) <= 0:
                print("无串口设备。")
            else:
                print("可用的串口设备如下：")
                for comPort in ports_list:
                    tempStr = f"{comPort.portName()} {comPort.description()}"
                    print(tempStr)
                    self.comboBox_com.addItem(tempStr)

    def comStaRefreshSlot(self, index):
        if (1 == index):
            # 进入串口界面
            self.comUpdateTimer.start(self._comUpdateTimerTick)
        else:
            # 离开串口界面
            self.comUpdateTimer.stop()

    def comCtrlButtonSlot(self):
        if (self._ser1Open):
            # 目前打开状态，准备关闭
            self._serCom.close()
            self._ser1Open = False
            self.pushButton_comCtrl.setText("连接")
            self.statusBar().showMessage(f"串口已断开！", 5000)
        else:
            # 目前关闭状态，准备打开
            try:
                namex = self.comboBox_com.currentText().split(" ")[0]
                if (namex == ""):
                    self.statusBar().showMessage(f"串口打开失败！请选择正确串口号", 5000)
                    return
                self._serCom.setPortName(namex)
                print(namex)
                self._serCom.setBaudRate(int(self.lineEdit_baud.text()))
                print(int(self.lineEdit_baud.text()))
                self._serCom.open(QtSerialPort.QSerialPort.ReadWrite)
            except Exception as e:
                self.statusBar().showMessage(f"串口打开失败！{str(e)}", 5000)
            else:
                self._ser1Open = True
                self.pushButton_comCtrl.setText("断开")
                self.statusBar().showMessage(f"{namex}已打开！", 5000)

    def recvProcess(self):
        errStr = ""
        val = 0

        try:
            val = float(self.recvByteArr)
        except Exception as e:
            errStr += e.__repr__()
        else:
            if (self.updateSta == updateStatus.send):
                if (self.updateNo == updateTarget.onoff):
                    if (val == 0):
                        self.label_on_off.setText("off")
                    else:
                        self.label_on_off.setText("on")
                elif (self.updateNo == updateTarget.volt):
                    self.label_volt.setText(f"{val:.1f} V")
                elif (self.updateNo == updateTarget.curr):
                    self.label_cur.setText(f"{val:.1f} A")
                elif (self.updateNo == updateTarget.power):
                    self.label_power.setText(f"{val:.1f} W")
                elif (self.updateNo == updateTarget.voltLim):
                    self.label_volt_lim.setText(f"{val:.1f} V")
                elif (self.updateNo == updateTarget.currLim):
                    self.label_cur_lim.setText(f"{val:.1f} A")
                else:
                    errStr += "内部错误1"

                self.updateNo = (self.updateNo+1) % updateTarget._total
                self.updateSta = updateStatus.ready
            else:
                errStr += "时序异常"

        if (errStr):
            self.statusBar().showMessage(f"解析错误："+errStr, 5000)
        else:
            self.noFrameCnt = 0

    def mainLoopSlot(self):
        if (self._ser1Open):

            # 收包逻辑
            # debugBa = bytearray()
            self.noFrameCnt += 1
            # 残包丢弃
            if (self._serCom.bytesAvailable()):
                self.noRecvCnt = 0
            else:
                self.noRecvCnt += 1
            if (self.noRecvCnt >= self.noRecvCntMax):
                # 判定为残包
                self.recvByteArr.clear()
                self.recvCnt = 0
                # 重新给指令
                self.updateSta = updateStatus.ready

            while (self._serCom.bytesAvailable() > 0):
                recvByte = self._serCom.read(1)
                # debugBa += recvByte
                if (recvByte == b'\x0d' or recvByte == b'\x0a'):
                    # 结尾
                    if (len(self.recvByteArr) > 0):
                        self.recvProcess()

                    self.recvByteArr.clear()
                    self.recvCnt = 0
                    # if(debugBa):
                    #     print(debugBa)
                else:
                    # 继续收
                    self.recvByteArr += recvByte
                    self.recvCnt += 1
                    # if(debugBa):
                    #     print(debugBa)

            # 发送逻辑
            if (self.cmdList):
                self._serCom.write(self.cmdList.pop(0))

            elif (self.updateSta == updateStatus.ready):
                if (self.updateNo == updateTarget.onoff):
                    self._serCom.write(b"OUTPUT?\r\n")
                elif (self.updateNo == updateTarget.volt):
                    self._serCom.write(b"MEASURE:VOLT?\r\n")
                elif (self.updateNo == updateTarget.curr):
                    self._serCom.write(b"MEASURE:CURR?\r\n")
                elif (self.updateNo == updateTarget.power):
                    self._serCom.write(b"MEASURE:POWER?\r\n")
                elif (self.updateNo == updateTarget.voltLim):
                    self._serCom.write(b"VOLT?\r\n")
                elif (self.updateNo == updateTarget.currLim):
                    self._serCom.write(b"CURR?\r\n")
                else:
                    self._serCom.write(b"*IDN?\r\n")

                self.updateSta = updateStatus.send

            # 判故逻辑
            if (self.noRecvCnt > self.noRecvCntMax):
                self.label_status.setText("串口无接收")

            elif (self.noFrameCnt > self.noFrameThd):
                self.label_status.setText("收帧无法解析")

            else:
                self.label_status.setText("正常")

        else:
            self.noFrameCnt = 0
            self.label_status.setText("串口未打开")
            self.cmdList.clear()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(VERSION_STR)

    cmdPar = QtCore.QCommandLineParser()
    cmdPar.addHelpOption()
    cmdPar.addVersionOption()
    cmdPar.setApplicationDescription(VERSION_STR)
    cmdPar.process(app)

    w = mainWindow()
    sys.exit(app.exec())
