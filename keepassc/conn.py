'''
Copyright (C) 2012-2013 Karsten-Kai König <kkoenig@posteo.de>

This file is part of keepassc.

keepassc is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or at your
option) any later version.

keepassc is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License along
with keepassc.  If not, see <http://www.gnu.org/licenses/>.
'''

"""This module implements some functions for a connection.

Functions:
    build_message(parts)
    receive(conn)
    sendmsg(sock, msg)
"""

import logging


def build_message(parts):
    """Join many parts to one message with a seperator

    A message will look like

    b'foo\xB2\xEA\xC0bar\xB2\xEA\xC0foobar'

    so that it could easily splitted by .split

    parts has to be a tuple of bytestrings

    """

    msg = b''
    for i in parts[:-1]:
        msg += i
        msg += b'\xB2\xEA\xC0' # \xB2\xEA\xC0 = BREAK
    msg += parts[-1]

    return msg

def receive(conn):
    """Receive a message

    conn has to be the socket which receive the message

    A message has to end with the bytestring  b'\xDE\xAD\xE1\x1D'
    
    """

    ip, port = conn.getpeername()
    logging.info('Receiving a message from '+ip+':'+str(port))
    data = b''
    while True:
        try:
            received = conn.recv(16)
        except:
            raise
        if b'\xDE\xAD\xE1\x1D' in received:
            data += received[:received.find(b'\xDE\xAD\xE1\x1D')]
            break
        else:
            data += received
            if data[-4:] == b'\xDE\xAD\xE1\x1D':
                data = data[:-4]
                break
    return data

def sendmsg(sock, msg):
    """Send message

    sock is the socket which sends the message

    msg hast to be a bytestring

    """

    ip, port = sock.getpeername()
    try:
        logging.info('Send a message to '+ip+':'+str(port))
        # \xDE\xAD\xE1\x1D = DEAD END
        sock.sendall(msg + b'\xDE\xAD\xE1\x1D')
    except:
        raise

