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

        try:
            if self.init_connection(self.server_address) is False:
                self.stop()
            
            # Listen for commands
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(self.agent_address)
            sock.listen(1)
        except OSError:
            self.stop() # TODO log err

        while True:
            try:
                conn, client = sock.accept()
            except OSError:
                continue
            cmd = self.receive(conn)
            if cmd in self.lookup:
                self.lookup[cmd](conn)
            elif cmd is False:
                try:
                    conn.sendall(b'Message receive failed') 
                except OSError:
                    pass # conn seems to have a problem; go to close
            else:
                try:
                    conn.sendall(b'Command isn\'t available')
                except OSError:
                    pass
            conn.close()

    def find(self, conn):
        """Find Entries"""

        try:
            serv = self.connect_server()
            if self.sendmsg(serv, b'FIND') is False:
                conn.sendall(b'FAIL: Server doesn\'t receive message')
                raise OSError
            answer = self.receive(serv)
            if answer[:4] == b'FAIL':
                conn.sendall(answer)
                raise OSError
            elif answer is False:
                conn.sendall(b'FAIL: Can\'t receive message from server')
                raise OSError
            else:
                conn.sendall(b'ACKEND')
            title = self.receive(conn)
            if title is False:
                raise OSError
            if self.sendmsg(serv, title) is False:
                conn.sendall(b'FAIL: Can\'t send message to server')
                raise OSError
            answer = self.receive(serv)
            if answer[:4] == b'FAIL':
                conn.sendall(answer)
                raise OSError
            elif answer is False:
                conn.sendall(b'FAIL: Can\'t receive message from server')
                raise OSError
            data = self.decrypt_msg(answer)
            if data is False:
                conn.sendall(b'FAIL: Decryption failed. Wrong password?END')
            else:
                conn.sendall(data+b'END')
            serv.close()
        except (OSError, TypeError):
            serv.close() # TODO log err
            return False
