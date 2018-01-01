#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""UDP client."""

import socket
import sys
from xml.sax import make_parser
from xml.sax.handler import ContentHandler
import os
import datetime
import uuid
import hashlib

tags = {'account':['username', 'passwd'],
'uaserver':['ip', 'port'],
'rtpaudio':['port'],
'regproxy':['ip', 'port'],
'log':['path'],
'audio':['path']
}

sipmethods = ['REGISTER',
'INVITE',
'ACK',
'BYE'
]

sipresponses = ['100',
'190',
'200',
'400'
]

def logEvent(file, line):

    #print('printing to log file:', line)
    eventTime = datetime.datetime.today().strftime('%Y%m%d%H%M%S')
    file.write(eventTime + ' ' + line + '\r\n')


def sendSong(song, receiver_address):
    """sendSong calls command to be executed by shell.

    arguments needed are (song_name)

    """
    command = './mp32rtp -i ' + receiver_address[0] \
    + '-p ' + str(receiver_address[1])
    command += ' < ' + song
    print(command)
    os.system(command)

def composeSipMsg(method, config_data, options):
    """composeSipMsg creates a good formatted SIP message.

    Arguments needed are (method, address)

    """

    if method == 'REGISTER':
        sipmsg = method + " " + "sip:" + config_data['account']['username'] \
        + ':' + config_data['uaserver']['port'] \
        + ' ' + "SIP/2.0\r\n" + 'Expires: ' + options

    elif method == 'INVITE':
        sipmsg = method + " " + "sip:" + options + ' ' + "SIP/2.0\r\n" \
        + 'Content-Type: application/sdp\r\n\r\n' \
        + 'v=0\r\n' \
        + 'o=' + config_data['account']['username'] + ' ' \
        + config_data['uaserver']['ip'] + '\r\n' \
        + 's=mysession\r\n' \
        + 't=0\r\n' \
        + 'm=audio ' + config_data['rtpaudio']['port'] + ' ' + 'RTP'

    elif method == 'BYE':
        sipmsg = method + " " + "sip:" + options + ' ' + "SIP/2.0\r\n"

    elif method == 'ACK':
        sipmsg = method + " " + "sip:" + options + ' ' + "SIP/2.0\r\n"

    return sipmsg


def generateNonceResponse(password, nonce):

    salt = uuid.uuid4().hex
    cnonce = hashlib.md5(salt.encode() + password.encode()).hexdigest() + ':' + salt
    return hashlib.md5(salt.encode() + password.encode()).hexdigest() + ':' + salt


def doClient(config_data, sip_method, option):
    """Main function of the program. It does server-client communication.

    Arguments needed are (server_addr, sipmsg)
    """
    file = open(config_data['log']['path'], 'a')
    logEvent(file, 'Starting...')
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as my_socket:
        try:
            my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            my_socket.connect((config_data['regproxy']['ip'],
            int(config_data['regproxy']['port'])))
            #print(my_socket.getsockname())
            LINE = composeSipMsg(sip_method, config_data, option)
            print("Sending: " + LINE)
            my_socket.send(bytes(LINE, 'utf-8'))
            logEvent(file, 'Sent to ' + config_data['regproxy']['ip'] \
            + ':' + config_data['regproxy']['port'] + ': ' + LINE)
            while True:
                data = my_socket.recv(1024)
                if data:
                    print('received -- ', data.decode('utf-8'))
                    logEvent(file, 'Received from ' + config_data['regproxy']['ip'] \
                    + ':' + config_data['regproxy']['port'] + ': ' \
                     + data.decode())
                    okline = 'SIP/2.0 401 Unauthorized\r\n'
                    if okline in data.decode():
                        nonceIndex = data.decode().find('nonce=')
                        hashed_password = data.decode()[nonceIndex+7: \
                        len(data.decode())-1]
                        nonceResponse = \
                        generateNonceResponse(config_data['account']['passwd'],
                        hashed_password)
                        options = option + '\r\n' \
                        + 'Authorization: Digest response="' \
                        + nonceResponse + '"'
                        LINE = composeSipMsg('REGISTER', config_data, options)
                        logEvent(file, 'Sent to ' + config_data['regproxy']['ip'] \
                        + ':' + config_data['regproxy']['port'] + ': ' + LINE)
                        my_socket.send(bytes(LINE, 'utf-8'))

                    elif data.decode() == 'SIP/2.0 200 OK\r\n\r\n':
                        break
                        pass

                    elif data.decode() == 'SIP/2.0 404 User Not Found\r\n\r\n':
                            print('User not found')
                            break

                    elif data.decode() == 'SIP/2.0 405 Method Not Allowed\r\n\r\n':
                            print('User not found')
                            break

                    elif data.decode() == 'SIP/2.0 400 Bad Request\r\n\r\n':
                            print('Bad Request')
                            break

                    elif data.decode == 'SIP/2.0 500 Server Internal Error\r\n\r\n':
                            print('Server error')
                            break

                    elif data.decode() == 'SIP/2.0 403 Forbidden\r\n\r\n':
                            print('Authentication failed. Try Again')
                            break

                    else:
                        rtpaddress = data.decode()[data.decode().find('o='):]
                        rtpaddress = rtpaddress[rtpaddress.find(' ')+1:]
                        rtpaddress = rtpaddress[:rtpaddress.find('\r\n')]
                        rtpport = data.decode()[data.decode().find('m='):]
                        rtpport = rtpport[rtpport.find(' ')+1:]
                        rtpport = rtpport[:rtpport.find('\r\n')]
                        rtpport = rtpport[:rtpport.rfind(' ')]
                        rtpaddress = [rtpaddress, rtpport]
                        LINE = composeSipMsg('ACK', config_data, option)
                        my_socket.send(bytes(LINE, 'utf-8'))
                        logEvent(file, 'Sent to ' + config_data['regproxy']['ip'] \
                        + ':' + config_data['regproxy']['port'] + ': ' + LINE)
                        sendSong(config_data['audio']['path'], rtpaddress)
                        logEvent(file, 'Sent to ' + rtpaddress[0] \
                        + ':' + rtpaddress[1] + ': ' + 'RTP FILE')
                        print('All OK. Sending ACK and RTP')
                        break

        except (socket.gaierror, ConnectionRefusedError):
                logEvent(file, 'Error: No server listening at ' \
                + config_data['regproxy']['ip'] + ' port ' \
                + config_data['regproxy']['port'])
                sys.exit('Error: Server not found')

class handleXML(ContentHandler):

    def __init__(self, tags):

        self.XML = {}
        self.tags = tags

    def startElement(self, name, attrs):

        attdict = {}

        if name != 'config':
            for attrib in self.tags[name]:

                toAppend = attrs.get(attrib, '')
                attdict[attrib] = toAppend
                self.XML[name] = attdict


    def get_tags(self):

        tags = self.XML
        return tags


if __name__ == "__main__":
    # Creamos el socket, lo configuramos y lo atamos a un servidor/puerto
    try:

        config_file = sys.argv[1]
        sip_method = sys.argv[2].upper()
        option = sys.argv[3]

    except(FileNotFoundError, IndexError, ValueError):
        sys.exit('Usage: python uaclient.py config method option')


    parser = make_parser()
    cHandler = handleXML(tags)
    parser.setContentHandler(cHandler)
    parser.parse(open(config_file))
    config_data = cHandler.get_tags()
    doClient(config_data, sip_method, option)
