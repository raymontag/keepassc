import logging
import signal
import socket
import ssl
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
                 agent_port = 50001, password = None, keyfile = None,
                 tls = False, tls_dir = None):
        Client.__init__(self, loglevel, logfile, server_address, server_port,
                        agent_port, password, keyfile)
        Daemon.__init__(self, pidfile)
        self.lookup = {
            b'FIND': self.find}
        self.sock = None

        # Agent is a daemon and cannot find the keyfile after run
        if self.keyfile is not None:
            with open(self.keyfile, "rb") as handler:
                self.keyfile = handler.read()
                handler.close()
        else:
            self.keyfile = b''

        if tls is True:
            self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            self.context.verify_mode = ssl.CERT_REQUIRED
            self.context.load_verify_locations(tls_dir)
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
        cmd_chain = self.build_message(tmp)

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
                cert = conn.getpeercert()
                try:
                    ssl.match_hostname(cert, "KeePassC Server")
                except:
                    return b'FAIL: TLS - Hostname does not match'
            self.sendmsg(conn, cmd_chain)
            answer = self.receive(conn)
        except:
            raise
        finally:
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()

        return answer

    def run(self):
        """Overide Daemon.run() and provide sockets"""

        try:
            # Listen for commands
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.bind(self.agent_address)
            self.sock.listen(1)
        except OSError as err:
            print(err)
            logging.error(err.__str__())
            self.stop()
        else:
            logging.info('Agent socket created on '+self.agent_address[0]+':'+
                         str(self.agent_address[1]))

        while True:
            conn, client = self.sock.accept()
            logging.info('Connected to '+client[0]+':'+str(client[1]))
            conn.settimeout(60)
            try:
                parts = self.receive(conn).split(b'\xB2\xEA\xC0')
                cmd = parts.pop(0)
                if cmd in self.lookup:
                    self.lookup[cmd](conn, parts)
                else:
                    logging.error('Received a wrong command')
                    self.sendmsg(conn, b'FAIL: Command isn\'t available')
            except OSError as err:
                logging.error(err.__str__())
            finally:
                conn.shutdown(socket.SHUT_RDWR)
                conn.close()

    def find(self, conn, cmd_misc):
        """Find Entries"""

        try:
            answer = self.send_cmd(b'FIND', cmd_misc[0])
            self.sendmsg(conn, answer)
            if answer[:4] == b'FAIL':
                raise OSError(answer.decode())
        except (OSError, TypeError) as err:
            logging.error(err.__str__())

    def handle_sigterm(self, signum, frame):
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
        del self.keyfile

