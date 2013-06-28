import logging
import socket
import struct

from Crypto.Hash import SHA256

from keepassc.conn import Connection

class Client(Connection):
    """The KeePassC client"""

    def __init__(self, loglevel, logfile, server_address = 'localhost',
                 server_port = 50000, agent_port = 50001, password = None,
                  keyfile = None):
        Connection.__init__(self, loglevel, logfile, password, keyfile)
        self.server_address = (server_address, server_port)
        self.agent_address = ('localhost', agent_port)
    
    def connect_server(self):
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            conn.connect(self.server_address)
        except:
            raise
        else:
            logging.info('Connected to '+self.server_address[0]+':'+
                         str(self.server_address[1]))
        conn.settimeout(5)

        if self.keyfile is not None:
            with open(self.keyfile, 'rb') as keyfile:
                key = keyfile.read()
                keyfile.close()
        else:
            key = b''
        if self.password is None:
            password = b''
        else:
            password = self.password.encode() 

        self.sendmsg(conn, password)
        self.sendmsg(conn, key)
        ret = self.receive(conn)
        if ret[:4] == b'FAIL':
            logging.error(ret.decode())
            return False
        else:
            return conn

    def find(self, title):
        try:
            conn = self.connect_server()
            if conn is False:
                raise OSError("FAIL: Wrong password")
            self.sendmsg(conn, b'FIND')
            answer = self.receive(conn)
            if answer[:4] == b'FAIL':
                raise OSError(answer.decode())
            self.sendmsg(conn, title)
            answer = self.receive(conn)
            if answer[:4] == b'FAIL':
                raise OSError(answer.decode())
            return answer
        except (OSError, TypeError) as err:
            logging.error(err.__str__())
            return err.__str__()
        else:
            conn.close()

