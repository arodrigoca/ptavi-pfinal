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
from uaclient import logEvent
import socket
import uuid
import hashlib
from random import randint

scheduler = sched.scheduler(time.time, time.sleep)

tags = {'server': ['servername', 'ip', 'port'],
        'database': ['users', 'passwords'],
        'log': ['path']
        }

requests = ['INVITE', 'BYE', 'ACK']
responses = ['100', '180', '200', '404', '500', '401', '405']

config_file = sys.argv[1]
parser = make_parser()
cHandler = handleXML(tags)
parser.setContentHandler(cHandler)
parser.parse(open(config_file))
config_data = cHandler.get_tags()

pswds_file = config_data['database']['passwords']
with open(pswds_file, 'r') as f:
    pswds_data = f.read().splitlines()

random_nonce = 898989898798989898989


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
    clientIP = handler.client_address[0]
    clientPort = int(stringInfo[1][stringInfo[1].rfind(':')+1:])
    client_final_address = (clientIP, clientPort)
    addrStart = stringInfo[1].find(":") + 1
    addrEnd = stringInfo[1].rfind(':')
    user = stringInfo[1][addrStart:addrEnd]
    expire_int = int(stringInfo[3].split("\r")[0])
    expire_time = time.strftime('%Y-%m-%d %H:%M:%S',
                                time.gmtime(time.time() + expire_int))

    tagsDictionary = {"address": client_final_address,
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


def fordwardMessage(stringInfo, usersDict, message, handler, logfile):

    addrStart = stringInfo[1].find(":") + 1
    user = stringInfo[1][addrStart:]

    ip = usersDict[user]['address'][0]
    port = usersDict[user]['address'][1]
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    my_socket.connect((ip, port))
    my_socket.send(bytes(message, 'utf-8'))
    logEvent(logfile, 'Sent to ' +
             ip + ':' + str(port) + ': ' + message)
    if stringInfo[0] != 'ACK':
        while True:
            data = my_socket.recv(1024)
            if data:
                logEvent(logfile, 'Received from ' + ip +
                         ':' + str(port) + ': ' +
                         data.decode())
                handler.wfile.write(data)
                break


def generateNonce(password):

    range_start = 10**(21-1)
    range_end = (10**21)-1
    nonce = randint(range_start, range_end)
    global random_nonce
    random_nonce = nonce
    return str(nonce)


def checkPassword(hashed_password, user_password):

    print(random_nonce, 'is the random nonce')
    cnonce = hashlib.sha1()
    cnonce.update(str(random_nonce).encode())
    cnonce.update(user_password.encode())
    cnonce.hexdigest()
    print(cnonce.hexdigest(), 'is my cnonce digest')
    print(hashed_password, 'is received cnonce digest')
    if str(cnonce.hexdigest()) == hashed_password:
        return True

    else:
        return False


def findUserPassword(user):

    password = [s for s in pswds_data if user in s]
    password = password[0].split(' ')[1]
    return password
    print('USER PASSWORD:', password)


class SIPRegisterHandler(socketserver.DatagramRequestHandler):
    """Echo server class."""

    usersDict = {}

    def handle(self):
        """Handle method of the server class.

        (all requests will be handled by this method).

        """

        stringMsg = self.rfile.read().decode('utf-8')
        print(stringMsg)
        stringInfo = stringMsg.split(" ")
        stringSimplified = stringMsg.split('\r\n')
        notfound = False
        try:
            file = open(config_data['log']['path'], 'a')

        except:
            sys.exit('Log file not found. Finishing...')
            self.wfile.write(b'SIP/2.0 500 Server Internal Error')

        logEvent(file, 'Received from ' +
                 self.client_address[0] +
                 ':' + str(self.client_address[1]) + ': ' +
                 stringMsg)
        try:
            if stringInfo[0] == 'REGISTER':
                if 'Digest' not in stringInfo:
                    try:
                        addrStart = stringInfo[1].find(":") + 1
                        addrEnd = stringInfo[1].rfind(':')
                        user = stringInfo[1][addrStart:addrEnd]
                        userPassword = findUserPassword(user)
                        nonce = generateNonce(userPassword)
                    except Exception as e:
                        print(e)
                        logEvent(file, 'Sent to ' +
                                 self.client_address[0] +
                                 ':' + str(self.client_address[1]) + ': ' +
                                 "SIP/2.0 404 User Not Found\r\n\r\n")
                        l = 'SIP/2.0 404 User Not Found\r\n\r\n'
                        self.wfile.write(l.encode())
                        notfound = True

                    if not notfound:
                        logEvent(file, 'Sent to ' +
                                 self.client_address[0] +
                                 ':' + str(self.client_address[1]) + ': ' +
                                 "SIP/2.0 401 Unauthorized\r\n\r\n")
                        self.wfile.write(("SIP/2.0 401 Unauthorized\r\n" +
                                          'WWW Authenticate: Digest nonce=' +
                                          '"' +
                                          nonce + '"' + '\r\n\r\n').encode())

                else:
                    try:
                        addrStart = stringInfo[1].find(":") + 1
                        addrEnd = stringInfo[1].rfind(':')
                        user = stringInfo[1][addrStart:addrEnd]
                        userPassword = findUserPassword(user)
                        nonceIndex = stringMsg.find('response=')
                        hashed_password = stringMsg[nonceIndex+10:
                                                    len(stringMsg)-5]
                        print('RECEIVED NONCE:', hashed_password)
                        if checkPassword(hashed_password, userPassword):
                            print('Authentication correct')
                            registerUser(stringInfo,
                                         SIPRegisterHandler.usersDict,
                                         self)
                            logEvent(file, 'Sent to ' +
                                     self.client_address[0] +
                                     ':' + str(self.client_address[1]) + ': ' +
                                     "SIP/2.0 200 OK\r\n\r\n")
                            self.wfile.write(b"SIP/2.0 200 OK\r\n\r\n")

                        else:
                            print('Authentication incorrect')
                            logEvent(file, 'Sent to ' +
                                     self.client_address[0] +
                                     ':' + str(self.client_address[1]) + ': ' +
                                     "SIP/2.0  403 Forbidden\r\n\r\n")
                            self.wfile.write(b'SIP/2.0 403 Forbidden\r\n\r\n')

                    except Exception as e:
                        print(e)
                        logEvent(file, 'Sent to ' +
                                 self.client_address[0] +
                                 ':' + str(self.client_address[1]) + ': ' +
                                 "SIP/2.0 404 User Not Found\r\n\r\n")
                        self.wfile.write(b'SIP/2.0 404 User Not Found\r\n\r\n')

            elif stringInfo[0] in requests:

                if stringInfo[0] == 'INVITE':
                    origUser = stringSimplified[4].split('=')[1]
                    origUser = origUser[:origUser.rfind(' ')]
                    if origUser in SIPRegisterHandler.usersDict:
                        print('origin user in in database!')
                        try:
                            fordwardMessage(stringInfo,
                                            SIPRegisterHandler.usersDict,
                                            stringMsg, self, file)

                        except KeyError:
                            print('Requested user not found in database')
                            logEvent(file, 'Sent to ' +
                                     self.client_address[0] +
                                     ':' + str(self.client_address[1]) + ': ' +
                                     "SIP/2.0 404 User Not Found\r\n\r\n")
                            l = 'SIP/2.0 404 User Not Found\r\n\r\n'
                            self.wfile.write(l.encode())

                    else:
                        print('origin user not in database!')
                        logEvent(file, 'Sent to ' +
                                 self.client_address[0] +
                                 ':' + str(self.client_address[1]) + ': ' +
                                 "SIP/2.0 400 Bad Request\r\n\r\n")
                        self.wfile.write(b"SIP/2.0 400 Bad Request\r\n\r\n")
                elif stringInfo[0] == 'BYE':
                    try:
                        fordwardMessage(stringInfo,
                                        SIPRegisterHandler.usersDict,
                                        stringMsg, self, file)

                    except KeyError:
                        print('Requested user not found in database')
                        logEvent(file, 'Sent to ' +
                                 self.client_address[0] +
                                 ':' + str(self.client_address[1]) + ': ' +
                                 "SIP/2.0 404 User Not Found\r\n\r\n")
                        self.wfile.write(b'SIP/2.0 404 User Not Found\r\n\r\n')

                else:
                    fordwardMessage(stringInfo, SIPRegisterHandler.usersDict,
                                    stringMsg, self, file)

            else:
                logEvent(file, 'Sent to ' +
                         self.client_address[0] +
                         ':' + str(self.client_address[1]) + ': ' +
                         "SIP/2.0 405 Method Not Allowed\r\n\r\n")
                self.wfile.write(b"SIP/2.0 405 Method Not Allowed\r\n\r\n")
        except Exception as e:
                if e == '[Errno 111] Connection refused':
                    logEvent(file, 'Sent to ' +
                             self.client_address[0] +
                             ':' + str(self.client_address[1]) + ': ' +
                             "SIP/2.0 404 User Not Found\r\n\r\n")
                    self.wfile.write(b'SIP/2.0 404 User Not Found\r\n\r\n')

                else:
                    logEvent(file, 'Sent to ' +
                             self.client_address[0] +
                             ':' + str(self.client_address[1]) + ': ' +
                             "SIP/2.0 400 Bad Request\r\n\r\n")
                    self.wfile.write(b"SIP/2.0 400 Bad Request\r\n\r\n")
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
        serv = socketserver.UDPServer(('', int(config_data['server']['port'])),
                                      SIPRegisterHandler)
        SIPRegisterHandler.json2registered()
        print("Server " + config_data['server']['servername'] +
              ' listening at port ' + config_data['server']['port'])
        serv.serve_forever()
    except(KeyboardInterrupt, IndexError):
        print("Usage: python proxy_registrar.py config")
