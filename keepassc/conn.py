import logging
import socket
import sys
from os.path import expanduser, realpath, join

from Crypto.Hash import SHA256

from keepassc.helper import cbc_encrypt, cbc_decrypt, get_key

class Connection(object):
    def __init__(self, loglevel = logging.ERROR, logfile = 'keepassc.log',
                 password = None, keyfile = None):
        try:
            logdir = realpath(expanduser(getenv('XDG_DATA_HOME')))
        except:
            logdir = realpath(expanduser('~/.local/share'))
        finally:
            logfile = join(logdir, 'keepassc', logfile)

        logging.basicConfig(format='[%(levelname)s] in %(filename)s:'
                                   '%(funcName)s at %(asctime)s\n%(message)s',
                            level=loglevel, filename=logfile, 
                            filemode='a')
        self.password = password
        self.keyfile = keyfile

    def receive(self, conn):
        """Receive a message"""

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
                if data[-3:] == b'\xDE\xAD\xE1\x1D':
                    data = data[:-3]
                    break
        return data

    def sendmsg(self, sock, msg):
        """Send message"""

        ip, port = sock.getpeername()
        try:
            logging.info('Send a message to '+ip+':'+str(port))
            sock.sendall(msg + b'\xDE\xAD\xE1\x1D')
        except:
            raise

