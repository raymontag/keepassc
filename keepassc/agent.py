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

"""This module implements an agent for KeePassC

    Classes:
        Agent(Client, Daemon)
"""

import logging
import signal
import socket
import ssl
import sys
from hashlib import sha256
from os import chdir
from os.path import expanduser, realpath, isfile, join

from keepassc.conn import *
from keepassc.client import Client
from keepassc.daemon import Daemon


class Agent(Daemon):
    """The KeePassC agent daemon"""

    def __init__(self, pidfile, loglevel, logfile,
                 server_address = 'localhost', server_port = 50000,
                 agent_port = 50001, password = None, keyfile = None,
                 tls = False, tls_dir = None):
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

        self.lookup = {
            b'FIND': self.find,
            b'GET': self.get_db,
            b'GETC': self.get_credentials}

        self.server_address = (server_address, server_port)
        try:
            # Listen for commands
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.bind(("localhost", agent_port))
            self.sock.listen(1)
        except OSError as err:
            print(err)
            logging.error(err.__str__())
            sys.exit(1)
        else:
            logging.info('Agent socket created on localhost:'+
                         str(agent_port))

        if tls_dir is not None:
            self.tls_dir = realpath(expanduser(tls_dir)).encode()
        else:
            self.tls_dir = b''

        chdir("/var/empty")

        self.password = password
        # Agent is a daemon and cannot find the keyfile after run
        if keyfile is not None:
            with open(keyfile, "rb") as handler:
                self.keyfile = handler.read()
                handler.close()
        else:
            self.keyfile = b''

        if tls is True:
            self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            self.context.verify_mode = ssl.CERT_REQUIRED
            self.context.load_verify_locations(tls_dir + "/cacert.pem")
        else:
            self.context = None

        #Handle SIGTERM
        signal.signal(signal.SIGTERM, self.handle_sigterm)

    def send_cmd(self, *cmd):
        """Overrides Client.connect_server"""

        if self.password is None:
            password = b''
        else:
            password = self.password.encode()

        tmp = [password, self.keyfile]
        tmp.extend(cmd)
        cmd_chain = build_message(tmp)

        try:
            tmp_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.context is not None:
                conn = self.context.wrap_socket(tmp_conn)
            else:
                conn = tmp_conn
            conn.connect(self.server_address)
        except:
            raise
        else:
            logging.info('Connected to '+self.server_address[0]+':'+
                         str(self.server_address[1]))

        try:
            conn.settimeout(60)
            if self.context is not None:
                if not isfile(self.tls_dir.decode() + '/pin'):
                    sha = sha256()
                    sha.update(conn.getpeercert(True))
                    with open(self.tls_dir.decode() + '/pin', 'wb') as pin:
                        pin.write(sha.digest())
                else:
                    with open(self.tls_dir.decode() + '/pin', 'rb') as pin:
                        pinned_key = pin.read()
                    sha = sha256()
                    sha.update(conn.getpeercert(True))
                    if pinned_key != sha.digest():
                        return (b'FAIL: Server certificate differs from '
                                b'pinned certificate')
                cert = conn.getpeercert()
                try:
                    ssl.match_hostname(cert, "KeePassC Server")
                except:
                    return b'FAIL: TLS - Hostname does not match'
            sendmsg(conn, cmd_chain)
            answer = receive(conn)
        except:
            raise
        finally:
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()

        return answer

    def run(self):
        """Overide Daemon.run() and provide sockets"""

        while True:
            try:
                conn, client = self.sock.accept()
            except OSError:
                break

            logging.info('Connected to '+client[0]+':'+str(client[1]))
            conn.settimeout(60)

            try:
                parts = receive(conn).split(b'\xB2\xEA\xC0')
                cmd = parts.pop(0)
                if cmd in self.lookup:
                    self.lookup[cmd](conn, parts)
                else:
                    logging.error('Received a wrong command')
                    sendmsg(conn, b'FAIL: Command isn\'t available')
            except OSError as err:
                logging.error(err.__str__())
            finally:
                conn.shutdown(socket.SHUT_RDWR)
                conn.close()

    def find(self, conn, cmd_misc):
        """Find Entries"""

        try:
            answer = self.send_cmd(b'FIND', cmd_misc[0])
            sendmsg(conn, answer)
            if answer[:4] == b'FAIL':
                raise OSError(answer.decode())
        except (OSError, TypeError) as err:
            logging.error(err.__str__())

    def get_db(self, conn, cmd_misc):
        """Get the whole encrypted database from server"""

        try:
            answer = self.send_cmd(b'GET')
            sendmsg(conn, answer)
            if answer[:4] == b'FAIL':
                raise OSError(answer.decode())
        except (OSError, TypeError) as err:
            logging.error(err.__str__())

    def get_credentials(self, conn, cmd_misc):
        """Send password credentials to client"""

        if self.password is None:
            password = b''
        else:
            password = self.password.encode()
        if self.context:
            tls = b'True'
        else:
            tls = b'False'

        tmp = [password, self.keyfile, self.server_address[0].encode(),
               str(self.server_address[1]).encode(), tls,
               self.tls_dir]
        chain = build_message(tmp)
        try:
            sendmsg(conn, chain)
        except (OSError, TypeError) as err:
            logging.error(err.__str__())

    def handle_sigterm(self, signum, frame):
        """Handle SIGTERM"""

        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
        del self.keyfile

