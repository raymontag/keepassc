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
    
    def send_cmd(self, *cmd):
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

        tmp = [password, key]
        tmp.extend(cmd)
        cmd_chain = self.build_message(tmp)

        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect(self.server_address)
            logging.info('Connected to '+self.server_address[0]+':'+
                         str(self.server_address[1]))
            conn.settimeout(60)
            self.sendmsg(conn, cmd_chain)
            answer = self.receive(conn)
        except:
            raise
        else:
            conn.close()

        return answer

    def find(self, title):
        try:
            answer = self.send_cmd(b'FIND', title)
            if answer[:4] == b'FAIL':
                raise OSError(answer.decode())
            return answer.decode()
        except (OSError, TypeError) as err:
            logging.error(err.__str__())
            return err.__str__()

