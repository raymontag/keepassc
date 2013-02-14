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

from os import makedirs, remove
from os.path import isdir, isfile


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
              'rem_key': False}

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
