from winappdbg import System, Debug, Process, HexDump
import binascii
import threading
import gui
import queue
from functools import reduce

stackDbg = queue.Queue()
nPacketCounter = 0


def toHex(s):
    lst = []
    for ch in s:
        hv = hex(ord(ch)).replace('0x', '')
        if len(hv) == 1:
            hv = '0' + hv
        lst.append(hv)

    return reduce(lambda x, y: x + y, lst)


class CEdenEternalDebugger():
    def __init__(self, pFilename):
        System.request_debug_privileges()
        self.hSendAddress = "0x2"
        self.hRecvAddress = "0x4"
        self.bQueueStarted = False
        self.bStartLog = False
        self.bSend = False
        self.bBlock = False
        self.lBlockSend = []
        self.lBlockRecv = []
        self.lBlock = []
        try:
            self.oDebug = Debug(self.handlerEvent)
            self.oDebug.system.scan_processes()
            for (process, name) in self.oDebug.system.find_processes_by_filename(pFilename):
                self.oDebug.attach(process.get_pid())
                stackDbg.put("MSG_INJECTED")
                self.bQueueStarted = True
                self.checkThread = threading.Thread(target=self.handleQueue)
                self.checkThread.start()
                self.oDebug.loop()
        finally:
            stackDbg.put("MSG_NOT_INJECTED")
            self.bQueueStarted = False
            self.oDebug.stop()

    def handleQueue(self):
        while self.bQueueStarted:
            sMsg = gui.stackGui.get()
            if(sMsg == "MSG_START_LOG"):
                self.bStartLog = True
            elif(sMsg == "MSG_STOP_LOG"):
                self.bStartLog = False
            elif(sMsg == "MSG_EXIT"):
                self.oDebug.stop()
            elif(sMsg[:8] == "MSG_SEND"):
                sSend = sMsg.split('|')
                self.bSend = True
                self.sSendMsg = sSend[1]
            elif(sMsg[:9] == "MSG_BLOCK"):
                sBlock = sMsg[10:]
                split = sBlock.split('|')
                if(split[0] == "[C->S]"):
                    self.lBlockSend.append(split[1])
                elif(split[0] == "[S->C]"):
                    self.lBlockRecv.append(split[1])

            elif(sMsg == "MSG_RBLOCK"):
                self.bBlock = True

            elif(sMsg == "MSG_SBLOCK"):
                self.bBlock = False
                del self.lBlock[:]
                del self.lBlockRecv[:]
                del self.lBlockSend[:]

    def handlerEvent(self, event):
        nPid = event.get_pid()
        if(self.bStartLog == True):
            event.debug.break_at(nPid, self.hSendAddress, self.recvOutPackets)
            event.debug.break_at(nPid, self.hRecvAddress, self.recvInPackets)
        else:
            event.debug.dont_break_at(nPid, self.hSendAddress)
            event.debug.dont_break_at(nPid, self.hRecvAddress)

    def recvOutPackets(self, event):
        nPid = event.get_pid()
        oProcess = Process(nPid)

        if(self.bStartLog == True):
            stackMem = event.get_thread().get_sp()
            address = event.get_process().read_pointer(stackMem + 0x4)

            if(oProcess.is_address_readable(address)):
                hPacket = self.checkOutPacket(address, oProcess)
                if(self.bBlock == True):
                    if(len(self.lBlockSend) > 0):
                        for pck in self.lBlockSend:
                            if(hPacket == pck):
                                bytes = len(hPacket) / 2
                                packie = hPacket[:4]
                                for i in range(0, bytes - 2):
                                    packie += "00"
                                if(len(packie) % 2 == 0):
                                    blockPacket = binascii.unhexlify(packie)
                                    oProcess.write(address, blockPacket)
                                else:
                                    packie += "0"
                                    blockPacket = binascii.unhexlify(packie)
                                    oProcess.write(address, blockPacket)
                                hPacket = self.checkOutPacket(
                                    address, oProcess)
                if(hPacket[:2] == "01"):
                    if(self.bSend == True):
                        sSendPacket = self.sendPacket(oProcess, address)

                        if(sSendPacket != "NOWRITE"):
                            if(sSendPacket != None):
                                stackDbg.put("SND|" + sSendPacket)
                        else:
                            stackDbg.put("SND|" + hPacket)
                    else:
                        stackDbg.put("SND|" + hPacket)
                else:
                    stackDbg.put("SND|" + hPacket)

        else:
            event.debug.dont_break_at(nPid, self.hSendAddress)

    def recvInPackets(self, event):
        nPid = event.get_pid()
        oProcess = Process(nPid)

        if(self.bStartLog == True):

            #RECV_LENGTH_ADDRESS = 0x0018FC04
            #RECV_ADDRESS = 0x0018FC10
            RECV_LENGTH_ADDRESS = 0x0018FC14
            RECV_ADDRESS = 0x0018FC20
            if(oProcess.is_address_readable(RECV_ADDRESS)):
                address = oProcess.read_pointer(RECV_ADDRESS)
                if(oProcess.is_address_readable(address)):
                    sLength = oProcess.read(RECV_LENGTH_ADDRESS, 1)
                    nLength = int(toHex(sLength), 16)
                    if(nLength > 0):
                        file = open("config/recv.cfg", "r")
                        hPacket = self.checkInPacket(
                            address, oProcess, nLength)

                        if(self.bBlock == True):
                            if(len(self.lBlockRecv) > 0):
                                for pck in self.lBlockRecv:
                                    if(hPacket == pck):
                                        bytes = len(hPacket) / 2
                                        packie = ""
                                        for i in range(0, bytes):
                                            packie += "00"
                                        print(packie)
                                        blockPacket = binascii.unhexlify(
                                            packie)
                                        oProcess.write(address, blockPacket)
                                        hPacket = self.checkInPacket(
                                            address, oProcess, nLength)
                        if(hPacket[0:4] == '2901'):
                            stackDbg.put("RCV|" + hPacket)
                            self.recvQuests(hPacket)
                        elif(hPacket[0:4] == '5401'):
                            stackDbg.put("RCV|" + hPacket)
                            self.editQuests(hPacket)
                        elif(hPacket[0:2] == '36'):
                            stackDbg.put("RCV|" + hPacket)
                        else:
                            stackDbg.put("RCV|" + hPacket)

        else:
            event.debug.dont_break_at(nPid, self.hRecvAddress)

    def checkOutPacket(self, pAddress, pProcess):
        sLength = pProcess.read(pAddress - 2, 1)
        nLength = int(toHex(sLength), 16)
        sPacket = pProcess.read(pAddress, nLength)
        hPacket = HexDump.hexadecimal(sPacket)
        return hPacket

    def checkInPacket(self, pAddress, pProcess, pLength):
        sPacket = pProcess.read(pAddress, pLength)
        hPacket = HexDump.hexadecimal(sPacket)
        return hPacket

    def recvQuests(self, pPacket):
        i = 8
        sQuests = ""
        bRecv = True
        while bRecv:
            sWord = pPacket[i:i + 4]
            i += 8
            if(sWord == "0106"):
                bRecv = False
            else:
                sQuests += sWord

        i = 0
        for z in range(len(sQuests) / 4):
            sLeft = sQuests[i * 4:(i * 4) + 2]
            sRight = sQuests[(i * 4) + 2:(i * 4) + 4]
            sID = sRight + sLeft
            stackDbg.put("QUEST_RCV|" + sID)
            i += 1

    def editQuests(self, pPacket):
        sQuest = pPacket[6:10]
        sAction = pPacket[14:16]
        sLeft = sQuest[:2]
        sRight = sQuest[2:]
        sID = sRight + sLeft
        stackDbg.put("EDIT_QUEST|" + sID + "|" + sAction)

    def sendPacket(self, pProcess, pAddress):
        sText = self.sSendMsg
        sPackets = sText.split("\n")
        nLength = len(sPackets)

        global nPacketCounter

        sHeader = "1a00"
        try:
            sSendPacket = sHeader + str(sPackets[nPacketCounter])
            if(str(sPackets[nPacketCounter]) != ""):
                if((len(sSendPacket) / 2) < 26):
                    for i in range(1, 31 - (len(sSendPacket) / 2)):
                        sSendPacket += "00"
                hPacket = binascii.unhexlify(sSendPacket)
                pProcess.write(pAddress - 2, hPacket)

            nPacketCounter += 1

            if nPacketCounter == nLength - 1:
                self.bSend = False
                self.sSendMsg = ""
                nPacketCounter = 0

            if(str(sPackets[nPacketCounter]) != ""):
                return sSendPacket[4:]
            else:
                return "NOWRITE"

        except IndexError:
            print("packet sending error!")
            self.bSend = False
            self.sSendMsg = ""
            nPacketCounter = 0
