import socket
import struct

from Crypto.Hash import SHA256

from keepassc.conn import Connection
from keepassc.helper import ecb_decrypt, transform_key

class Client(Connection):
    """The KeePassC client"""

    def __init__(self, server_address = 'localhost', 
                 server_port = 50000, agent_port = 50001, password = None,
                 keyfile = None):
        Connection.__init__(self, password, keyfile)
        self.server_address = (server_address, server_port)
        self.agent_address = ('localhost', agent_port)
    
    def init_connection(self, address):
        """Get encryption details from server"""

        try:
            sock = self.connect_server()
            sock.sendall(b'NEWEND') # only b'NEW' is handled by server
            data = self.receive(sock)
        except OSError:
            return False # TODO log err
        else:
            if data is False:
                return False
        finally:
            sock.close()

        try:
            # SHA256 32Bytes long
            decrypted_data = ecb_decrypt(self.masterkey, data[:-32])
            if self.verify_decryption(decrypted_data, data[-32:]) is False:
                return False
        except TypeError:
            return False

        self.seed1 = struct.unpack('<32s', decrypted_data[:32])[0]
        self.seed2 = struct.unpack('<16s', decrypted_data[32:48])[0]
        self.rounds = struct.unpack('<I', decrypted_data[48:52])[0]
        self.vec = struct.unpack('<16s', decrypted_data[52:])[0]
        try:
            self.final_key = transform_key(self.masterkey, self.seed1, 
                                           self.seed2, self.rounds)
        except TypeError:
            return False

    def connect_server(self):
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            conn.connect(self.server_address)
        except OSError:
            return False
        return conn

    def find(self, title):
        try:
            conn = self.connect_server()
            self.sendmsg(conn, b'FIND')
            answer = self.receive(conn)
            if answer[:4] == b'FAIL':
                return answer
            elif answer is False:
                return b'FAIL: Can\'t receive answer from server'
            self.sendmsg(conn, title)
            answer = self.receive(conn)
            if answer[:4] == b'FAIL':
                return answer
            elif answer is False:
                return b'FAIL: Can\'t receive answer from server'
            data = self.decrypt_msg(answer)
            conn.close()
            return data
        except (OSError, TypeError):
            conn.close()
            return b'FAIL: An error occured'

