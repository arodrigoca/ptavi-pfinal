#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Main class and program for a simple SIP server."""

import socketserver
import json
import time
import sched
import _thread
import sys
from xml.sax import make_parser
from xml.sax.handler import ContentHandler
from uaclient import handleXML
import socket

scheduler = sched.scheduler(time.time, time.sleep)

tags = {'server': ['servername', 'ip', 'port'],
'database': ['users', 'passwords'],
'log': ['path']
}

requests = ['INVITE', 'BYE', 'ACK']
responses = ['100', '180', '200', '404', '500', '401', '405']


def deleteUser(usersDict, user):
    """DeleteUser method deletes an user from the dictionary.

    Arguments needed are (dictionary, userToDelete).

    """
    try:
        del usersDict[user]
        print("User", user, "deleted", "because its entry expired")
        SIPRegisterHandler.register2json(usersDict)

    except KeyError:
        print("No entry for", user)


def schedDelete(usersDict, user):
    """schedDelete method schedules an user deletion when his expire time arrives.

    Arguments needed are (dictionary, userToDelete).

    """
    try:
        scheduler.enterabs(usersDict[user]["fromEpoch"], 1, deleteUser,
                           (usersDict, user))
        scheduler.run()
    except KeyError:
        pass


def registerUser(stringInfo, usersDict, handler):
    """registerUser method manages user registration and deletion.

    Arguments needed are (stringReceived, dictionary).

    This method also contains a thread call. For each user in your user
    dictionary, it call the second thread and schedules an user deletion
    with schedDelete function.

    """
    addrStart = stringInfo[1].find(":") + 1
    addrEnd = stringInfo[1].rfind(':')
    user = stringInfo[1][addrStart:addrEnd]
    expire_int = int(stringInfo[3].split("\r")[0])
    expire_time = time.strftime('%Y-%m-%d %H:%M:%S',
                                time.gmtime(time.time() + expire_int))

    tagsDictionary = {"address": handler.client_address,
                      "expires": expire_time,
                      "fromEpoch": time.time() + expire_int,
                      "registered": time.time()}

    usersDict[user] = tagsDictionary
    if expire_int == 0:
        deleteUser(usersDict, user)
    else:
        print("client", user, "registered", "for",
              expire_int, "seconds")

    _thread.start_new_thread(schedDelete, (usersDict, user))
    SIPRegisterHandler.register2json(usersDict)


def fordwardMessage(stringInfo, usersDict, message):

    addrStart = stringInfo[1].find(":") + 1
    user = stringInfo[1][addrStart:]
    try:
        ip = usersDict[user]['address'][0]
        port = usersDict[user]['address'][1]
        my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        my_socket.connect((ip, port))
        my_socket.send(bytes(message, 'utf-8'))

    except KeyError:
        print('user not found in database')


class SIPRegisterHandler(socketserver.DatagramRequestHandler):
    """Echo server class."""

    usersDict = {}

    def handle(self):
        """Handle method of the server class.

        (all requests will be handled by this method).

        """
        stringMsg = self.rfile.read().decode('utf-8')
        stringInfo = stringMsg.split(" ")
        stringSimplified = stringMsg.split('\r\n')
        try:
            if stringInfo[0] == 'REGISTER':
                if 'Digest' not in stringInfo:
                    self.wfile.write(b"SIP/2.0 401 Unauthorized\r\n\r\n")

                else:
                    registerUser(stringInfo, SIPRegisterHandler.usersDict, self)
                    self.wfile.write(b"SIP/2.0 200 OK\r\n\r\n")

            elif stringInfo[0] in requests:
                fordwardMessage(stringInfo, SIPRegisterHandler.usersDict, stringMsg)
                self.wfile.write(b"SIP/2.0 200 OK\r\n\r\n")

            else:
                self.wfile.write(b"SIP/2.0 400 Bad Request\r\n\r\n")
        except Exception as e:
                self.wfile.write(b"SIP/2.0 500 Server Internal Error\r\n\r\n")
                print("Server error:", e)

    @classmethod
    def register2json(self, usersDict):
        """register2json method prints user dictionary to json file.

        Arguments needed are (dictionary).

        """
        fileName = "registered.json"
        with open(fileName, "w+") as f:
            json.dump(usersDict, f, sort_keys=True, indent=4)

    @classmethod
    def json2registered(self):
        """json2registered method reads a json file and saves its content.

        Arguments needed are ().

        """
        try:
            with open("registered.json", "r+") as f:
                # print("Reading json file")
                initDict = json.load(f)
                self.usersDict = initDict
                for user in self.usersDict:
                    _thread.start_new_thread(schedDelete,
                                             (self.usersDict, user))
        except FileNotFoundError:
            print("json file not found")


if __name__ == "__main__":
    # Listens at localhost ('') port 6001
    # and calls the EchoHandler class to manage the request

    try:
        config_file = sys.argv[1]
        parser = make_parser()
        cHandler = handleXML(tags)
        parser.setContentHandler(cHandler)
        parser.parse(open(config_file))
        config_data = cHandler.get_tags()

        serv = socketserver.UDPServer(('', int(config_data['server']['port'])),
                                      SIPRegisterHandler)
        SIPRegisterHandler.json2registered()
        print("Server " + config_data['server']['servername']
        + ' listening at port ' + config_data['server']['port'])
        serv.serve_forever()
    except(KeyboardInterrupt, IndexError):
        print("Usage: python proxy_registrar.py config")
