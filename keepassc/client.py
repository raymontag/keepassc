import logging
import socket
import ssl
import struct

from Crypto.Hash import SHA256

from keepassc.conn import Connection

class Client(Connection):
    """The KeePassC client"""

    def __init__(self, loglevel, logfile, server_address = 'localhost',
                 server_port = 50000, agent_port = 50001, password = None,
                 keyfile = None, tls = False, tls_dir = None):
        Connection.__init__(self, loglevel, logfile, password, keyfile)
        self.server_address = (server_address, server_port)
        logging.error(self.server_address)
        self.agent_address = ('localhost', agent_port)

        if tls is True:
            self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            self.context.verify_mode = ssl.CERT_REQUIRED
            self.context.load_verify_locations(tls_dir)
        else:
            self.context = None
    
    def send_cmd(self, *cmd):
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

    def find(self, title):
        try:
            answer = self.send_cmd(b'FIND', title)
            if answer[:4] == b'FAIL':
                raise OSError(answer.decode())
            return answer.decode()
        except (OSError, TypeError) as err:
            logging.error(err.__str__())
            return err.__str__()

    def get_db(self):
        try:
            db_buf = self.send_cmd(b'GET')
            if db_buf[:4] == b'FAIL':
                raise OSError(db_buf.decode())
            return db_buf
        except (OSError, TypeError) as err:
            logging.error(err.__str__())
            return err.__str__()
        
    def create_group(self, title, root):
        try:
            db_buf = self.send_cmd(b'NEWG', title, root)
            if db_buf[:4] == b'FAIL':
                raise OSError(db_buf.decode())
            return db_buf
        except (OSError, TypeError) as err:
            logging.error(err.__str__())
            return err.__str__()
