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
'200'
]

def composeSipMsg(method, address):
    """composeSipMsg creates a good formatted SIP message.

    Arguments needed are (method, address)

    """
    sipmsg = method + " " + "sip:" + address[2] + '@' + address[0] \
        + ' ' + "SIP/2.0\r\n\r\n"

    return sipmsg

def doClient(config_data, sip_method):
    """Main function of the program. It does server-client communication.

    Arguments needed are (server_addr, sipmsg)
    """

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as my_socket:
        try:
            my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            my_socket.connect((config_data['regproxy']['ip'],
            int(config_data['regproxy']['port'])))
            LINE = composeSipMsg()
            print("Sending: " + LINE)
            my_socket.send(bytes(LINE, 'utf-8'))
            while True:
                data = my_socket.recv(1024)
                if data:
                    print('received -- ', data.decode('utf-8'))
                    okline = 'a'
                    if data.decode() == okline:
                        LINE = composeSipMsg('ACK', server_addr)
                        my_socket.send(bytes(LINE, 'utf-8'))
                    break

        except (socket.gaierror, ConnectionRefusedError):
                sys.exit('Error: Server not found')

class handleXML(ContentHandler):

    def __init__(self):

        self.XML = {}

    def startElement(self, name, attrs):

        attdict = {}

        if name != 'config':
            for attrib in tags[name]:

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
    cHandler = handleXML()
    parser.setContentHandler(cHandler)
    parser.parse(open(config_file))
    config_data = cHandler.get_tags()
    print(config_data)
    doClient(config_data, sip_method)
