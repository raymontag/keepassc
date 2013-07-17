import logging
import os
import signal
import socket
import ssl
import struct
import sys
import threading
from os.path import join

from Crypto.Hash import SHA256
from kppy import KPDB, KPError

from keepassc.conn import Connection
from keepassc.daemon import Daemon
from keepassc.helper import (get_passwordkey, get_filekey, get_key, 
                             transform_key, cbc_decrypt, cbc_encrypt, 
                             ecb_encrypt)

class Server(Connection, Daemon):
    """The KeePassC server daemon"""

    def __init__(self, pidfile, loglevel, logfile, address = 'localhost',
                 port = 50000, db = None, password = None, keyfile = None,
                 tls = False, tls_dir = None, tls_port = 50002, tls_req = False):
        Connection.__init__(self, loglevel, logfile, password, keyfile)
        Daemon.__init__(self, pidfile)
        if db is None:
            print('Need a database path')
            sys.exit(1)
        try:
            self.db = KPDB(db, password, keyfile)
        except KPError as err:
            print(err)
            logging.error(err.__str__())
            sys.exit(1)

        master = get_key(self.db.password, self.db.keyfile)
        self.final_key =  transform_key(master, self.db._transf_randomseed,
                                        self.db._final_randomseed, 
                                        self.db._key_transf_rounds)
        self.lookup = {
            b'FIND': self.find}
        self.address = (address, port)
        self.tls_address = (address, tls_port)
        self.sock = None
        self.tls_sock = None
        self.tls_req = tls_req
        
        if tls is True or tls_req is True:
            self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            cert = join(tls_dir, "servercert.pem")
            key = join(tls_dir, "serverkey.pem")
            self.context.load_cert_chain(certfile=cert, keyfile=key)
        else:
            self.context = None

        #Handle SIGTERM
        signal.signal(signal.SIGTERM, self.handle_sigterm)

    def check_password(self, password, keyfile):
        """Check received password"""
        
        master = get_key(password, keyfile, True)
        final =  transform_key(master, self.db._transf_randomseed,
                               self.db._final_randomseed, 
                               self.db._key_transf_rounds)
        return (self.final_key == final)

    def run(self):
        """Overide Daemon.run() and provide socets"""
        
        if self.tls_req is False:
            non_tls_thread = threading.Thread(target=self.handle_non_tls)
            non_tls_thread.start()
        if self.context is not None:
            tls_thread = threading.Thread(target=self.handle_tls)
            tls_thread.start()

    def handle_non_tls(self):
        try:
            # Listen for commands
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.bind(self.address)
            self.sock.listen(5)
        except OSError as err:
            logging.error(err.__str__())
            self.stop()
        else:
            logging.info('Server socket created on '+self.address[0]+':'+
                         str(self.address[1]))

        while True:
            conn, client = self.sock.accept()
            logging.info('Connection from '+client[0]+':'+str(client[1]))
            client_thread = threading.Thread(target=self.handle_client, args=(conn,))
            client_thread.start()

    def handle_tls(self):
        try:
            # Listen for commands
            self.tls_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tls_sock.bind(self.tls_address)
            self.tls_sock.listen(5)
        except OSError as err:
            logging.error(err.__str__())
            self.stop()
        else:
            logging.info('TLS-Server socket created on '+self.tls_address[0]+':'+
                         str(self.tls_address[1]))

        while True:
            try:
                conn_tmp, client = self.tls_sock.accept()
                conn = self.context.wrap_socket(conn_tmp, server_side = True)
            except ssl.SSLError as err:
                logging.error(err.__str__())
                continue
            logging.info('Connection from '+client[0]+':'+str(client[1]))
            client_thread = threading.Thread(target=self.handle_client, args=(conn,))
            client_thread.start()

    def handle_client(self, conn):
        conn.settimeout(60)

        try:
            msg = self.receive(conn)
            parts = msg.split(b'\xB2\xEA\xC0')
            password = parts.pop(0)
            keyfile = parts.pop(0)
            cmd = parts.pop(0)

            if password == b'':
                password = None
            else:
                password = password.decode()
            if keyfile == b'':
                keyfile = None
            if self.check_password(password, keyfile) is False:
                self.sendmsg(conn, b'FAIL: Wrong password')
                raise OSError("Received wrong password")
        except OSError as err:
            logging.error(err.__str__())
        else:
            try:
                if cmd in self.lookup:
                    self.lookup[cmd](conn, parts)
                else:
                    logging.error('Received a wrong command')
                    self.sendmsg(conn, b'FAIL: Command isn\'t available')
            except (OSError, ValueError):
                logging.error(err.__str__())
        finally:
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()

    def find(self, conn, cmd_misc):
        """Find entries and send them to connection"""

        title = cmd_misc[0]
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

    def handle_sigterm(self, signum, frame):
        self.db.close()
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
        del self.final_key
