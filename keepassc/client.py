import socket
import struct
import sys

from keepassc.daemon import Daemon
from keepassc.helper import ecb_decrypt, get_key

class Client(Daemon):
    def __init__(self, pidfile, address = 'localhost', port = 50000,
                 password = None, keyfile = None):
        super().__init__(pidfile)
        self.seed1 = None
        self.seed2 = None
        self.rounds = None
        self.vec = None
        self.password = password
        self.keyfile = keyfile
        self.address = (address, port)
    
    def run(self):
        self.init_connection(self.address)

    def init_connection(self, address):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(self.address)
            sock.sendall(b'NEWEND') # Only b'NEW' is handled by server
            data = self.receive(sock)
        finally:
            sock.close()
        data = ecb_decrypt(get_key(self.password, self.keyfile), data)
        self.seed1 = struct.unpack('<32s', data[:32])[0]
        self.seed2 = struct.unpack('<16s', data[32:48])[0]
        self.rounds = struct.unpack('<I', data[48:52])[0]
        self.vec = struct.unpack('<16s', data[52:68])[0]

    def receive(self, conn):
        """Receive a message from server"""

        data = b''
        while True:
            received = conn.recv(16)
            if b'END' in received:
                data += received[:received.find(b'END')]
                break
            else:
                data += received
                if data[-3:] == b'END':
                    data = data[:-3]
                    break
        return data
