import logging
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

    def __init__(self, pidfile, loglevel, logfile, 
                 server_address = 'localhost', server_port = 50000, 
                 agent_port = 50001, password = None, keyfile = None):
        Client.__init__(self, loglevel, logfile, server_address, server_port,
                        agent_port, password, keyfile)
        Daemon.__init__(self, pidfile)
        self.lookup = {
            b'FIND': self.find}

        # Agent is a daemon and cannot find the keyfile after run
        if self.keyfile is not None:
            with open(self.keyfile, "rb") as handler:
                self.keyfile = handler.read()
                handler.close()
        else:
            self.keyfile = b''

    def connect_server(self):
        """Overrides Client.connect_server"""

        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            conn.connect(self.server_address)
        except:
            raise
        else:
            logging.info('Connected to '+self.server_address[0]+':'+
                         str(self.server_address[1]))
        conn.settimeout(5)

        if self.password is None:
            password = b''
        else:
            password = self.password.encode() 

        self.sendmsg(conn, password)
        self.sendmsg(conn, self.keyfile)
        ret = self.receive(conn)
        if ret[:4] == b'FAIL':
            logging.error(ret.decode())
            return False
        else:
            return conn

    def run(self):
        """Overide Daemon.run() and provide sockets"""

        try:
            # Listen for commands
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(self.agent_address)
            sock.listen(1)
        except OSError as err:
            print(err)
            logging.error(err.__str__())
            self.stop()
        else:
            logging.info('Agent socket created on '+self.agent_address[0]+':'+
                         str(self.agent_address[1]))

        while True:
            conn, client = sock.accept()
            logging.info('Connected to '+client[0]+':'+str(client[1]))
            try:
                conn.settimeout(5)
                cmd = self.receive(conn)
                if cmd in self.lookup:
                    self.lookup[cmd](conn)
                else:
                    logging.error('Received a wrong command')
                    self.sendmsg(conn, b'Command isn\'t available')
            except OSError as err:
                logging.error(err.__str__())
            finally:
                conn.close()

    def find(self, conn):
        """Find Entries"""

        try:
            serv = self.connect_server()
            if serv is False:
                self.sendmsg(conn, b'FAIL: Wrong password')
                raise OSError
            if self.sendmsg(serv, b'FIND') is False:
                self.sendmsg(conn, b'FAIL: Server doesn\'t receive message')
                raise OSError
            answer = self.receive(serv)
            if answer[:4] == b'FAIL':
                self.sendmsg(conn, answer)
                raise OSError
            elif answer is False:
                self.sendmsg(conn, b'FAIL: Can\'t receive message from server')
                raise OSError
            else:
                self.sendmsg(conn, b'ACK')
            title = self.receive(conn)
            if self.sendmsg(serv, title) is False:
                self.sendmsg(conn, b'FAIL: Can\'t send message to server')
                raise OSError
            answer = self.receive(serv)
            if answer[:4] == b'FAIL':
                self.sendmsg(conn, answer)
                raise OSError
            elif answer is False:
                self.sendmsg(conn, b'FAIL: Can\'t receive message from server')
                raise OSError
            self.sendmsg(conn, answer)
        except (OSError, TypeError) as err:
            logging.error(err.__str__())
            return False
        finally:
            serv.close()

