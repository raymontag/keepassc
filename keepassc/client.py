import logging
import socket
import struct

from Crypto.Hash import SHA256

from keepassc.conn import Connection

class Client(Connection):
    """The KeePassC client"""

    def __init__(self, loglevel, logfile, server_address = 'localhost',
                 server_port = 50000, agent_port = 50001):
        Connection.__init__(self, loglevel, logfile)
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
        return conn

    def init_connection(self, address):
        """Validate server certificate"""

        pass

    def find(self, title):
        try:
            conn = self.connect_server()
            self.sendmsg(conn, b'FIND')
            answer = self.receive(conn)
            if answer[:4] == b'FAIL':
                return answer
            self.sendmsg(conn, title)
            answer = self.receive(conn)
            if answer[:4] == b'FAIL':
                return answer
            return answer
        except (OSError, TypeError) as err:
            logging.error(err.__str__())
            return b'FAIL: '+err.__str__()
        finally:
            conn.close()

