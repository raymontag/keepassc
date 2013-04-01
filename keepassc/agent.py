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

        try:
            if self.init_connection(self.server_address) is False:
                raise OSError('Decryption of encryption information failed.'
                              ' Wrong password?')
        except OSError as err:
            print(err)
            logging.error(err.__str__())
            sys.exit(1)

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
                    conn.sendall(b'Command isn\'t available')
            except OSError as err:
                logging.error(err.__str__())
                continue # log error
            finally:
                conn.close()

    def find(self, conn):
        """Find Entries"""

        try:
            serv = self.connect_server()
            if self.sendmsg(serv, b'FIND') is False:
                conn.sendall(b'FAIL: Server doesn\'t receive message')
                raise OSError
            answer = self.receive(serv)
            if answer[:4] == b'FAIL':
                conn.sendall(answer)
                raise OSError
            elif answer is False:
                conn.sendall(b'FAIL: Can\'t receive message from server')
                raise OSError
            else:
                conn.sendall(b'ACKEND')
            title = self.receive(conn)
            if title is False:
                raise OSError
            if self.sendmsg(serv, title) is False:
                conn.sendall(b'FAIL: Can\'t send message to server')
                raise OSError
            answer = self.receive(serv)
            if answer[:4] == b'FAIL':
                conn.sendall(answer)
                raise OSError
            elif answer is False:
                conn.sendall(b'FAIL: Can\'t receive message from server')
                raise OSError
            data = self.decrypt_msg(answer)
            if data is False:
                msg = 'Decryption failed. Wrong password?'
                logging.error(msg)
                conn.sendall(b'FAIL: '+msg.encode()+'END')
            else:
                conn.sendall(data+b'END')
        except (OSError, TypeError) as err:
            logging.error(err.__str__())
            return False
        finally:
            serv.close()
