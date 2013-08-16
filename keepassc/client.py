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

"""This module implements the Client class for KeePassC.

Classes:
    Client(Connection)
"""

import logging
import socket
import ssl
from os.path import join, expanduser, realpath, isfile
from hashlib import sha256

from keepassc.conn import *

class Client(object):
    """The KeePassC client"""

    def __init__(self, loglevel, logfile, server_address = 'localhost',
                 server_port = 50000, password = None, keyfile = None,
                 tls = False, tls_dir = None):
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

        self.password = password
        self.keyfile = keyfile
        self.server_address = (server_address, server_port)

        self.tls_dir = tls_dir

        if tls is True:
            self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            self.context.verify_mode = ssl.CERT_REQUIRED
            logging.error(tls_dir)
            self.context.load_verify_locations(tls_dir + "/cacert.pem")
        else:
            self.context = None

    def send_cmd(self, *cmd):
        """Send a command to server

        *cmd are arbitary byte strings

        """
        if self.keyfile is not None:
            with open(self.keyfile, 'rb') as keyfile:
                key = keyfile.read()
        else:
            key = b''
        if self.password is None:
            password = b''
        else:
            password = self.password.encode()

        tmp = [password, key]
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
                if not isfile(self.tls_dir + '/pin'):
                    sha = sha256()
                    sha.update(conn.getpeercert(True))
                    with open(self.tls_dir + '/pin', 'wb') as pin:
                        pin.write(sha.digest())
                else:
                    with open(self.tls_dir + '/pin', 'rb') as pin:
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

    def get_bytes(self, cmd, *misc):
        """Send a command and get the answer as bytes

        cmd is a bytestring with the command
        *misc are arbitary bytestring needed for the command

        """

        try:
            db_buf = self.send_cmd(cmd, *misc)
            if db_buf[:4] == b'FAIL':
                raise OSError(db_buf.decode())
            return db_buf
        except (OSError, TypeError) as err:
            logging.error(err.__str__())
            return err.__str__()

    def get_string(self, cmd, *misc):
        """Send a command and get the answer decoded"""

        try:
            answer = self.send_cmd(cmd, *misc).decode()
            if answer[:4] == b'FAIL':
                raise OSError(answer)
            return answer
        except (OSError, TypeError) as err:
            logging.error(err.__str__())
            return err.__str__()

    def find(self, title):
        """Find entries by title"""

        return self.get_string(b'FIND', title)

    def get_db(self):
        """Just get the whole encrypted database from server"""

        return self.get_bytes(b'GET')

    def change_password(self, password, keyfile):
        """Change the password of the remote database

        This is only allowed from localhost (127.0.0.1

        """

        return self.get_string(b'CHANGESECRET', password, keyfile)

    def create_group(self, title, root):
        """Create a group

        
        title is the group title, root is the id of the parent group

        """

        return self.get_bytes(b'NEWG', title, root)

    def create_entry(self, title, url, username, password, comment, y, mon, d,
                     group_id):
        """Create an entry

        Watch the kppy documentation for an explanation of the arguments

        """

        return self.get_bytes(b'NEWE', title, url, username, password, comment,
                              y, mon, d, group_id)

    def delete_group(self, group_id, last_mod):
        """Delete a group by the id

        last_mod is needed to check if the group was updated since the
        last refresh

        """

        return self.get_bytes(b'DELG', group_id, str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def delete_entry(self, uuid, last_mod):
        """Delete an entry by uuid"""

        return self.get_bytes(b'DELE', uuid, str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def move_group(self, group_id, root):
        """Move a group to a new parent

        If root is 0 the group with id group_id is moved to the root

        """

        return self.get_bytes(b'MOVG', group_id, root)

    def move_entry(self, uuid, root):
        """Move an entry with uuid to the group with id root"""

        return self.get_bytes(b'MOVE', uuid, root)

    def set_g_title(self, title, group_id, last_mod):
        """Set the title of a group"""

        return self.get_bytes(b'TITG', title, group_id,
                         str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def set_e_title(self, title, uuid, last_mod):
        """Set the title of an entry"""

        return self.get_bytes(b'TITE', title, uuid, str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def set_e_user(self, username, uuid, last_mod):
        """Set the username of an entry"""

        return self.get_bytes(b'USER', username, uuid,
                         str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def set_e_url(self, url, uuid, last_mod):
        """Set the URL of an entry"""

        return self.get_bytes(b'URL', url, uuid, str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def set_e_comment(self, comment, uuid, last_mod):
        """Set the comment of an entry"""

        return self.get_bytes(b'COMM', comment, uuid,
                         str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def set_e_pass(self, password, uuid, last_mod):
        """Set the password of an entry"""

        return self.get_bytes(b'PASS', password, uuid,
                         str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def set_e_exp(self, y, mon, d, uuid, last_mod):
        """Set the expiration date of an entry"""

        return self.get_bytes(b'DATE', y, mon, d, uuid,
                         str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

