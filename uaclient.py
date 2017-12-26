#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""UDP client."""

import socket
import sys
from xml.sax import make_parser
from xml.sax.handler import ContentHandler

tags = ['account', 'uaserver', 'rtpaudio', 'regproxy', 'log', 'audio']




def doClient(server_addr, sipmsg):
    """Main function of the program. It does server-client communication.

    Arguments needed are (server_addr, sipmsg)
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as my_socket:
        try:
            my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            my_socket.connect((server_addr[0], server_addr[1]))
            LINE = composeSipMsg(sipmsg, server_addr)
            print("Sending: " + LINE)
            my_socket.send(bytes(LINE, 'utf-8'))
            while True:
                data = my_socket.recv(1024)
                if data:
                    print('received -- ', data.decode('utf-8'))
                    okline = 'SIP/2.0 100 Trying\r\n\r\n'
                    okline = okline + 'SIP/2.0 180 Ringing\r\n\r\n'
                    okline = okline + 'SIP/2.0 200 OK\r\n\r\n'
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




    def get_tags(self, file):

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

    #doClient(SERVER_ADDR, SIPMSG)
    parser = make_parser()
    cHandler = handleXML()
    parser.setContentHandler(cHandler)
    parser.parse(open(config_file))
