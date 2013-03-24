import sys
import socket
import struct

from Crypto.Hash import SHA256
from kppy import KPDB, KPError

from keepassc.conn import Connection
from keepassc.daemon import Daemon
from keepassc.helper import (get_passwordkey, get_filekey, get_key, 
                             transform_key, cbc_decrypt, cbc_encrypt, 
                             ecb_encrypt)

class Server(Connection, Daemon):
    """The KeePassC server daemon"""

    def __init__(self, pidfile, address = 'localhost', port = 50000, db = None,
                 password = None, keyfile = None):
        Connection.__init__(self, password, keyfile)
        Daemon.__init__(self, pidfile)
        if db is None:
            print('Need a database path')
            sys.exit(1)
        try:
            self.db = KPDB(db, password, keyfile)
        except KPError as err:
            print(err) # TODO log err
            sys.exit(1)

        self.seed1 = self.db._transf_randomseed
        self.seed2 = self.db._final_randomseed
        self.rounds = self.db._key_transf_rounds
        self.vec = self.db._enc_iv
        try:
            self.masterkey = get_key(self.db.password, self.db.keyfile)
            self.final_key = transform_key(self.masterkey, self.seed1, 
                                           self.seed2, self.rounds)
        except TypeError as err:
            print(err) # TODO log err
            sys.exit(1)

        self.lookup = {
            b'NEW': self.new_connection,
            b'FIND': self.find}
        self.address = (address, port)

    def run(self):
        """Overide Daemon.run() and provide sockets"""
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.bind(self.address)
        sock.listen(1)
        while True:
            try:
                conn, client = sock.accept()
            except OSError:
                continue
            conn.settimeout(5)
            try:
                cmd = self.receive(conn)
            except OSError:
                pass # TODO log error
            else:
                try:
                    if cmd != b'NEW':
                        cmd = self.decrypt_msg(cmd)
                    if cmd in self.lookup:
                        self.lookup[cmd](conn)
                    elif cmd is False:
                        conn.sendall(b'FAIL: Decryption of command failedEND')
                    else:
                        conn.sendall(b'FAIL: Command isn\'t availableEND')
                except OSError:
                    pass # TODO log error; connection will close
            finally:
                conn.close()

    def new_connection(self, conn):
        msg = (self.seed1+self.seed2+
               struct.pack('<I',self.rounds)+self.vec)
        test_hash = self.create_hash(msg)
        conn.sendall(ecb_encrypt(msg, self.masterkey)+test_hash+b'END')

    def find(self, conn):
        """Find entries and send them to connection"""

        conn.sendall(b'ACKEND')
        title = self.decrypt_msg(self.receive(conn))
        if title is False: # TODO logging
            conn.sendall(b'FAIL: Decryption of entry title failedEND')
            return False
        msg = ''
        for i in self.db._entries:
            if title.decode().lower() in i.title.lower():
                msg += 'Title: '+i.title+'\n'
                if i.url is not None:
                    msg += 'URL: '+i.url+'\n'
                if i.username is not None:
                    msg += 'Username: '+i.username+'\n'
                if i.password is not None:
                    msg += 'Password: '+i.password+'\n'
                if i.creation is not None:
                    msg += 'Creation: '+i.creation.__str__()+'\n'
                if i.last_access is not None:
                    msg += 'Access: '+i.last_access.__str__()+'\n'
                if i.last_mod is not None:
                    msg += 'Modification: '+i.last_mod.__str__()+'\n'
                if i.expire is not None:
                    msg += 'Expiration: '+i.expire.__str__()+'\n'
                if i.comment is not None:
                    msg += 'Comment: '+i.comment+'\n'
                msg += '\n'
        self.sendmsg(conn, msg.encode())

