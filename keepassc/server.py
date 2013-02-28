import sys
import socket

from keepassc.daemon import Daemon
from keepassc.helper import (get_passwordkey, get_filekey, transform_key, 
                             cbc_decrypt, cbc_encrypt, ecb_encrypt)

from Crypto.Hash import SHA256
from kppy import KPDB, KPError

class Server(Daemon):
    """The KeePassC server daemon"""

    def __init__(self, pidfile, address = 'localhost', port = 50000, db = None,
                 password = None, keyfile = None):
        super().__init__(pidfile)
        if db is None:
            print('Need a database path')
            sys.exit(1)
        try:
            self.db = KPDB(db, password, keyfile)
        except KPError as err:
            print(err)
            sys.exit(1)
        self.seed1 = self.db._transf_randomseed
        self.seed2 = self.db._final_randomseed
        self.rounds = self.db._key_transf_rounds
        self.vec = self.db._enc_iv

        self.lookup = {
            b'Find': self.find}
        self.address = (address, port)

    def run(self):
        """Overide Daemon.run() and provide sockets"""
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(self.address)
        sock.listen(1)
        conn, client = sock.accept()
        while True:
            cmd = self.receive(conn)
            if cmd is b'NEW':
                msg = bytes(self.seed1+'\n'+self.seed2+'\n'+self.rounds+'\n'+
                            str(self.vec))
                conn.sendall(ecb_encrypt(msg, self.get_key()))
            elif cmd in self.lookup:
                lookup[cmd](conn)
            else:
                conn.sendall(b'Command isn\'t available')
            conn.close()
                
    def receive(self, conn):
        """Receive a message from client"""

        data = b''
        while True:
            received = conn.recv(16)
            if received:
                data += received
            else:
                break
        if data == b'NEW':
            return data
        else:
            # Return decrypted data
            return cbc_decrypt(self.get_key(), data, self.vec)

    def get_key(self):
        """Get a key generated from KeePass-password and -keyfile"""

        if self.db.password is None:
            masterkey = get_filekey(self.db.keyfile)
        elif self.db.password is not None and self.db.keyfile is not None:
            passwordkey = get_passwordkey(self.db.password)
            filekey = get_filekey(self.db.keyfile)
            sha = SHA256.new()
            sha.update(passwordkey+filekey)
            masterkey = sha.digest()
        else:
            masterkey = get_passwordkey(self.db.password)

        final_key = transform_key(masterkey, self.seed1, self.seed2, self.rounds)
        return final_key

    def find(self, conn):
        """Find entries and send them to connection"""

        title = self.receive()
        for i in self.db._entries:
            if title.lower() in i.title.lower():
                msg = bytes('Title\n'+i.title+'\n\n')
                if i.url is not None:
                    msg += bytes('URL\n'+i.url+'\n\n')
                if i.username is not None:
                    msg += bytes('Username\n'+i.username+'\n\n')
                if i.password is not None:
                    msg += bytes('Password\n'+i.password+'\n\n')
                if i.creation is not None:
                    msg += bytes('Creation\n'+i.creation.__str__()+'\n\n')
                if i.last_access is not None:
                    msg += bytes('Access\n'+i.last_access.__str__()+'\n\n')
                if i.last_mod is not None:
                    msg += bytes('Modification\n'+i.last_mod.__str__()+'\n\n')
                if i.expire is not None:
                    msg += bytes('Expiration\n'+i.expire.__str__()+'\n\n')
                if i.comment is not None:
                    msg += bytes('Comment\n'+i.comment+'\n\n')
                conn.sendall(cbc_encrypt(msg, self.get_key(), self.vec))

