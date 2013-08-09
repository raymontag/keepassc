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

    def get_bytes(self, cmd, *misc):
        try:
            db_buf = self.send_cmd(cmd, *misc)
            if db_buf[:4] == b'FAIL':
                raise OSError(db_buf.decode())
            return db_buf
        except (OSError, TypeError) as err:
            logging.error(err.__str__())
            return err.__str__()

    def get_string(self, cmd, *misc):
        try:
            answer = self.send_cmd(cmd, *misc).decode()
            if answer[:4] == b'FAIL':
                raise OSError(answer)
            return answer
        except (OSError, TypeError) as err:
            logging.error(err.__str__())
            return err.__str__()

    def find(self, title):
        return self.get_string(b'FIND', title)

    def get_db(self):
        return self.get_bytes(b'GET')
        
    def change_password(self, password, keyfile):
        return self.get_string(b'CHANGESECRET', password, keyfile)

    def create_group(self, title, root):
        return self.get_bytes(b'NEWG', title, root)

    def create_entry(self, title, url, username, password, comment, y, mon, d,
                     group_id):
        return self.get_bytes(b'NEWE', title, url, username, password, comment,
                              y, mon, d, group_id)

    def delete_group(self, group_id, last_mod):
        return self.get_bytes(b'DELG', group_id, str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())
        
    def delete_entry(self, uuid, last_mod):
        return self.get_bytes(b'DELE', uuid, str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def move_group(self, group_id, root):
        return self.get_bytes(b'MOVG', group_id, root)

    def move_entry(self, uuid, root):
        return self.get_bytes(b'MOVE', uuid, root)

    def set_g_title(self, title, group_id, last_mod):
        return self.get_bytes(b'TITG', title, group_id, 
                         str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def set_e_title(self, title, uuid, last_mod):
        return self.get_bytes(b'TITE', title, uuid, str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def set_e_user(self, username, uuid, last_mod):
        return self.get_bytes(b'USER', username, uuid, 
                         str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def set_e_url(self, url, uuid, last_mod):
        return self.get_bytes(b'URL', url, uuid, str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def set_e_comment(self, comment, uuid, last_mod):
        return self.get_bytes(b'COMM', comment, uuid, 
                         str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def set_e_pass(self, password, uuid, last_mod):
        return self.get_bytes(b'PASS', password, uuid, 
                         str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())

    def set_e_exp(self, y, mon, d, uuid, last_mod):
        return self.get_bytes(b'DATE', y, mon, d, uuid, 
                         str(last_mod[0]).encode(),
                         str(last_mod[1]).encode(), str(last_mod[2]).encode(),
                         str(last_mod[3]).encode(), str(last_mod[4]).encode(),
                         str(last_mod[5]).encode())
    
