#!/usr/bin/python
import socket
import select
from algorithm import *


class EasyNetClientTCP:

    _clientSocket = None

    def __init__(self,pIp,pPort):
        self._key = ""
        self._cipher = None
        try:
            self._clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._clientSocket.connect((pIp,pPort))
            self._clientSocket.setblocking(0)
        except:
            self._clientSocket.close()
            print(("Can not connect to Server with IP: " + str(pIp)))



    def getPacket(self,buf = 1024):
        if(self._key == ""):
            return self._clientSocket.recv(buf)
        else:
            msg = self._clientSocket.recv(buf)
            return self._cipher.decrypt (msg)

    def getPacketBl(self,buf = 1024):
        self._clientSocket.setblocking(1)
        if(self._key == ""):
            return self._clientSocket.recv(buf)
        else:
            msg = self._clientSocket.recv(buf)
            return self._cipher.decrypt (msg)

    def sendPacket(self,msg):
        if(self._key == ""):
            return self._clientSocket.send(msg)
        else:
            newmsg = self._cipher.encrypt(msg)
            return self._clientSocket.send(newmsg)

    def setKey(self,pKey):
        self._cipher = des(pKey, CBC, "\0\0\0\0\0\0\0\0", pad=None, padmode=PAD_PKCS5)
        self._key = pKey

    def quit(self):
        self._clientSocket.shutdown(socket.SHUT_RDWR)
        self._clientSocket.close()
