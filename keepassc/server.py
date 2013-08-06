import logging
import os
import signal
import socket
import ssl
import struct
import sys
import time
import threading
from os.path import join, expanduser, realpath

from Crypto.Hash import SHA256
from kppy.database import KPDBv1
from kppy.exceptions import KPError

from keepassc.conn import Connection
from keepassc.daemon import Daemon
from keepassc.helper import (get_passwordkey, get_filekey, get_key, 
                             transform_key, cbc_decrypt, cbc_encrypt, 
                             ecb_encrypt)

class waitDecorator(object):
    def __init__(self, func):
        self.func = func
        self.lock = False

    def __get__(self, obj, type=None):
        return self.__class__(self.func.__get__(obj, type))

    def __call__(self, *args):
        while True:
            if self.lock == True:
                time.sleep(1)
                continue
            else:
                self.lock = True
                self.func(args[0], args[1])
                self.lock = False
                break
        
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

        self.db_path = realpath(expanduser(db))

        # To use this idiom only once, I store the keyfile path
        # as a class attribute
        if keyfile is not None:
            self.keyfile = realpath(expanduser(keyfile))
        else:
            self.keyfile = None

        try:
            self.db = KPDBv1(self.db_path, password, keyfile)
            self.db.load()
        except KPError as err:
            print(err)
            logging.error(err.__str__())
            sys.exit(1)

        self.lookup = {
            b'FIND': self.find,
            b'GET': self.send_db,
            b'NEWG': self.create_group}
        if tls_req is True:
            tls_port = port
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
        remote_final =  transform_key(master, self.db._transf_randomseed,
                                      self.db._final_randomseed, 
                                      self.db._key_transf_rounds)
        master = get_key(self.db.password, self.keyfile)
        final =  transform_key(master, self.db._transf_randomseed,
                               self.db._final_randomseed, 
                               self.db._key_transf_rounds)
        return (remote_final == final)

    def run(self):
        """Overide Daemon.run() and provide socets"""
        
        try:
            if self.tls_req is False:
                non_tls_thread = threading.Thread(target=self.handle_non_tls)
                non_tls_thread.start()
            if self.context is not None:
                tls_thread = threading.Thread(target=self.handle_tls)
                tls_thread.start()
        except OSError as err:
            logging.error(err.__str__())
            self.stop()

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
            except (OSError, ValueError) as err:
                logging.error(err.__str__())
        finally:
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()

    def find(self, conn, parts):
        """Find entries and send them to connection"""

        title = parts.pop(0)
        msg = ''
        for i in self.db.entries:
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

    def send_db(self, conn, parts):
        with open(self.db_path, 'rb') as handler:
            buf = handler.read()
        self.sendmsg(conn, buf)

    @waitDecorator
    def create_group(self, conn, parts):
        title = parts.pop(0).decode()
        root = int(parts.pop(0))
        if root == 0:
            self.db.create_group(title)
        else:
            for i in self.db.groups:
                if i.id_ == root:
                    self.db.create_group(title, i)
                    break
                elif i is self.db.groups[-1]:
                    self.sendmsg(conn, b"FAIL: Parent doesn't exist anymore. "
                                       b"You should refresh")
                    return
        self.db.save()
        self.send_db(conn, [])

    def handle_sigterm(self, signum, frame):
        self.db.close()
        if self.sock is not None:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        if self.tls_sock is not None:
            self.tls_sock.shutdown(socket.SHUT_RDWR)
            self.tls_sock.close()
