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

import curses as cur
import logging
from curses.ascii import NL, DEL, SP
from datetime import date
from os import chdir, getcwd, getenv, geteuid, makedirs, remove
from os.path import expanduser, isfile, isdir, realpath, join
from pwd import getpwuid
from random import sample
from socket import gethostname, socket, AF_INET, SOCK_STREAM, SHUT_RDWR
from sys import exit

from kppy.database import KPDBv1
from kppy.exceptions import KPError

from keepassc.conn import *
from keepassc.client import Client
from keepassc.editor import Editor
from keepassc.helper import parse_config, write_config
from keepassc.filebrowser import FileBrowser
from keepassc.dbbrowser import DBBrowser


class Control(object):
    '''This class represents the whole application.'''
    def __init__(self):
        '''The __init__-method.

        It just initializes some variables and settings and changes
        the working directory to /var/empty to prevent coredumps as
        normal user.

        '''

        try:
            self.config_home = realpath(expanduser(getenv('XDG_CONFIG_HOME')))
        except:
            self.config_home = realpath(expanduser('~/.config'))
        finally:
            self.config_home = join(self.config_home, 'keepassc', 'config')

        try:
            self.data_home = realpath(expanduser(getenv('XDG_DATA_HOME')))
        except:
            self.data_home = realpath(expanduser('~/.local/share/'))
        finally:
            self.data_home = join(self.data_home, 'keepassc')
        self.last_home = join(self.data_home, 'last')
        self.remote_home = join(self.data_home, 'remote')
        self.key_home = join(self.data_home, 'key')

        self.config = parse_config(self)

        if self.config['rem_key'] is False and isfile(self.key_home):
            remove(self.key_home)

        self.initialize_cur()
        self.last_file = None
        self.last_key = None
        self.loginname = getpwuid(geteuid())[0]
        self.hostname = gethostname()
        self.cur_dir = getcwd()
        chdir('/var/empty')
        self.db = None

    def initialize_cur(self):
        '''Method to initialize curses functionality'''

        self.stdscr = cur.initscr()
        try:
            cur.curs_set(0)
        except:
            print('Invisible cursor not supported')
        cur.cbreak()
        cur.noecho()
        self.stdscr.keypad(1)
        cur.start_color()
        cur.use_default_colors()
        cur.init_pair(1, -1, -1)
        cur.init_pair(2, 2, -1)
        cur.init_pair(3, -1, 1)
        cur.init_pair(4, 6, -1)
        cur.init_pair(5, 0, 6)
        cur.init_pair(6, 0, 7)
        cur.init_pair(7, 1, -1)
        self.stdscr.bkgd(1)
        self.ysize, self.xsize = self.stdscr.getmaxyx()

        self.group_win = cur.newwin(self.ysize - 1, int(self.xsize / 3),
                                    1, 0)
        # 11 is the y size of info_win
        self.entry_win = cur.newwin((self.ysize - 1) - 11,
                                    int(2 * self.xsize / 3),
                                    1, int(self.xsize / 3))
        self.info_win = cur.newwin(11,
                                   int(2 * self.xsize / 3),
                                   (self.ysize - 1) - 11,
                                   int(self.xsize / 3))
        self.group_win.keypad(1)
        self.entry_win.keypad(1)
        self.group_win.bkgd(1)
        self.entry_win.bkgd(1)
        self.info_win.bkgd(1)

    def resize_all(self):
        '''Method to resize windows'''

        self.ysize, self.xsize = self.stdscr.getmaxyx()
        self.group_win.resize(self.ysize - 1, int(self.xsize / 3))
        self.entry_win.resize(
            self.ysize - 1 - 11, int(2 * self.xsize / 3))
        self.info_win.resize(11, int(2 * self.xsize / 3))
        self.group_win.mvwin(1, 0)
        self.entry_win.mvwin(1, int(self.xsize / 3))
        self.info_win.mvwin((self.ysize - 1) - 11, int(self.xsize / 3))

    def any_key(self):
        '''If any key is needed.'''

        while True:
            try:
                e = self.stdscr.getch()
            except KeyboardInterrupt:
                e = 4
            if e == 4:
                return -1
            elif e == cur.KEY_RESIZE:
                self.resize_all()
            else:
                return e

    def draw_text(self, changed, *misc):
        '''This method is a wrapper to display some text on stdscr.

        misc is a list that should consist of 3-tuples which holds
        text to display.
        (1st element: y-coordinate, 2nd: x-coordinate, 3rd: text)

        '''

        if changed is True:
            cur_dir = self.cur_dir + '*'
        else:
            cur_dir = self.cur_dir
        try:
            self.stdscr.clear()
            self.stdscr.addstr(
                0, 0, self.loginname + '@' + self.hostname + ':',
                cur.color_pair(2))
            self.stdscr.addstr(
                0, len(self.loginname + '@' + self.hostname + ':'),
                cur_dir)
            for i, j, k in misc:
                self.stdscr.addstr(i, j, k)
        except:  # to prevent a crash if screen is small
            pass
        finally:
            self.stdscr.refresh()

    def draw_help(self, *text):
        """Draw a help

        *text are arbitary string

        """

        if len(text) > self.ysize -1:
            length = self.ysize - 1
            offset = 0
            spill = len(text) - self.ysize + 2
        else:
            length = len(text)
            offset = 0
            spill = 0

        while True:
            try:
                self.draw_text(False)
                for i in range(length):
                    self.stdscr.addstr(
                    i + 1, 0, text[(i + offset)])
            except:
                pass
            finally:
                self.stdscr.refresh()
            try:
                e = self.stdscr.getch()
            except KeyboardInterrupt:
                e = 4

            if e == cur.KEY_DOWN:
                if offset < spill:
                    offset += 1
            elif e == cur.KEY_UP:
                if offset > 0:
                    offset -= 1
            elif e == NL:
                return
            elif e == cur.KEY_RESIZE:
                self.resize_all()
                if len(text) > self.ysize -1:
                    length = self.ysize - 1
                    offset = 0
                    spill = len(text) - self.ysize + 2
                else:
                    length = len(text)
                    offset = 0
                    spill = 0
            elif e == 4:
                if self.db is not None:
                    self.db.close()
                self.close()

    def get_password(self, std, needed=True):
        '''This method is used to get a password.

        The pasword will not be displayed during typing.

        std is a string that should be displayed. If needed is True it
        is not possible to return an emptry string.

        '''
        password = Editor(self.stdscr, max_text_size=1, win_location=(0, 1),
                          win_size=(1, self.xsize), title=std, pw_mode=True)()
        if needed is True and not password:
            return False
        else:
            return password

    def get_authentication(self):
        """Get authentication credentials"""

        while True:
            if (self.config['skip_menu'] is False or
                (self.config['rem_db'] is False and
                 self.config['rem_key'] is False)):
                auth = self.gen_menu(1, (
                                     (1, 0, 'Use a password (1)'),
                                     (2, 0, 'Use a keyfile (2)'),
                                     (3, 0, 'Use both (3)')),
                                    (5, 0, 'Press \'F5\' to go back to main '
                                           'menu'))
            else:
                self.draw_text(False)
                auth = 3
            if auth is False:
                return False
            elif auth == -1:
                self.close()
            if auth == 1 or auth == 3:
                if self.config['skip_menu'] is True:
                    needed = False
                else:
                    needed = True
                password = self.get_password('Password: ', needed = needed)
                if password is False:
                    self.config['skip_menu'] = False
                    continue
                elif password == -1:
                    self.close()
                # happens only if self.config['skip_menu'] is True
                elif password == "":
                    password = None
                if auth != 3:
                    keyfile = None
            if auth == 2 or auth == 3:
                # Ugly construct but works
                # "if keyfile is False" stuff is needed to implement the
                # return to previous screen stuff
                # Use similar constructs elsewhere
                while True:
                    self.get_last_key()
                    if (self.last_key is None or
                            self.config['rem_key'] is False):
                        ask_for_lf = False
                    else:
                        ask_for_lf = True

                    keyfile = FileBrowser(self, ask_for_lf, True, 
                                          self.last_key)()
                    if keyfile is False:
                        break
                    elif keyfile == -1:
                        self.close()
                    elif not isfile(keyfile):
                        self.draw_text(False,
                                       (1, 0, 'That\'s not a file'),
                                       (3, 0, 'Press any key.'))
                        if self.any_key() == -1:
                            self.close()
                        continue
                    break
                if keyfile is False:
                    continue
                if auth != 3:
                    password = None
                if self.config['rem_key'] is True:
                    if not isdir(self.key_home[:-4]):
                        if isfile(self.key_home[:-4]):
                            remove(self.key_home[:-4])
                        makedirs(self.key_home[:-4])
                    handler = open(self.key_home, 'w')
                    handler.write(keyfile)
                    handler.close()
            break
        return (password, keyfile)

    def get_last_db(self):
        if isfile(self.last_home) and self.config['rem_db'] is False:
            remove(self.last_home)
            self.last_file = None
        elif isfile(self.last_home):
            try:
                handler = open(self.last_home, 'r')
            except Exception as err:
                self.last_file = None
                print(err.__str__())
            else:
                self.last_file = handler.readline()
                handler.close()
        else:
            self.last_file = None

    def get_last_key(self):
        if isfile(self.key_home) and self.config['rem_key'] is False:
            remove(self.key_home)
            self.last_key = None
        elif isfile(self.key_home):
            try:
                handler = open(self.key_home, 'r')
            except Exception as err:
                self.last_key = None
                print(err.__str__())
            else:
                self.last_key = handler.readline()
                handler.close()
        else:
            self.last_key = None

    def gen_pass(self):
        '''Method to generate a password'''

        while True:
            items = self.gen_check_menu(((1, 0, 'Include numbers'),
                                         (2, 0,
                                          'Include capitalized letters'),
                                         (3, 0, 'Include special symbols')),
                                        (5, 0, 'Press space to un-/check'),
                                        (6, 0,
                                         'Press return to enter options'))
            if items is False or items == -1:
                return items
            length = self.get_num('Password length: ')
            if length is False:
                continue
            elif length == -1:
                return -1
            char_set = 'abcdefghijklmnopqrstuvwxyz'
            if items[0] == 1:
                char_set += '1234567890'
            if items[1] == 1:
                char_set += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            if items[2] == 1:
                char_set += '!"#$%& \'()*+,-./:;<=>?@[\\]^_`{|}~$§'

            password = ''
            for _ in range(length):
                password += sample(char_set, 1)[0]
            return password

    def get_exp_date(self, *exp):
        '''This method is used to get an expiration date for entries.

        exp is used to display an actual expiration date.

        '''

        pass_y = False
        pass_mon = False
        goto_last = False
        while True:
            if pass_y is False:
                edit = ''
                e = cur.KEY_BACKSPACE
                while e != NL:
                    if (e == cur.KEY_BACKSPACE or e == DEL) and len(edit) != 0:
                        edit = edit[:-1]
                    elif e == cur.KEY_BACKSPACE or e == DEL:
                        pass
                    elif e == 4:
                        return -1
                    elif e == cur.KEY_RESIZE:
                        self.resize_all()
                    elif e == cur.KEY_F5:
                        return False
                    elif len(edit) < 4 and e >= 48 and e <= 57:
                        edit += chr(e)
                    self.draw_text(False,
                                   (1, 0, 'Special date 2999-12-28 means that '
                                    'the expires never.'),
                                   (3, 0, 'Year: ' + edit))
                    if exp:
                        try:
                            self.stdscr.addstr(2, 0,
                                               'Actual expiration date: ' +
                                               str(exp[0]) + '-' +
                                               str(exp[1]) + '-' +
                                               str(exp[2]))
                        except:
                            pass
                        finally:
                            self.stdscr.refresh()
                    try:
                        e = self.stdscr.getch()
                    except KeyboardInterrupt:
                        e = 4
                    if e == NL and edit == '':
                        e = cur.KEY_BACKSPACE
                        continue
                y = int(edit)
                pass_y = True

            if pass_mon is False:
                edit = ''
                e = cur.KEY_BACKSPACE
                while e != NL:
                    if (e == cur.KEY_BACKSPACE or e == DEL) and len(edit) != 0:
                        edit = edit[:-1]
                    elif e == cur.KEY_BACKSPACE or e == DEL:
                        pass
                    elif e == 4:
                        return -1
                    elif e == cur.KEY_RESIZE:
                        self.resize_all()
                    elif e == cur.KEY_F5:
                        pass_y = False
                        goto_last = True
                        break
                    elif len(edit) < 2 and e >= 48 and e <= 57:
                        edit += chr(e)
                    self.draw_text(False,
                                   (1, 0, 'Special date 2999-12-28 means that '
                                    'the expires never.'),
                                   (3, 0, 'Year: ' + str(y)),
                                   (4, 0, 'Month: ' + edit))
                    if exp:
                        try:
                            self.stdscr.addstr(2, 0,
                                               'Actual expiration date: ' +
                                               str(exp[0]) + '-' +
                                               str(exp[1]) + '-' +
                                               str(exp[2]))
                        except:
                            pass
                        finally:
                            self.stdscr.refresh()
                    try:
                        e = self.stdscr.getch()
                    except KeyboardInterrupt:
                        e = 4

                    if e == NL and edit == '':
                        e = cur.KEY_BACKSPACE
                        continue
                    elif e == NL and (int(edit) > 12 or int(edit) < 1):
                        self.draw_text(False,
                                       (1, 0,
                                        'Month must be between 1 and 12. '
                                        'Press any key.'))
                        if self.any_key() == -1:
                            return -1
                        e = ''
                if goto_last is True:
                    goto_last = False
                    continue
                mon = int(edit)
                pass_mon = True

            edit = ''
            e = cur.KEY_BACKSPACE
            while e != NL:
                if (e == cur.KEY_BACKSPACE or e == DEL) and len(edit) != 0:
                    edit = edit[:-1]
                elif e == cur.KEY_BACKSPACE or e == DEL:
                    pass
                elif e == 4:
                    return -1
                elif e == cur.KEY_RESIZE:
                    self.resize_all()
                elif e == cur.KEY_F5:
                    pass_mon = False
                    goto_last = True
                    break
                elif len(edit) < 2 and e >= 48 and e <= 57:
                    edit += chr(e)
                self.draw_text(False,
                               (1, 0, 'Special date 2999-12-28 means that the '
                                'expires never.'),
                               (3, 0, 'Year: ' + str(y)),
                               (4, 0, 'Month: ' + str(mon)),
                               (5, 0, 'Day: ' + edit))
                if exp:
                    try:
                        self.stdscr.addstr(2, 0, 'Actual expiration date: ' +
                                           str(exp[0]) + '-' +
                                           str(exp[1]) + '-' +
                                           str(exp[2]))
                    except:
                        pass
                    finally:
                        self.stdscr.refresh()
                try:
                    e = self.stdscr.getch()
                except KeyboardInterrupt:
                    e = 4

                if e == NL and edit == '':
                    e = cur.KEY_BACKSPACE
                    continue
                elif (e == NL and (mon == 1 or mon == 3 or mon == 5 or
                                   mon == 7 or mon == 8 or mon == 10 or
                                   mon == 12) and
                      (int(edit) > 31 or int(edit) < 0)):
                    self.draw_text(False,
                                   (1, 0,
                                    'Day must be between 1 and 31. Press '
                                    'any key.'))
                    if self.any_key() == -1:
                        return -1
                    e = ''
                elif (e == NL and mon == 2 and (int(edit) > 28 or
                                                int(edit) < 0)):
                    self.draw_text(False,
                                   (1, 0,
                                    'Day must be between 1 and 28. Press '
                                    'any key.'))
                    if self.any_key() == -1:
                        return -1
                    e = ''
                elif (e == NL and (mon == 4 or mon == 6 or mon == 9 or
                      mon == 11) and (int(edit) > 30 or int(edit) < 0)):
                    self.draw_text(False,
                                   (1, 0,
                                    'Day must be between 1 and 30. Press '
                                    'any key.'))
                    if self.any_key() == -1:
                        return -1
                    e = ''
            if goto_last is True:
                goto_last = False
                pass_mon = False
                continue
            d = int(edit)
            break
        return (y, mon, d)

    def get_num(self, std='', edit='', length=4):
        '''Method to get a number'''

        edit = edit
        e = 60 # just an unrecognized letter
        while e != NL:
            if (e == cur.KEY_BACKSPACE or e == DEL) and len(edit) != 0:
                edit = edit[:-1]
            elif e == cur.KEY_BACKSPACE or e == DEL:
                pass
            elif e == 4:
                return -1
            elif e == cur.KEY_RESIZE:
                self.resize_all()
            elif e == cur.KEY_F5:
                return False
            elif len(edit) < length and e >= 48 and e <= 57:
                edit += chr(e)
            self.draw_text(False,
                           (1, 0, std + edit))
            try:
                e = self.stdscr.getch()
            except KeyboardInterrupt:
                e = 4
            if e == NL and edit == '':
                e = cur.KEY_BACKSPACE
                continue
        return int(edit)

    def gen_menu(self, highlight, misc, *add):
        '''A universal method to generate a menu.

        misc is a tupel of triples (y, x, 'text')

        add are more tuples but the content should not be accessable

        '''

        if len(misc) == 0:
            return False
        h_color = 6
        n_color = 1
        e = ''
        while e != NL:
            try:
                self.stdscr.clear()
                self.stdscr.addstr(
                    0, 0, self.loginname + '@' + self.hostname + ':',
                    cur.color_pair(2))
                self.stdscr.addstr(0,
                                   len(self.loginname +
                                       '@' + self.hostname + ':'),
                                   self.cur_dir)
                for i, j, k in misc:
                    if i == highlight:
                        self.stdscr.addstr(i, j, k, cur.color_pair(h_color))
                    else:
                        self.stdscr.addstr(i, j, k, cur.color_pair(n_color))
                for i, j, k in add:
                    self.stdscr.addstr(i, j, k)
            except:
                pass
            finally:
                self.stdscr.refresh()
            try:
                e = self.stdscr.getch()
            except KeyboardInterrupt:
                e = 4
            if e == 4:
                return -1
            elif e == cur.KEY_RESIZE:
                self.resize_all()
            elif e == cur.KEY_F5:
                return False
            elif e == NL:
                return highlight
            elif (e == cur.KEY_DOWN or e == ord('j')) and highlight < len(misc):
                highlight += 1
            elif (e == cur.KEY_UP or e == ord('k')) and highlight > 1:
                highlight -= 1
            elif 49 <= e <= 48 + len(misc):  # ASCII(49) = 1 ...
                return e - 48

    def gen_check_menu(self, misc, *add):
        '''Print a menu with checkable entries'''

        if len(misc) == 0:
            return False
        items = []
        for i in range(len(misc)):
            items.append(0)
        highlight = 1
        h_color = 6
        n_color = 1
        e = ''
        while e != NL:
            try:
                self.stdscr.clear()
                self.stdscr.addstr(
                    0, 0, self.loginname + '@' + self.hostname + ':',
                    cur.color_pair(2))
                self.stdscr.addstr(0,
                                   len(self.loginname +
                                       '@' + self.hostname + ':'),
                                   self.cur_dir)
                for i, j, k in misc:
                    if items[i - 1] == 0:
                        check = '[ ]'
                    else:
                        check = '[X]'
                    if i == highlight:
                        self.stdscr.addstr(
                            i, j, check + k, cur.color_pair(h_color))
                    else:
                        self.stdscr.addstr(
                            i, j, check + k, cur.color_pair(n_color))
                for i, j, k in add:
                    self.stdscr.addstr(i, j, k)
            except:
                pass
            finally:
                self.stdscr.refresh()
            try:
                e = self.stdscr.getch()
            except KeyboardInterrupt:
                e = 4
            if e == 4:
                return -1
            elif e == cur.KEY_RESIZE:
                self.resize_all()
            elif e == cur.KEY_F5:
                return False
            elif e == SP:
                if items[highlight - 1] == 0:
                    items[highlight - 1] = 1
                else:
                    items[highlight - 1] = 0
            elif (e == cur.KEY_DOWN or e == ord('j')) and highlight < len(misc):
                highlight += 1
            elif (e == cur.KEY_UP or e == ord('k')) and highlight > 1:
                highlight -= 1
            elif e == NL:
                return items

    def gen_config_menu(self):
        '''The configuration menu'''

        self.config = parse_config(self)
        menu = 1
        while True:
            menu = self.gen_menu(menu,
                ((1, 0, 'Delete clipboard automatically: ' +
                  str(self.config['del_clip'])),
                 (2, 0, 'Waiting time (seconds): ' +
                  str(self.config['clip_delay'])),
                 (3, 0, 'Lock database automatically: ' +
                  str(self.config['lock_db'])),
                 (4, 0, 'Waiting time (seconds): ' +
                  str(self.config['lock_delay'])),
                 (5, 0, 'Remember last database: ' +
                  str(self.config['rem_db'])),
                 (6, 0, 'Remember last keyfile: ' +
                  str(self.config['rem_key'])),
                 (7, 0, 'Use directly password and key if one of the two '
                        'above is True: ' +
                  str(self.config['skip_menu'])),
                 (8, 0, 'Pin server certificate: ' + str(self.config['pin'])),
                 (9, 0, 'Generate default configuration'),
                 (10, 0, 'Write config')),
                (12, 0, 'Automatic locking works only for saved databases!'))
            if menu == 1:
                if self.config['del_clip'] is True:
                    self.config['del_clip'] = False
                elif self.config['del_clip'] is False:
                    self.config['del_clip'] = True
            elif menu == 2:
                delay = self.get_num('Waiting time: ',
                                     str(self.config['clip_delay']))
                if delay is False:
                    continue
                elif delay == -1:
                    self.close()
                else:
                    self.config['clip_delay'] = delay
            elif menu == 3:
                if self.config['lock_db'] is True:
                    self.config['lock_db'] = False
                elif self.config['lock_db'] is False:
                    self.config['lock_db'] = True
            elif menu == 4:
                delay = self.get_num('Waiting time: ',
                                     str(self.config['lock_delay']))
                if delay is False:
                    continue
                elif delay == -1:
                    self.close()
                else:
                    self.config['lock_delay'] = delay
            elif menu == 5:
                if self.config['rem_db'] is True:
                    self.config['rem_db'] = False
                elif self.config['rem_db'] is False:
                    self.config['rem_db'] = True
            elif menu == 6:
                if self.config['rem_key'] is True:
                    self.config['rem_key'] = False
                elif self.config['rem_key'] is False:
                    self.config['rem_key'] = True
            elif menu == 7:
                if self.config['skip_menu'] is True:
                    self.config['skip_menu'] = False
                elif self.config['skip_menu'] is False:
                    self.config['skip_menu'] = True
            elif menu == 8:
                if self.config['pin'] is True:
                    self.config['pin'] = False
                elif self.config['pin'] is False:
                    self.config['pin'] = True
            elif menu == 9:
                self.config = {'del_clip': True,  # standard config
                               'clip_delay': 20,
                               'lock_db': True,
                               'lock_delay': 60,
                               'rem_db': True,
                               'rem_key': False,
                               'skip_menu': False,
                               'pin': True}
            elif menu == 10:
                write_config(self, self.config)
                return True
            elif menu is False:
                return False
            elif menu == -1:
                self.close()

    def draw_lock_menu(self, changed, highlight, *misc):
        '''Draw menu for locked database'''

        h_color = 6
        n_color = 1
        if changed is True:
            cur_dir = self.cur_dir + '*'
        else:
            cur_dir = self.cur_dir
        try:
            self.stdscr.clear()
            self.stdscr.addstr(
                0, 0, self.loginname + '@' + self.hostname + ':',
                cur.color_pair(2))
            self.stdscr.addstr(
                0, len(self.loginname + '@' + self.hostname + ':'),
                cur_dir)
            for i, j, k in misc:
                if i == highlight:
                    self.stdscr.addstr(i, j, k, cur.color_pair(h_color))
                else:
                    self.stdscr.addstr(i, j, k, cur.color_pair(n_color))
        #except: # to prevent a crash if screen is small
        #    pass
        finally:
            self.stdscr.refresh()

    def main_loop(self, kdb_file=None, remote = False):
        '''The main loop. The program alway return to this method.'''

        if remote is True:
            self.remote_interface()
        else:
            # This is needed to remember last database and open it directly
            self.get_last_db()

            if kdb_file is not None:
                self.cur_dir = kdb_file
                if self.open_db(True) is True:
                    db = DBBrowser(self)
                    del db
                    last = self.cur_dir.split('/')[-1]
                    self.cur_dir = self.cur_dir[:-len(last) - 1]
            elif self.last_file is not None and self.config['rem_db'] is True:
                self.cur_dir = self.last_file
                if self.open_db(True) is True:
                    db = DBBrowser(self)
                    del db
                    last = self.cur_dir.split('/')[-1]
                    self.cur_dir = self.cur_dir[:-len(last) - 1]

        while True:
            self.get_last_db()
            menu = self.gen_menu(1, ((1, 0, 'Open existing database (1)'),
                                  (2, 0, 'Create new database (2)'),
                                  (3, 0, 'Connect to a remote database(3)'),
                                  (4, 0, 'Configuration (4)'),
                                  (5, 0, 'Quit (5)')),
                                 (7, 0, 'Type \'F1\' for help inside the file '
                                        'or database browser.'),
                                 (8, 0, 'Type \'F5\' to return to the previous'
                                        ' dialog at any time.'))
            if menu == 1:
                if self.open_db() is False:
                    continue
                db = DBBrowser(self)
                del db
                last = self.cur_dir.split('/')[-1]
                self.cur_dir = self.cur_dir[:-len(last) - 1]
            elif menu == 2:
                while True:
                    auth = self.gen_menu(1, (
                                         (1, 0, 'Use a password (1)'),
                                         (2, 0, 'Use a keyfile (2)'),
                                         (3, 0, 'Use both (3)')))
                    password = None
                    confirm = None
                    filepath = None
                    self.db = KPDBv1(new=True)
                    if auth is False:
                        break
                    elif auth == -1:
                        self.db = None
                        self.close()
                    if auth == 1 or auth == 3:
                        while True:
                            password = self.get_password('Password: ')
                            if password is False:
                                break
                            elif password == -1:
                                self.db = None
                                self.close()
                            confirm = self.get_password('Confirm: ')
                            if confirm is False:
                                break
                            elif confirm == -1:
                                self.db = None
                                self.close()
                            if password == confirm:
                                self.db.password = password
                                break
                            else:
                                self.draw_text(False,
                                               (1, 0,
                                                'Passwords didn\' match!'),
                                               (3, 0, 'Press any key'))
                                if self.any_key() == -1:
                                    self.db = None
                                    self.close()
                        if auth != 3:
                            self.db.keyfile = None
                    if password is False or confirm is False:
                        continue
                    if auth == 2 or auth == 3:
                        while True:
                            filepath = FileBrowser(self, False, True, None)()
                            if filepath is False:
                                break
                            elif filepath == -1:
                                self.close()
                            elif not isfile(filepath):
                                self.draw_text(False,
                                               (1, 0, 'That\' not a file!'),
                                               (3, 0, 'Press any key'))
                                if self.any_key() == -1:
                                    self.db = None
                                    self.close()
                                continue
                            break
                        if filepath is False:
                            continue
                        self.db.keyfile = filepath
                        if auth != 3:
                            self.db.password = None

                    if auth is not False:
                        db = DBBrowser(self)
                        del db
                        last = self.cur_dir.split('/')[-1]
                        self.cur_dir = self.cur_dir[:-len(last) - 1]
                    else:
                        self.db = None
                    break
            elif menu == 3:
                self.remote_interface()
            elif menu == 4:
                self.gen_config_menu()
            elif menu == 5 or menu is False or menu == -1:
                self.close()

    def open_db(self, skip_fb=False):
        ''' This method opens a database.'''

        if skip_fb is False:
            filepath = FileBrowser(self, True, False, self.last_file)()
            if filepath is False:
                return False
            elif filepath == -1:
                self.close()
            else:
                self.cur_dir = filepath

        ret = self.get_authentication()
        if ret is False:
            return False
        password, keyfile = ret

        try:
            if isfile(self.cur_dir + '.lock'):
                self.draw_text(False,
                               (1, 0, 'Database seems to be opened.'
                                ' Open file in read-only mode?'
                                ' [(y)/n]'))
                while True:
                    try:
                        e = self.stdscr.getch()
                    except KeyboardInterrupt:
                        e = 4

                    if e == ord('n'):
                        read_only = False
                        break
                    elif e == 4:
                        self.close()
                    elif e == cur.KEY_RESIZE:
                        self.resize_all()
                    elif e == cur.KEY_F5:
                        return False
                    else:
                        read_only = True
                        break
            else:
                read_only = False
            self.db = KPDBv1(self.cur_dir, password, keyfile, read_only)
            self.db.load()
            return True
        except KPError as err:
            self.draw_text(False,
                           (1, 0, err.__str__()),
                           (4, 0, 'Press any key.'))
            if self.any_key() == -1:
                self.close()
            last = self.cur_dir.split('/')[-1]
            self.cur_dir = self.cur_dir[:-len(last) - 1]
            return False

    def remote_interface(self, ask_for_agent = True, agent = False):
        if ask_for_agent is True and agent is False:
            use_agent = self.gen_menu(1, ((1, 0, 'Use agent (1)'),
                                          (2, 0, 'Use no agent (2)')))
        elif agent is True:
            use_agent = 1
        else:
            use_agent = 2

        if use_agent == 1:
            port = self.get_num("Agent port: ", "50001", 5)
            if port is False:
                return False
            elif port == -1:
                self.close()

            sock = socket(AF_INET, SOCK_STREAM)
            sock.settimeout(60)
            try:
                sock.connect(('localhost', port))
                sendmsg(sock, build_message((b'GET',)))
            except OSError as err:
                self.draw_text(False, (1, 0, err.__str__()),
                                      (3, 0, "Press any key."))
                if self.any_key() == -1:
                    self.close()
                return False

            db_buf = receive(sock)
            if db_buf[:4] == b'FAIL' or db_buf[:4] == b'[Err':
                self.draw_text(False,
                               (1, 0, db_buf),
                               (3, 0, 'Press any key.'))
                if self.any_key() == -1:
                    self.close()
                return False
            sock.shutdown(SHUT_RDWR)
            sock.close()

            sock = socket(AF_INET, SOCK_STREAM)
            sock.settimeout(60)
            try:
                sock.connect(('localhost', port))
                sendmsg(sock, build_message((b'GETC',)))
            except OSError as err:
                self.draw_text(False, (1, 0, err.__str__()),
                                      (3, 0, "Press any key."))
                if self.any_key() == -1:
                    self.close()
                return False

            answer = receive(sock)
            parts = answer.split(b'\xB2\xEA\xC0')
            password = parts.pop(0).decode()
            keyfile_cont = parts.pop(0).decode()
            if keyfile_cont == '':
                keyfile = None
            else:
                if not isdir('/tmp/keepassc'):
                    makedirs('/tmp/keepassc')
                with open('/tmp/keepassc/tmp_keyfile', 'w') as handler:
                    handler.write(parts.pop(0).decode())
                    keyfile = '/tmp/keepassc/tmp_keyfile'

            server = parts.pop(0).decode()
            port = int(parts.pop(0))
            if parts.pop(0) == b'True':
                ssl = True
            else:
                ssl = False
            tls_dir = parts.pop(0).decode()
        elif use_agent is False:
            return False
        elif use_agent == -1:
            self.close()
        else:
            if isfile(self.remote_home):
                with open(self.remote_home, 'r') as handler:
                    last_address = handler.readline()
                    last_port = handler.readline()
            else:
                last_address = '127.0.0.1'
                last_port = None

            pass_auth = False
            pass_ssl = False
            while True:
                if pass_auth is False:
                    ret = self.get_authentication()
                    if ret is False:
                        return False
                    elif ret == -1:
                        self.close()
                    password, keyfile = ret
                pass_auth = True
                if pass_ssl is False:
                    ssl = self.gen_menu(1, ((1, 0, 'Use SSL/TLS (1)'),
                                            (2, 0, 'Plain text (2)')))
                    if ssl is False:
                        pass_auth = False
                        continue
                    elif ssl == -1:
                        self.close()
                pass_ssl = True
                server = Editor(self.stdscr, max_text_size=1,
                                inittext=last_address,
                                win_location=(0, 1),
                                win_size=(1, self.xsize),
                                title="Server address")()
                if server is False:
                    pass_ssl = False
                    continue
                elif server == -1:
                    self.close()
                if last_port is None:
                    if ssl == 1:
                        ssl = True # for later use
                        std_port = "50003"
                    else:
                        ssl = False
                        std_port = "50000"
                else:
                    if ssl == 1:
                        ssl = True # for later use
                    else:
                        ssl = False
                    std_port = last_port

                port = self.get_num("Server port: ", std_port, 5)
                if port is False:
                    path_auth = True
                    path_ssl = True
                    continue
                elif port == -1:
                    self.close()
                break

            if ssl is True:
                try:
                    datapath = realpath(expanduser(getenv('XDG_DATA_HOME')))
                except:
                    datapath = realpath(expanduser('~/.local/share'))
                finally:
                    tls_dir = join(datapath, 'keepassc')
            else:
                tls_dir = None

            client = Client(logging.INFO, 'client.log', server, port,
                            password, keyfile, ssl, tls_dir)
            db_buf = client.get_db()
            if db_buf[:4] == 'FAIL' or db_buf[:4] == "[Err":
                self.draw_text(False,
                               (1, 0, db_buf),
                               (3, 0, 'Press any key.'))
                if self.any_key() == -1:
                    self.close()
                return False
        self.db = KPDBv1(None, password, keyfile)
        self.db.load(db_buf)
        db = DBBrowser(self, True, server, port, ssl, tls_dir)
        del db
        return True

    def browser_help(self, mode_new):
        '''Print help for filebrowser'''

        if mode_new:
            self.draw_help(
            'Navigate with arrow keys.',
            '\'o\' - choose directory',
            '\'e\' - abort',
            '\'H\' - show/hide hidden files',
            '\'ngg\' - move to line n',
            '\'G\' - move to last line',
            '/text - go to \'text\' (like in vim/ranger)',
            '\n',
            'Press return.')
        else:
            self.draw_help(
            'Navigate with arrow keys.',
            '\'q\' - close program',
            '\'e\' - abort',
            '\'H\' - show/hide hidden files',
            '\'ngg\' - move to line n',
            '\'G\' - move to last line',
            '/text - go to \'text\' (like in vim/ranger)',
            '\n',
            'Press return.')

    def dbbrowser_help(self):
        self.draw_help(
        '\'e\' - go to main menu',
        '\'q\' - close program',
        '\'CTRL+D\' or \'CTRL+C\' - close program at any time',
        '\'x\' - save db and close program',
        '\'s\' - save db',
        '\'S\' - save db with alternative filepath',
        '\'c\' - copy password of current entry',
        '\'b\' - copy username of current entry',
        '\'H\' - show password of current entry',
        '\'o\' - open URL of entry in standard webbrowser',
        '\'P\' - edit db password',
        '\'g\' - create group',
        '\'G\' - create subgroup',
        '\'y\' - create entry',
        '\'d\' - delete group or entry (depends on what is marked)',
        '\'t\' - edit title of selected group or entry',
        '\'u\' - edit username',
        '\'p\' - edit password',
        '\'U\' - edit URL',
        '\'C\' - edit comment',
        '\'E\' - edit expiration date',
        '\'f\' or \'/\' - find entry by title',
        '\'L\' - lock db',
        '\'m\' - enter move mode for marked group or entry',
        '\'r\' - reload remote database (no function if not remote)',
        'Navigate with arrow keys or h/j/k/l like in vim',
        'Type \'return\' to enter subgroups',
        'Type \'backspace\' to go back to parent',
        'Type \'F5\' in a dialog to return to the previous one',
        '\n',
        'Press return.')

    def move_help(self):
        self.draw_help(
        '\'e\' - go to main menu',
        '\'q\' - close program',
        '\'CTRL+D\' or \'CTRL+C\' - close program at any time',
        'Navigate up or down with arrow keys or k and j',
        'Navigate to subgroup with right arrow key or h',
        'Navigate to parent with left arrow key or l',
        'Type \'return\' to move the group to marked parent or the entry',
        '\tto the marked group',
        'Type \'backspace\' to move a group to the root',
        'Type \'ESC\' to abort moving',
        '\n',
        'Press return.')

    def show_dir(self, highlight, dir_cont):
        '''List a directory with highlighting.'''

        self.draw_text(changed=False)
        for i in range(len(dir_cont)):
            if i == highlight:
                if isdir(self.cur_dir + '/' + dir_cont[i]):
                    try:
                        self.stdscr.addstr(
                            i + 1, 0, dir_cont[i], cur.color_pair(5))
                    except:
                        pass
                else:
                    try:
                        self.stdscr.addstr(
                            i + 1, 0, dir_cont[i], cur.color_pair(3))
                    except:
                        pass
            else:
                if isdir(self.cur_dir + '/' + dir_cont[i]):
                    try:
                        self.stdscr.addstr(
                            i + 1, 0, dir_cont[i], cur.color_pair(4))
                    except:
                        pass
                else:
                    try:
                        self.stdscr.addstr(i + 1, 0, dir_cont[i])
                    except:
                        pass
        self.stdscr.refresh()

    def close(self):
        '''Close the program correctly.'''

        if self.config['rem_key'] is False and isfile(self.key_home):
            remove(self.key_home)
        cur.nocbreak()
        self.stdscr.keypad(0)
        cur.endwin()
        exit()

    def show_groups(self, highlight, groups, cur_win, offset, changed, parent):
        '''Just print all groups in a column'''

        self.draw_text(changed)
        self.group_win.clear()
            
        if parent is self.db.root_group:
            root_title = 'Parent: _ROOT_'
        else:
            root_title = 'Parent: ' + parent.title
        if cur_win == 0:
            h_color = 5
            n_color = 4
        else:
            h_color = 6
            n_color = 1

        try:
            ysize = self.group_win.getmaxyx()[0]
            self.group_win.addstr(0, 0, root_title,
                                  cur.color_pair(n_color))
            if groups:
                if len(groups) <= ysize - 3:
                    num = len(groups)
                else:
                    num = ysize - 3

                for i in range(num):
                    if highlight == i + offset:
                        if groups[i + offset].children:
                            title = '+' + groups[i + offset].title
                        else:
                            title = ' ' + groups[i + offset].title
                        self.group_win.addstr(i + 1, 0, title,
                                              cur.color_pair(h_color))
                    else:
                        if groups[i + offset].children:
                            title = '+' + groups[i + offset].title
                        else:
                            title = ' ' + groups[i + offset].title
                        self.group_win.addstr(i + 1, 0, title,
                                              cur.color_pair(n_color))
                x_of_n = str(highlight + 1) + ' of ' + str(len(groups))
                self.group_win.addstr(ysize - 2, 0, x_of_n)
        except:
            pass
        finally:
            self.group_win.refresh()

    def show_entries(self, e_highlight, entries, cur_win, offset):
        '''Just print all entries in a column'''

        self.info_win.clear()
        try:
            self.entry_win.clear()
            if entries:
                if cur_win == 1:
                    h_color = 5
                    n_color = 4
                else:
                    h_color = 6
                    n_color = 1

                ysize = self.entry_win.getmaxyx()[0]
                if len(entries) <= ysize - 3:
                    num = len(entries)
                else:
                    num = ysize - 3

                for i in range(num):
                    title = entries[i + offset].title
                    if date.today() > entries[i + offset].expire.date():
                        expired = True
                    else:
                        expired = False
                    if e_highlight == i + offset:
                        if expired is True:
                            self.entry_win.addstr(i, 2, title,
                                                  cur.color_pair(3))
                        else:
                            self.entry_win.addstr(i, 2, title,
                                                  cur.color_pair(h_color))
                    else:
                        if expired is True:
                            self.entry_win.addstr(i, 2, title,
                                                  cur.color_pair(7))
                        else:
                            self.entry_win.addstr(i, 2, title,
                                                  cur.color_pair(n_color))
                self.entry_win.addstr(ysize - 2, 2, (str(e_highlight + 1) +
                                                     ' of ' +
                                                     str(len(entries))))
        except:
            pass
        finally:
            self.entry_win.noutrefresh()

        try:
            if entries:
                xsize = self.entry_win.getmaxyx()[1]
                entry = entries[e_highlight]
                if entry.title is None:
                    title = ""
                elif len(entry.title) > xsize:
                    title = entry.title[:xsize - 2] + '\\'
                else:
                    title = entry.title
                if entry.group.title is None:
                    group_title = ""
                elif len(entry.group.title) > xsize:
                    group_title = entry.group.title[:xsize - 9] + '\\'
                else:
                    group_title = entry.group.title
                if entry.username is None:
                    username = ""
                elif len(entry.username) > xsize:
                    username = entry.username[:xsize - 12] + '\\'
                else:
                    username = entry.username
                if entry.url is None:
                    url = ""
                elif len(entry.url) > xsize:
                    url = entry.title[:xsize - 7] + '\\'
                else:
                    url = entry.url
                if entry.creation is None:
                    creation = ""
                else:
                    creation = entry.creation.__str__()[:10]
                if entry.last_access is None:
                    last_access = ""
                else:
                    last_access = entry.last_access.__str__()[:10]
                if entry.last_mod is None:
                    last_mod = ""
                else:
                    last_mod = entry.last_mod.__str__()[:10]
                if entry.expire is None:
                    expire = ""
                else:
                    if entry.expire.__str__()[:19] == '2999-12-28 23:59:59':
                        expire = "Expires: Never"
                    else:
                        expire = "Expires: " + entry.expire.__str__()[:10]
                if entry.comment is None:
                    comment = ""
                else:
                    comment = entry.comment

                self.info_win.addstr(2, 0, title, cur.A_BOLD)
                self.info_win.addstr(3, 0, "Group: " + group_title)
                self.info_win.addstr(4, 0, "Username: " + username)
                self.info_win.addstr(5, 0, "URL: " + url)
                self.info_win.addstr(6, 0, "Creation: " + creation)
                self.info_win.addstr(7, 0, "Access: " + last_access)
                self.info_win.addstr(8, 0, "Modification: " + last_mod)
                self.info_win.addstr(9, 0, expire)
                if date.today() > entry.expire.date():
                    self.info_win.addstr(9, 22, ' (expired)')
                if '\n' in comment:
                    comment = comment.split('\n')[0]
                    dots = ' ...'
                else:
                    dots = ''
                self.info_win.addstr(10, 0, "Comment: " + comment + dots)
        except:
            pass
        finally:
            self.info_win.noutrefresh()
        cur.doupdate()
