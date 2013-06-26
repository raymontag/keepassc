import logging
import socket
import sys
from os.path import expanduser, realpath, join

from Crypto.Hash import SHA256

from keepassc.helper import cbc_encrypt, cbc_decrypt, get_key

class Connection(object):
    def __init__(self, loglevel = logging.ERROR, logfile = 'keepassc.log'):
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
            if b'END' in received:
                data += received[:received.find(b'END')]
                break
            else:
                data += received
                if data[-3:] == b'END':
                    data = data[:-3]
                    break
        return data

    def sendmsg(self, sock, msg):
        """Send message"""

        ip, port = sock.getpeername()
        try:
            logging.info('Send a message to '+ip+':'+str(port))
            sock.sendall(msg + b'END')
        except:
            raise

