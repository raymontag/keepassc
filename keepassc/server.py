'''
Copyright (C) 2012-2013 Karsten-Kai König <kkoenig@posteo.de>

This file is part of keepassc.

keepassc is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or at your
option) any later version.

keepassc is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License along
with keepassc.  If not, see <http://www.gnu.org/licenses/>.
'''

"""This file implements the server daemon.

Decorator:
    class waitDecorator(object)

Classes:
    class Server(Connection, Daemon)
"""

import logging
import signal
import socket
import ssl
import sys
import time
import threading
from datetime import datetime
from os import chdir
from os.path import join, expanduser, realpath

from kppy.database import KPDBv1
from kppy.exceptions import KPError

from keepassc.conn import *
from keepassc.daemon import Daemon
from keepassc.helper import get_key, transform_key

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
        
class Server(Daemon):
    """The KeePassC server daemon"""

    def __init__(self, pidfile, loglevel, logfile, address = None,
                 port = 50002, db = None, password = None, keyfile = None,
                 tls = False, tls_dir = None, tls_port = 50003, 
                 tls_req = False):
        Daemon.__init__(self, pidfile)

        try:
            logdir = realpath(expanduser(getenv('XDG_DATA_HOME')))
        except:
            logdir = realpath(expanduser('~/.local/share'))
        finally:
            logfile = join(logdir, 'keepassc', logfile)

        logging.basicConfig(format='[%(levelname)s] in %(filename)s:'
                                   '%(funcName)s at %(asctime)s\n%(message)s',
                            level=loglevel, filename=logfile,
                            filemode='a')

        if db is None:
            print('Need a database path')
            sys.exit(1)
            
        self.db_path = realpath(expanduser(db))

        # To use this idiom only once, I store the keyfile path
        # as a class attribute
        if keyfile is not None:
            keyfile = realpath(expanduser(keyfile))
        else:
            keyfile = None

        chdir("/var/empty")

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
            b'CHANGESECRET': self.change_password,
            b'NEWG': self.create_group,
            b'NEWE': self.create_entry,
            b'DELG': self.delete_group,
            b'DELE': self.delete_entry,
            b'MOVG': self.move_group,
            b'MOVE': self.move_entry,
            b'TITG': self.set_g_title,
            b'TITE': self.set_e_title,
            b'USER': self.set_e_user,
            b'URL': self.set_e_url,
            b'COMM': self.set_e_comment,
            b'PASS': self.set_e_pass,
            b'DATE': self.set_e_exp}

        self.sock = None
        self.net_sock = None
        self.tls_sock = None
        self.tls_req = tls_req
        
        if tls is True or tls_req is True:
            self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            cert = join(tls_dir, "servercert.pem")
            key = join(tls_dir, "serverkey.pem")
            self.context.load_cert_chain(certfile=cert, keyfile=key)
        else:
            self.context = None

        try:
            # Listen for commands
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.bind(("localhost", 50000))
            self.sock.listen(5)
        except OSError as err:
            print(err)
            logging.error(err.__str__())
            sys.exit(1)
        else:
            logging.info('Server socket created on localhost:50000')

        if self.tls_req is False and address is not None:
            try:
                # Listen for commands
                self.net_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.net_sock.bind((address, port))
                self.net_sock.listen(5)
            except OSError as err:
                print(err)
                logging.error(err.__str__())
                sys.exit(1)
            else:
                logging.info('Server socket created on '+address+':'+
                             str(port))

        if self.context is not None and address is not None:
            try:
                # Listen for commands
                self.tls_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.tls_sock.bind((address, tls_port))
                self.tls_sock.listen(5)
            except OSError as err:
                print(err)
                logging.error(err.__str__())
                sys.exit(1)
            else:
                logging.info('TLS-Server socket created on '+address+':'+
                             str(tls_port))


        #Handle SIGTERM
        signal.signal(signal.SIGTERM, self.handle_sigterm)

    def check_password(self, password, keyfile):
        """Check received password"""
        
        master = get_key(password, keyfile, True)
        remote_final =  transform_key(master, self.db._transf_randomseed,
                                      self.db._final_randomseed, 
                                      self.db._key_transf_rounds)
        master = get_key(self.db.password, self.db.keyfile)
        final =  transform_key(master, self.db._transf_randomseed,
                               self.db._final_randomseed, 
                               self.db._key_transf_rounds)
        return (remote_final == final)

    def run(self):
        """Overide Daemon.run() and provide socets"""
        
        try:
            local_thread = threading.Thread(target=self.handle_non_tls,
                                            args=(self.sock,))
            local_thread.start()
            if self.tls_req is False:
                non_tls_thread = threading.Thread(target=self.handle_non_tls,
                                                  args=(self.net_sock,))
                non_tls_thread.start()
            if self.context is not None:
                tls_thread = threading.Thread(target=self.handle_tls)
                tls_thread.start()
        except OSError as err:
            logging.error(err.__str__())
            self.stop()

    def handle_non_tls(self, sock):
        while True:
            try:
                conn, client = sock.accept()
            except OSError as err:
                # For correct closing
                if "Bad file descriptor" in err.__str__():
                    break
                logging.error(err.__str__())
            else:
                logging.info('Connection from '+client[0]+':'+str(client[1]))
                client_thread = threading.Thread(target=self.handle_client, 
                                                 args=(conn,client,))
                client_thread.daemon = True
                client_thread.start()

    def handle_tls(self):
        while True:
            try:
                conn_tmp, client = self.tls_sock.accept()
                conn = self.context.wrap_socket(conn_tmp, server_side = True)
            except (ssl.SSLError, OSError) as err:
                # For correct closing
                if "Bad file descriptor" in err.__str__():
                    break
                logging.error(err.__str__())
            else:
                logging.info('Connection from '+client[0]+':'+str(client[1]))
                client_thread = threading.Thread(target=self.handle_client, 
                                                 args=(conn, client,))
                client_thread.daemon = True
                client_thread.start()

    def handle_client(self, conn, client):
        conn.settimeout(60)

        try:
            msg = receive(conn)
            parts = msg.split(b'\xB2\xEA\xC0')
            parts.append(client)
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
                sendmsg(conn, b'FAIL: Wrong password')
                raise OSError("Received wrong password")
        except OSError as err:
            logging.error(err.__str__())
        else:
            try:
                if cmd in self.lookup:
                    self.lookup[cmd](conn, parts)
                else:
                    logging.error('Received a wrong command')
                    sendmsg(conn, b'FAIL: Command isn\'t available')
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
        sendmsg(conn, msg.encode())

    def send_db(self, conn, parts):
        with open(self.db_path, 'rb') as handler:
            buf = handler.read()
        sendmsg(conn, buf)

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
                    sendmsg(conn, b"FAIL: Parent doesn't exist anymore. "
                                       b"You should refresh")
                    return
        self.db.save()
        self.send_db(conn, [])

    @waitDecorator
    def change_password(self, conn, parts):
        client_add = parts[-1][0]
        if client_add != "localhost" and client_add != "127.0.0.1":
            sendmsg(conn, b'Password change from remote is not allowed')

        new_password = parts.pop(0).decode()
        new_keyfile = parts.pop(0).decode()
        if new_password == '':
            self.db.password = None
        else:
            self.db.password = new_password

        if new_keyfile == '':
            self.db.keyfile = None
        else:
            self.db.keyfile = realpath(expanduser(new_keyfile))

        self.db.save()
        sendmsg(conn, b"Password changed")

    @waitDecorator
    def create_entry(self, conn, parts):
        title = parts.pop(0).decode()
        url = parts.pop(0).decode()
        username = parts.pop(0).decode()
        password = parts.pop(0).decode()
        comment = parts.pop(0).decode()
        y = int(parts.pop(0))
        mon = int(parts.pop(0))
        d = int(parts.pop(0))
        root = int(parts.pop(0))

        for i in self.db.groups:
            if i.id_ == root:
                self.db.create_entry(i, title, 1, url, username, password,
                                     comment, y, mon, d)
                break
            elif i is self.db.groups[-1]:
                sendmsg(conn, b"FAIL: Group for entry doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])
    
    @waitDecorator
    def delete_group(self, conn, parts):
        group_id = int(parts.pop(0))
        time = datetime(int(parts[0]), int(parts[1]), int(parts[2]),
                        int(parts[3]), int(parts[4]), int(parts[5]))
        time = time.timetuple()

        for i in self.db.groups:
            if i.id_ == group_id:
                if self.check_last_mod(i, time) is True:
                    sendmsg(conn, b"FAIL: Group was modified. You should "
                                       b"refresh and if you're sure you want "
                                       b"to delete this group try it again.")
                    return
                i.remove_group()
                break
            elif i is self.db.groups[-1]:
                sendmsg(conn, b"FAIL: Group doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])

    @waitDecorator
    def delete_entry(self, conn, parts):
        uuid = parts.pop(0)
        time = datetime(int(parts[0]), int(parts[1]), int(parts[2]),
                        int(parts[3]), int(parts[4]), int(parts[5]))
        time = time.timetuple()
       
        for i in self.db.entries:
            if i.uuid == uuid:
                if self.check_last_mod(i, time) is True:
                    sendmsg(conn, b"FAIL: Entry was modified. You should "
                                       b"refresh and if you're sure you want "
                                       b"to delete this entry try it again.")
                    return
                i.remove_entry()
                break
            elif i is self.db.entries[-1]:
                sendmsg(conn, b"FAIL: Entry doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])

    @waitDecorator
    def move_group(self, conn, parts):
        group_id = int(parts.pop(0))
        root = int(parts.pop(0))

        for i in self.db.groups:
            if i.id_ == group_id:
                if root == 0:
                    i.move_group(self.db.root_group)
                else:
                    for j in self.db.groups:
                        if j.id_ == root:
                            i.move_group(j)
                            break
                        elif j is self.db.groups[-1]:
                            sendmsg(conn, b"FAIL: New parent doesn't "
                                               b"exist anymore. You should "
                                               b"refresh")
                            return
                break
            elif i is self.db.groups[-1]:
                sendmsg(conn, b"FAIL: Group doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])

    @waitDecorator
    def move_entry(self, conn, parts):
        uuid = parts.pop(0)
        root = int(parts.pop(0))

        for i in self.db.entries:
            if i.uuid == uuid:
                for j in self.db.groups:
                    if j.id_ == root:
                        i.move_entry(j)
                        break
                    elif j is self.db.groups[-1]:
                        sendmsg(conn, b"FAIL: New parent doesn't exist "
                                           b"anymore. You should refresh")
                        return
                break
            elif i is self.db.entries[-1]:
                sendmsg(conn, b"FAIL: Entry doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])
        
    @waitDecorator
    def set_g_title(self, conn, parts):
        title = parts.pop(0).decode()
        group_id = int(parts.pop(0))
        time = datetime(int(parts[0]), int(parts[1]), int(parts[2]),
                        int(parts[3]), int(parts[4]), int(parts[5]))
        time = time.timetuple()

        for i in self.db.groups:
            if i.id_ == group_id:
                if self.check_last_mod(i, time) is True:
                    sendmsg(conn, b"FAIL: Group was modified. You should "
                                       b"refresh and if you're sure you want "
                                       b"to edit this group try it again.")
                    return
                i.set_title(title)
                break
            elif i is self.db.groups[-1]:
                sendmsg(conn, b"FAIL: Group doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])

    @waitDecorator
    def set_e_title(self, conn, parts):
        title = parts.pop(0).decode()
        uuid = parts.pop(0)
        time = datetime(int(parts[0]), int(parts[1]), int(parts[2]),
                        int(parts[3]), int(parts[4]), int(parts[5]))
        time = time.timetuple()

        for i in self.db.entries:
            if i.uuid == uuid:
                if self.check_last_mod(i, time) is True:
                    sendmsg(conn, b"FAIL: Entry was modified. You should "
                                       b"refresh and if you're sure you want "
                                       b"to edit this entry try it again.")
                    return
                i.set_title(title)
                break
            elif i is self.db.entries[-1]:
                sendmsg(conn, b"FAIL: Entry doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])

    @waitDecorator
    def set_e_user(self, conn, parts):
        username = parts.pop(0).decode()
        uuid = parts.pop(0)
        time = datetime(int(parts[0]), int(parts[1]), int(parts[2]),
                        int(parts[3]), int(parts[4]), int(parts[5]))
        time = time.timetuple()

        for i in self.db.entries:
            if i.uuid == uuid:
                if self.check_last_mod(i, time) is True:
                    sendmsg(conn, b"FAIL: Entry was modified. You should "
                                       b"refresh and if you're sure you want "
                                       b"to edit this entry try it again.")
                    return
                i.set_username(username)
                break
            elif i is self.db.entries[-1]:
                sendmsg(conn, b"FAIL: Entry doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])

    @waitDecorator
    def set_e_url(self, conn, parts):
        url = parts.pop(0).decode()
        uuid = parts.pop(0)
        time = datetime(int(parts[0]), int(parts[1]), int(parts[2]),
                        int(parts[3]), int(parts[4]), int(parts[5]))
        time = time.timetuple()

        for i in self.db.entries:
            if i.uuid == uuid:
                if self.check_last_mod(i, time) is True:
                    sendmsg(conn, b"FAIL: Entry was modified. You should "
                                       b"refresh and if you're sure you want "
                                       b"to edit this entry try it again.")
                    return
                i.set_url(url)
                break
            elif i is self.db.entries[-1]:
                sendmsg(conn, b"FAIL: Entry doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])

    @waitDecorator
    def set_e_comment(self, conn, parts):
        comment = parts.pop(0).decode()
        uuid = parts.pop(0)
        time = datetime(int(parts[0]), int(parts[1]), int(parts[2]),
                        int(parts[3]), int(parts[4]), int(parts[5]))
        time = time.timetuple()

        for i in self.db.entries:
            if i.uuid == uuid:
                if self.check_last_mod(i, time) is True:
                    sendmsg(conn, b"FAIL: Entry was modified. You should "
                                       b"refresh and if you're sure you want "
                                       b"to edit this entry try it again.")
                    return
                i.set_comment(comment)
                break
            elif i is self.db.entries[-1]:
                sendmsg(conn, b"FAIL: Entry doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])

    @waitDecorator
    def set_e_pass(self, conn, parts):
        password = parts.pop(0).decode()
        uuid = parts.pop(0)
        time = datetime(int(parts[0]), int(parts[1]), int(parts[2]),
                        int(parts[3]), int(parts[4]), int(parts[5]))
        time = time.timetuple()

        for i in self.db.entries:
            if i.uuid == uuid:
                if self.check_last_mod(i, time) is True:
                    sendmsg(conn, b"FAIL: Entry was modified. You should "
                                       b"refresh and if you're sure you want "
                                       b"to edit this entry try it again.")
                    return
                i.set_password(password)
                break
            elif i is self.db.entries[-1]:
                sendmsg(conn, b"FAIL: Entry doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])

    @waitDecorator
    def set_e_exp(self, conn, parts):
        y = int(parts.pop(0))
        mon = int(parts.pop(0))
        d = int(parts.pop(0))
        uuid = parts.pop(0)
        time = datetime(int(parts[0]), int(parts[1]), int(parts[2]),
                        int(parts[3]), int(parts[4]), int(parts[5]))
        time = time.timetuple()

        for i in self.db.entries:
            if i.uuid == uuid:
                if self.check_last_mod(i, time) is True:
                    sendmsg(conn, b"FAIL: Entry was modified. You should "
                                       b"refresh and if you're sure you want "
                                       b"to edit this entry try it again.")
                    return
                i.set_expire(y, mon, d)
                break
            elif i is self.db.entries[-1]:
                sendmsg(conn, b"FAIL: Entry doesn't exist "
                                   b"anymore. You should refresh")
                return

        self.db.save()
        self.send_db(conn, [])

    def check_last_mod(self, obj, time):
       return obj.last_mod.timetuple() > time 

    def handle_sigterm(self, signum, frame):
        self.db.lock()
        if self.sock is not None:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        if self.net_sock is not None:
            self.net_sock.shutdown(socket.SHUT_RDWR)
            self.net_sock.close()
        if self.tls_sock is not None:
            self.tls_sock.shutdown(socket.SHUT_RDWR)
            self.tls_sock.close()
