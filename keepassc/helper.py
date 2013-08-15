# -*- coding: utf-8 -*-
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

import struct
from os import makedirs, remove
from os.path import isdir, isfile

from Crypto.Hash import SHA256
from Crypto.Cipher import AES

def parse_config(control):
    '''Parse the config file.

    It's important that a line in the file is written without spaces,
    that means

     - 'foo=bar' is a valid line
     - 'foo = bar' is not a valid one

    '''
    config = {'del_clip': True,  # standard config
              'clip_delay': 20,
              'lock_db': True,
              'lock_delay': 60,
              'rem_db': True,
              'rem_key': False,
              'skip_menu': False,
              'pin': True}

    if isfile(control.config_home):
        try:
            handler = open(control.config_home, 'r')
        except Exception as err:  # don't know if this is good style
            print(err.__str__())
        else:
            for line in handler:
                key, val = line.split('=')
                if val == 'True\n':
                    val = True
                elif val == 'False\n':
                    val = False
                else:
                    val = int(val)
                if key in config:
                    config[key] = val
            handler.close()
    else:  # write standard config
        write_config(control, config)
    return config


def write_config(control, config):
    '''Function to write the config file'''

    config_dir = control.config_home[:-7]
    if not isdir(config_dir):
        if isfile(config_dir):
            remove(config_dir)
        makedirs(config_dir)
    try:
        handler = open(control.config_home, 'w')
    except Exception as err:
        print(err.__str__())
        return False
    else:
        for key, val in config.items():
            handler.write(key + '=' + str(val) + '\n')
        handler.close()
    return True

def transform_key(masterkey, seed1, seed2, rounds):
    """This method creates the key to decrypt the database"""

    if masterkey is None or seed1 is None or seed2 is None or rounds is None:
        raise TypeError('None type not allowed')
    aes = AES.new(seed1, AES.MODE_ECB)

    # Encrypt the created hash
    for i in range(rounds):
        masterkey = aes.encrypt(masterkey)

    # Finally, hash it again...
    sha_obj = SHA256.new()
    sha_obj.update(masterkey)
    masterkey = sha_obj.digest()
    # ...and hash the result together with the randomseed
    sha_obj = SHA256.new()
    sha_obj.update(seed2 + masterkey)
    return sha_obj.digest()

def get_passwordkey(key):
    """This method hashes key"""

    if key is None:
        raise TypeError('None type not allowed')
    sha = SHA256.new()
    sha.update(key.encode('utf-8'))
    return sha.digest()

def get_filekey(keyfile):
    """This method creates a key from a keyfile."""

    try:
        handler = open(keyfile, 'rb')
        buf = handler.read()
    except:
        raise OSError('Could not open or read file.')
    else:
        handler.close()
    sha = SHA256.new()
    if len(buf) == 33:
        sha.update(buf)
        return sha.digest()
    elif len(buf) == 65:
        sha.update(struct.unpack('<65s', buf)[0].decode())
        return sha.digest()
    else:
        while buf:
            if len(buf) <= 2049:
                sha.update(buf)
                buf = []
            else:
                sha.update(buf[:2048])
                buf = buf[2048:]
        return sha.digest()

def get_remote_filekey(buf):
    """This method creates a key from a keyfile."""

    sha = SHA256.new()
    if len(buf) == 33:
        sha.update(buf)
        return sha.digest()
    elif len(buf) == 65:
        sha.update(struct.unpack('<65s', buf)[0].decode())
        return sha.digest()
    else:
        while buf:
            if len(buf) <= 2049:
                sha.update(buf)
                buf = []
            else:
                sha.update(buf[:2048])
                buf = buf[2048:]
        return sha.digest()

def get_key(password, keyfile, remote = False):
    """Get a key generated from KeePass-password and -keyfile"""

    if password is None and keyfile is None:
        raise TypeError('None type not allowed')
    elif password is None:
        if remote is True:
            masterkey = get_remote_filekey(keyfile)
        else:
            masterkey = get_filekey(keyfile)
    elif password is not None and keyfile is not None:
        passwordkey = get_passwordkey(password)
        if remote is True:
            filekey = get_remote_filekey(keyfile)
        else:
            filekey = get_filekey(keyfile)
        sha = SHA256.new()
        sha.update(passwordkey+filekey)
        masterkey = sha.digest()
    else:
        masterkey = get_passwordkey(password)

    return masterkey

