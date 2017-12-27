#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""UDP client."""

import socket
import sys
from xml.sax import make_parser
from xml.sax.handler import ContentHandler

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

    return sipmsg

def doClient(config_data, sip_method, option):
    """Main function of the program. It does server-client communication.

    Arguments needed are (server_addr, sipmsg)
    """

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as my_socket:
        try:
            my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            my_socket.connect((config_data['regproxy']['ip'],
            int(config_data['regproxy']['port'])))
            LINE = composeSipMsg(sip_method, config_data, option)
            print("Sending: " + LINE)
            my_socket.send(bytes(LINE, 'utf-8'))
            while True:
                data = my_socket.recv(1024)
                if data:
                    print('received -- ', data.decode('utf-8'))
                    okline = 'SIP/2.0 401 Unauthorized'
                    if data.decode() == okline:
                        option = '3600\r\n' \
                        + 'Authorization: Digest \
                         response="123123212312321212123"'
                        LINE = composeSipMsg('INVITE', config_data, option)
                        my_socket.send(bytes(LINE, 'utf-8'))
                    break

        except (socket.gaierror, ConnectionRefusedError):
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
        sys.exit('Usage: python3 client.py method receiver@IP:SIPport')


    parser = make_parser()
    cHandler = handleXML(tags)
    parser.setContentHandler(cHandler)
    parser.parse(open(config_file))
    config_data = cHandler.get_tags()
    doClient(config_data, sip_method, option)
