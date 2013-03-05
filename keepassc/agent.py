import socket
import struct
import sys

from Crypto.Hash import SHA256

from keepassc.client import Client
from keepassc.daemon import Daemon
from keepassc.helper import (cbc_encrypt, cbc_decrypt, ecb_decrypt, get_key, 
                             transform_key)

class Agent(Client, Daemon):
    """The KeePassC agent daemon"""

    def __init__(self, pidfile, server_address = 'localhost', 
                 server_port = 50000, agent_port = 50001, password = None,
                 keyfile = None):
        Client.__init__(self, server_address, server_port, agent_port, 
                        password, keyfile)
        Daemon.__init__(self, pidfile)
        self.lookup = {
            b'FIND': self.find}

    def run(self):
        """Overide Daemon.run() and provide sockets"""

        self.init_connection(self.server_address)
        
        # Listen for commands
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(self.agent_address)
        sock.listen(1)

        while True:
            conn, client = sock.accept()
            cmd = self.receive(conn)
            if cmd in self.lookup:
                self.lookup[cmd](conn)
            else:
                conn.sendall(b'Command isn\'t available')
            conn.close()

    def find(self, conn):
        """Find Entries"""

        serv = self.connect_server()
        self.sendmsg(serv, b'FIND')
        answer = self.receive(serv)
        if answer[:4] == b'FAIL':
            conn.sendall(answer)
            return
        else:
            conn.sendall(b'ACKEND')
        title = self.receive(conn)
        self.sendmsg(serv, title)
        answer = self.receive(serv)
        if answer[:4] == b'FAIL':
            conn.sendall(answer)
            return
        data = self.decrypt_msg(answer)
        if data is False:
            conn.sendall(b'FAIL: Decryption failed. Wrong password?END')
        else:
            conn.sendall(data+b'END')
        serv.close()
