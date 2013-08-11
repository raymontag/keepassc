"""This module implements the Connection class.

Classes:
    Connection(object)
"""

import logging
from os import getenv
from os.path import expanduser, realpath, join


class Connection(object):
    """This class represents a connection with some simple methods"""

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

    def build_message(self, parts):
        """Join many parts to one message with a seperator

        A message will look like

        b'foo\xB2\xEA\xC0bar\xB2\xEA\xC0foobar'

        so that it could easily splitted by .split

        """

        msg = b''
        for i in parts[:-1]:
            msg += i
            msg += b'\xB2\xEA\xC0' # \xB2\xEA\xC0 = BREAK
        msg += parts[-1]

        return msg

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
                if data[-4:] == b'\xDE\xAD\xE1\x1D':
                    data = data[:-4]
                    break
        return data

    def sendmsg(self, sock, msg):
        """Send message

        \xDE\xAD\xE1\x1D marks the end of the message

        """

        ip, port = sock.getpeername()
        try:
            logging.info('Send a message to '+ip+':'+str(port))
            # \xDE\xAD\xE1\x1D = DEAD END
            sock.sendall(msg + b'\xDE\xAD\xE1\x1D')
        except:
            raise

