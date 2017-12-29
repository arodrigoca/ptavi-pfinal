#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""SIP/UDP/RTP server."""

import socketserver
import sys
import os
from uaclient import handleXML
from xml.sax import make_parser
from xml.sax.handler import ContentHandler
import socket

tags = {'account':['username', 'passwd'],
'uaserver':['ip', 'port'],
'rtpaudio':['port'],
'regproxy':['ip', 'port'],
'log':['path'],
'audio':['path']
}

config_file = sys.argv[1]
parser = make_parser()
cHandler = handleXML(tags)
parser.setContentHandler(cHandler)
parser.parse(open(config_file))
config_data = cHandler.get_tags()



def composeSipAnswer(method, address):
    """composeSipAnswer builds a SIP message with correct format.

    arguments needed are (method, address)

    """
    sipmsg = method

    return sipmsg


def sendSong(song):
    """sendSong calls command to be executed by shell.

    arguments needed are (song_name)

    """
    command = './mp32rtp -i 127.0.0.1 -p 23032 < ' + song
    print(command)
    os.system(command)


def checkClientMessage(msg):
    """checkClientMessage checks if received message is correct formatted.

    arguments needed are (msg)

    """
    sipPart = msg[msg.find(' ')+1:]
    sipPart = [sipPart[:sipPart.find(':')+1],
               sipPart[sipPart.find(':')+1:sipPart.find('@')],
               sipPart[sipPart.find('@'):sipPart.find('@')+1],
               sipPart[sipPart.find('@')+1:sipPart.find(' ')],
               sipPart[sipPart.find(' ')+1:]]
    msg = msg.split(' ')

    if sipPart[0] == 'sip:' and sipPart[2] == '@':
        if msg[0] == 'INVITE' or msg[0] == 'ACK' or msg[0] == 'BYE':
            msgInfo = ['OK', msg[0]]
            return msgInfo

        else:
            msgInfo = ['METHOD NOT ALLOWED', msg[0]]
            return msgInfo

    else:
        msgInfo = ['BAD REQUEST', msg[0]]
        return msgInfo

def SDP():

    sipmsg = 'SIP/2.0 200 OK\r\n' \
    + 'Content-Type: application/sdp\r\n\r\n' \
    + 'v=0\r\n' \
    + 'o=' + config_data['account']['username'] + ' ' \
    + config_data['uaserver']['ip'] + '\r\n' \
    + 's=mysession\r\n' \
    + 't=0\r\n' \
    + 'm=audio ' + config_data['rtpaudio']['port'] + ' ' + 'RTP'

    return sipmsg


class SIPRegisterHandler(socketserver.DatagramRequestHandler):
    """Echo server class."""

    def handle(self):
        """handle do all the things relates do communication."""
        print('Replying to', self.client_address)
        my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        while 1:

            line = self.rfile.read()
            if line:

                print("user sent " + line.decode('utf-8'))
                checkClientMessage(line.decode('utf-8'))
                if checkClientMessage(line.decode('utf-8'))[0] == 'OK':

                    if checkClientMessage(line.decode('utf-8'))[1] == 'ACK':
                        #sendSong(sys.argv[3])
                        print('enviando cancion')

                    elif checkClientMessage(line.decode('utf-8'))[1] == 'BYE':
                        LINE = (composeSipAnswer('SIP/2.0 200 OK',
                                self.client_address) + '\r\n\r\n').encode()
                        self.wfile.write(LINE)

                    else:
                        print('METHOD ALLOWED')

                        LINE = (composeSipAnswer('SIP/2.0 100 Trying',
                                self.client_address) + '\r\n\r\n').encode()
                        self.wfile.write(LINE)
                        LINE = (composeSipAnswer('SIP/2.0 180 Ringing',
                                self.client_address) + '\r\n\r\n').encode()
                        self.wfile.write(LINE)
                        LINE = SDP().encode()
                        print(SDP())
                        self.wfile.write(LINE)

                elif checkClientMessage(line.decode('utf-8'))[0]\
                        == 'METHOD NOT ALLOWED':
                    print('METHOD NOT ALLOWED')
                    LINE = (composeSipAnswer('405 METHOD NOT ALLOWED',
                            self.client_address) + '\r\n').encode()
                    self.wfile.write(LINE)

                else:
                    print('BAD REQUEST')
                    LINE = (composeSipAnswer('400 BAD REQUEST',
                            self.client_address) + '\r\n').encode()
                    self.wfile.write(LINE)
            # Si no hay más líneas salimos del bucle infinito
            if not line:
                break


if __name__ == "__main__":
    # Creamos servidor de eco y escuchamos
    try:

        print(int(config_data['uaserver']['port']))
        serv = socketserver.UDPServer(('', int(config_data['uaserver']['port'])),
                                      SIPRegisterHandler)
        print("Listening..." + '\r\n')
        serv.serve_forever()

    except KeyboardInterrupt:
            sys.exit('Exiting')

    except IndexError:
            sys.exit('Usage: python3 server.py IP port audio_file')