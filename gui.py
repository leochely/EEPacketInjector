from PyQt5 import QtGui, QtCore, uic, QtWidgets
import sys
import tool
import threading
from dbg import CEdenEternalDebugger, stackDbg
import queue
from easyNet import EasyNetClientTCP
import hashlib
import binascii


ngPckNmb = 1
ngBlckNmb = 1

ip = 123
port = 1234
stackGui = queue.Queue()


class CMainGUI():

    def __init__(self):

        self.user = ""
        self.pw = ""
        self.queueStarted = False
        self.app = QtWidgets.QApplication(sys.argv)
        self.window = None
        self.sendDlg = None
        self.settingsDlg = None
        self.CClient = EasyNetClientTCP(ip, port)

        self.login = uic.loadUi("login.ui")

        self.login.show()
        self.login.loginBtn.clicked.connect(self.loginConnect)

        sys.exit(self.app.exec_())

    def loginConnect(self):

        self.user = str(self.login.userEdit.text())
        self.pw = hashlib.md5(str(self.login.passwordEdit.text())).hexdigest()
        self.login.setVisible(False)
        self.window = uic.loadUi("main.ui")
        self.sendDlg = uic.loadUi("send.ui")
        self.settingsDlg = uic.loadUi("settings.ui")
        self.blockDlg = uic.loadUi("block.ui")
        self.editBlockDlg = uic.loadUi("edblock.ui")
        self.window.listWidget.setColumnWidth(0, 50)
        self.window.listWidget.setColumnWidth(1, 80)
        self.window.listWidget.setColumnWidth(2, 60)
        self.window.listWidget.setColumnWidth(3, 493)
        self.window.listWidget.setColumnWidth(4, 100)
        self.window.listWidget.setSortingEnabled(True)
        self.window.listWidget.clear()
        self.window.listWidgetQuest.clear()
        self.window.listWidgetQuest2.clear()

        self.window.statusLbl.setText(
            "<font style='color: red;background: black;'>STATUS: Not injected</font>")
        self.log("::LOG STARTED::")
        self.window.show()
        self.window.listWidgetQuest.customContextMenuRequested.connect(
            self.openQuestContexMenu)
        self.window.listWidgetQuest2.customContextMenuRequested.connect(
            self.openQuestContexMenu2)

        self.window.actionExit.triggered.connect(self.quit)
        self.window.actionInject.triggered.connect(self.inject)

        self.window.actionSend.triggered.connect(self.openSendDialog)
        self.window.actionStop.triggered.connect(self.stopLog)
        self.window.actionStart.triggered.connect(self.startLog)
        self.window.actionSettings.triggered.connect(self.openSettingsDialog)
        self.window.clearBtn.clicked.connect(self.clearLog)

        self.window.listWidget.doubleClicked.connect(self.addPacketToSend)
        self.window.listWidget.customContextMenuRequested.connect(
            self.openLoggerContexMenu)
        self.sendDlg.sendBtn.clicked.connect(self.send)

        self.sendDlg.listBlocker.customContextMenuRequested.connect(
            self.openBlockListContexMenu)

        self.blockDlg.addBtn.clicked.connect(self.addToBlockList)
        self.editBlockDlg.addBtn.clicked.connect(self.clickedEditBlock)
        self.sendDlg.startBtn.clicked.connect(self.startBlocking)
        self.sendDlg.stopBtn.clicked.connect(self.stopBlocking)
        self.settingsDlg.connect(self.settingsDlg.opacitySlider, QtCore.SIGNAL(
            'valueChanged(int)'), self.changeOpacity)

        self.log("GUI configuration successfull")

    def openBlockListContexMenu(self, position):
        self.ctMenuQuest = QtGui.QMenu()
        self.questStart = self.ctMenuQuest.addAction("Edit")
        self.questStart.triggered.connect(self.editBlockItem)
        self.questFinish = self.ctMenuQuest.addAction("Remove")
        self.questFinish.triggered.connect(self.removeBlockItem)
        self.ctMenuQuest.exec_(
            self.sendDlg.listBlocker.viewport().mapToGlobal(position))

    def removeBlockItem(self):
        oItem = self.sendDlg.listBlocker.currentItem()
        a = self.sendDlg.listBlocker.indexFromItem(oItem)
        c = a.row()
        b = self.sendDlg.listBlocker.takeTopLevelItem(c)

    def editBlockItem(self):
        oItem = self.sendDlg.listBlocker.currentItem()
        self.editBlockDlg.connectionLbl.setText(oItem.text(1))
        self.editBlockDlg.sigEdit.setText(oItem.text(2))
        self.editBlockDlg.idLbl.setText(oItem.text(0))
        self.editBlockDlg.packetEdit.insertPlainText(oItem.text(3))
        self.editBlockDlg.show()

    def clickedEditBlock(self):
        oItem = self.sendDlg.listBlocker.currentItem()
        self.editBlockDlg.setVisible(False)
        a = self.sendDlg.listBlocker.indexFromItem(oItem)
        c = a.row()
        b = self.sendDlg.listBlocker.takeTopLevelItem(c)

        item = QtGui.QTreeWidgetItem()
        item.setText(0, self.editBlockDlg.idLbl.text())
        item.setText(1, self.editBlockDlg.connectionLbl.text())
        item.setText(2, self.editBlockDlg.sigEdit.text())
        item.setText(3, self.editBlockDlg.packetEdit.toPlainText())

        self.sendDlg.listBlocker.insertTopLevelItem(c, item)

    def changeOpacity(self, event):
        val = self.settingsDlg.opacitySlider.value()
        self.window.setWindowOpacity(1.0 - (val / 100.0) + 0.3)
        self.settingsDlg.setWindowOpacity(1.0 - (val / 100.0) + 0.3)
        self.sendDlg.setWindowOpacity(1.0 - (val / 100.0) + 0.3)

    def startBlocking(self):
        self.sendDlg.startBtn.setEnabled(False)
        self.sendDlg.stopBtn.setEnabled(True)
        self.sendDlg.listBlocker.setEnabled(False)
        for i in range(0, self.sendDlg.listBlocker.topLevelItemCount()):
            item = self.sendDlg.listBlocker.topLevelItem(i)
            stackGui.put("MSG_BLOCK|" + item.text(1) +
                         "|" + item.text(2) + item.text(3))
        stackGui.put("MSG_RBLOCK")

    def stopBlocking(self):
        self.sendDlg.stopBtn.setEnabled(False)
        self.sendDlg.startBtn.setEnabled(True)
        self.sendDlg.listBlocker.setEnabled(True)
        stackGui.put("MSG_SBLOCK")

    def addToBlockList(self):
        oItem = self.window.listWidget.currentItem()
        item = QtGui.QTreeWidgetItem()
        item.setText(0, self.blockDlg.idLbl.text())
        item.setText(1, self.blockDlg.connectionLbl.text())
        item.setText(2, self.blockDlg.sigEdit.text())
        item.setText(3, self.blockDlg.packetEdit.toPlainText())
        self.sendDlg.listBlocker.insertTopLevelItem(ngBlckNmb - 1, item)
        self.blockDlg.setVisible(False)

    def debug(self):
        self.dbg = CEdenEternalDebugger("_Launcher.exe")

    def quit(self):
        stackGui.put("MSG_EXIT")
        self.queueStarted = False
        self.app.quit()

    def handleQueue(self):
        while self.queueStarted:
            sMsg = stackDbg.get()
            if(sMsg == "MSG_INJECTED"):
                self.window.actionInject.setEnabled(False)
                self.window.actionStart.setEnabled(True)
                self.window.actionSend.setEnabled(True)
                self.window.statusLbl.setText(
                    "<font style='color: black;background: green;'>STATUS: Injected, have fun</font>")
                self.log("Injection successfull")
                self.addQuests()

            elif(sMsg == "MSG_NOT_INJECTED"):
                self.window.actionInject.setEnabled(True)
                self.window.actionStart.setEnabled(False)
                self.window.actionSend.setEnabled(False)
                self.log(
                    "Injection failed! Game not running or not started as administrator")

            elif(sMsg[:3] == "SND"):
                if(self.window.chkSend.isChecked()):
                    bUnknown = True
                    sPacket = sMsg.split('|')
                    file = open("config/send.cfg", "r")
                    sSig = sPacket[1][:4]
                    for line in file:
                        ids = line.split('|')
                        if(sSig == ids[0]):
                            self.addPacketItem(
                                sPacket[1], "[C->S]", ids[1], 50, 205, 50)
                            bUnknown = False
                            break
                    file.close()
                    if(bUnknown):
                        self.addPacketItem(
                            sPacket[1], "[C->S]", "ID_UNKNOWN", 8, 205, 8)

            elif(sMsg[:3] == "RCV"):
                if(self.window.chkRecv.isChecked()):
                    bUnknown = True
                    sPacket = sMsg.split('|')
                    file = open("config/recv.cfg", "r")
                    sSig = sPacket[1][:4]
                    for line in file:
                        ids = line.split('|')
                        if(sSig == ids[0]):
                            self.addPacketItem(
                                sPacket[1], "[S->C]", ids[1], 165, 42, 42)
                            bUnknown = False
                            break
                    file.close()
                    if(bUnknown):
                        self.addPacketItem(
                            sPacket[1], "[S->C]", "ID_UNKNOWN", 165, 00, 00)

            elif(sMsg[:9] == "QUEST_RCV"):
                self.CClient.sendPacket(
                    "ID_LOGIN|" + self.user + "|" + self.pw)
                logged = self.CClient.getPacketBl()
                if(logged == "USER LOGGED IN"):
                    self.window.listWidgetQuest2.clear()
                    sMessage = sMsg.split('|')
                    sPacket = sMessage[1]
                    i = 0
                    fobj = open("db/t_mission.ini", "r")
                    for line in fobj:
                        id = line.split('|')
                        if(sPacket != ""):
                            if(id[0] == str(int(sPacket, 16))):
                                item = QtGui.QTreeWidgetItem()
                                qbrush = QtGui.QBrush(
                                    QtGui.QColor(165, 42, 42))
                                item.setText(0, id[0])
                                if(id[1].find("LVL") == -1):
                                    lvl = "unknown"
                                    name = id[1]
                                else:
                                    lvl = id[1][:5]
                                    name = id[1][7:]
                                item.setText(1, lvl)
                                item.setText(2, name)
                                item.setText(3, id[2])
                                self.window.listWidgetQuest2.insertTopLevelItem(
                                    i, item)
                                i += 1
                    fobj.close()
                else:
                    self.quit()
            elif(sMsg[:10] == "EDIT_QUEST"):
                self.CClient.sendPacket(
                    "ID_LOGIN|" + self.user + "|" + self.pw)
                logged = self.CClient.getPacketBl()
                if(logged == "USER LOGGED IN"):
                    sMessage = sMsg.split('|')
                    sPacket = sMessage[1]
                    sAction = sMessage[2]
                    nQuestId = int(sPacket, 16)
                    fobj = open("db/t_mission.ini", "r")
                    if(sAction == "03"):
                        for line in fobj:
                            id = line.split('|')
                            if(id[0] == str(nQuestId)):
                                item = QtGui.QTreeWidgetItem()
                                qbrush = QtGui.QBrush(
                                    QtGui.QColor(165, 42, 42))
                                if(id[1].find("LVL") == -1):
                                    lvl = "unknown"
                                    name = id[1]
                                else:
                                    lvl = id[1][:5]
                                    name = id[1][7:]
                                item.setText(0, id[0])
                                item.setText(1, lvl)
                                item.setText(2, name)
                                item.setText(3, id[2])
                                self.window.listWidgetQuest2.insertTopLevelItem(
                                    0, item)
                                break
                    elif(sAction == "04"):
                        pass
                    else:
                        list = self.window.listWidgetQuest2.findItems(
                            str(nQuestId), QtCore.Qt.MatchExactly, 0)
                        try:
                            b = list[0]
                            a = self.window.listWidgetQuest2.indexFromItem(
                                list[0])
                            c = a.row()
                            b = self.window.listWidgetQuest2.takeTopLevelItem(
                                c)
                        except IndexError:
                            print("no quest")

                    fobj.close()
                else:
                    self.quit()

    def inject(self):
        self.dbgThread = threading.Thread(target=self.debug)
        self.checkThread = threading.Thread(target=self.handleQueue)
        self.checkThread.start()
        self.queueStarted = True
        self.dbgThread.start()

    def startLog(self):
        self.CClient.sendPacket("ID_LOGIN|" + self.user + "|" + self.pw)
        logged = self.CClient.getPacketBl()
        if(logged == "USER LOGGED IN"):
            self.window.actionStop.setEnabled(True)
            self.window.actionStart.setEnabled(False)
            self.window.actionSend.setEnabled(True)
            stackGui.put("MSG_START_LOG")
            self.log("Start debugging")
        else:
            self.quit()

    def stopLog(self):
        self.window.actionStart.setEnabled(True)
        self.window.actionStop.setEnabled(False)
        self.window.actionSend.setEnabled(False)
        stackGui.put("MSG_STOP_LOG")
        self.log("Stop debugging")

    def clearLog(self):
        global ngPckNmb
        self.window.listWidget.clear()
        self.log("Packetlist cleared")
        ngPckNmb = 1

    def openSendDialog(self):
        if(self.sendDlg.isVisible() == False):
            self.sendDlg.input.clear()
            self.log("Sendlist cleared")
            self.sendDlg.show()
            self.log("Sendlist opened")
        self.sendDlg.activateWindow()

    def openSettingsDialog(self):
        self.settingsDlg.show()

    def okSettings(self):
        self.settingsDlg.setVisible(False)

    def addPacketToSend(self):
        if(self.sendDlg.isVisible() == False):
            self.sendDlg.input.clear()
            self.log("Sendlist cleared")
            self.sendDlg.show()
            self.log("Sendlist opened")

        self.sendDlg.activateWindow()
        item = self.window.listWidget.currentItem()
        if(item != None):
            packet = item.text(2)
            packet += item.text(3)
            self.sendDlg.input.insertPlainText(str(packet) + "\n")
            self.log("Added packet to sendlist")
        else:
            self.log("No item selected to send")

    def send(self):
        self.CClient.sendPacket("ID_LOGIN|" + self.user + "|" + self.pw)
        logged = self.CClient.getPacketBl()
        if(logged == "USER LOGGED IN"):
            stackGui.put("MSG_SEND|" + self.sendDlg.input.toPlainText())
            self.log("Trying to send packets")
            # os.system("tools\sender.exe")
        else:
            self.quit()

    def openQuestContexMenu(self, position):
        self.ctMenuQuest = QtGui.QMenu()
        self.questStart = self.ctMenuQuest.addAction("Start")
        self.questStart.triggered.connect(self.startQuest)
        self.questFinish = self.ctMenuQuest.addAction("Finish")
        self.questFinish.triggered.connect(self.finishQuest)
        self.questOpen = self.ctMenuQuest.addAction("Open Dialog")
        self.questOpen.triggered.connect(self.openQuest)
        self.ctMenuQuest.exec_(
            self.window.listWidgetQuest.viewport().mapToGlobal(position))

    def openQuestContexMenu2(self, position):
        self.ctMenuQuest = QtGui.QMenu()
        self.questFinish = self.ctMenuQuest.addAction("Finish")
        self.questFinish.triggered.connect(self.finishQuest2)
        self.questOpen = self.ctMenuQuest.addAction("Open Dialog")
        self.questOpen.triggered.connect(self.openQuest2)
        self.ctMenuQuest.exec_(
            self.window.listWidgetQuest2.viewport().mapToGlobal(position))

    def openLoggerContexMenu(self, position):
        self.ctMenuQuest = QtGui.QMenu()
        self.questStart = self.ctMenuQuest.addAction("Add to sendlist")
        self.questStart.triggered.connect(self.addPacketToSend)
        self.questFinish = self.ctMenuQuest.addAction("Add to blocklist")
        self.questFinish.triggered.connect(self.openBlockAdder)
        self.ctMenuQuest.exec_(
            self.window.listWidget.viewport().mapToGlobal(position))

    def openBlockAdder(self):
        self.blockDlg.show()
        oItem = self.window.listWidget.currentItem()
        self.blockDlg.connectionLbl.setText(oItem.text(1))
        self.blockDlg.sigEdit.setText(oItem.text(2))
        self.blockDlg.idLbl.setText(oItem.text(4))
        self.blockDlg.packetEdit.insertPlainText(oItem.text(3))

    def startQuest(self):
        self.editQuest("0100", self.window.listWidgetQuest)

    def finishQuest(self):
        self.editQuest("0200", self.window.listWidgetQuest)

    def openQuest(self):
        self.editQuest("0900", self.window.listWidgetQuest)

    def finishQuest2(self):
        self.editQuest("0200", self.window.listWidgetQuest2)

    def openQuest2(self):
        self.editQuest("0900", self.window.listWidgetQuest2)

    def editQuest(self, pSig, pWidget):
        self.sendDlg.input.clear()
        items = pWidget.selectedItems()
        self.log("Trying to edit Quest")
        if(items != None):
            for oItem in items:
                sPacket = oItem.text(0)
                nID = hex(int(sPacket))
                nQuestID = nID[2:]
                if(len(nQuestID) == 3):
                    nRealQuestID = "0" + nQuestID
                sLeft = nRealQuestID[:2]
                sRight = nRealQuestID[2:]
                sSendPacket = "5700" + pSig + sRight + sLeft + "0000ffff"
                self.sendDlg.input.insertPlainText(sSendPacket + "\n")
                self.log("Added Questpacket with Sig:" + pSig + " to sendlist")
                # os.system("tools\sender.exe")
            stackGui.put("MSG_SEND|" + self.sendDlg.input.toPlainText())
        else:
            self.log("No Quest selected")

    def addQuests(self):
        fobj = open("db/t_mission.ini", "r")
        i = 0
        self.log("Load QuestDB")
        for line in fobj:
            ids = line.split('|')
            item = QtGui.QTreeWidgetItem()
            qbrush = QtGui.QBrush(QtGui.QColor(165, 42, 42))

            if(ids[1].find("LVL") == -1):
                lvl = "unknown"
                name = ids[1]
            else:
                lvl = ids[1][:5]
                name = ids[1][7:]

            item.setText(0, ids[0])
            item.setText(1, lvl)
            item.setText(2, name)
            item.setText(3, ids[2])

            self.window.listWidgetQuest.insertTopLevelItem(i, item)
            i += 1
        fobj.close()
        self.log("QuestDB Loaded")

    def log(self, pText):
        self.window.listLog.insertPlainText(pText + "\n")

    def addPacketItem(self, pPacket, pTransfer, id, r, g, b):
        global ngPckNmb
        qbrush = QtGui.QBrush(QtGui.QColor(r, g, b))
        item = QtGui.QTreeWidgetItem()
        item.setData(0, QtCore.Qt.DisplayRole, ngPckNmb)
        item.setText(1, pTransfer)
        item.setForeground(1, qbrush)
        qbrush = QtGui.QBrush(QtGui.QColor(70, 130, 180))
        sSig = pPacket[:4]
        sPacket = pPacket[4:]
        item.setText(2, sSig)
        item.setForeground(2, qbrush)
        item.setText(3, sPacket)
        sig = id.split('\n')
        item.setText(4, sig[0])
        qbrush = QtGui.QBrush(QtGui.QColor(r, g, b))
        item.setForeground(4, qbrush)
        self.window.listWidget.insertTopLevelItem(ngPckNmb - 1, item)
        ngPckNmb += 1

    def getSignatures(self):
        pass
