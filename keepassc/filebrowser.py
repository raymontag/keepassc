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
from curses.ascii import NL, DEL
from os import listdir
from os.path import expanduser, isdir

class FileBrowser(object):
    '''This class represents the file browser'''

    def __init__(self, control):

        self.control = control

    def get_filepath(self, ask_for_lf=True, keyfile=False, last_file=None):
        '''This method is used to get a filepath, e.g. for 'Save as' '''

        if ask_for_lf is False or last_file is None:
            nav = self.control.gen_menu((
                (1, 0, 'Use the file browser (1)'),
                (2, 0, 'Type direct path (2)')))
        else:
            nav = self.control.gen_menu((
                (1, 0, 'Use ' + last_file + ' (1)'),
                (2, 0, 'Use the file browser (2)'),
                (3, 0, 'Type direct path (3)')))
        if ((ask_for_lf is True and last_file is not None and nav == 2) or
                ((last_file is None or ask_for_lf is False) and nav == 1)):
            if keyfile is True:
                filepath = self.browser(False, keyfile)
            else:
                filepath = self.browser(True)
                if type(filepath) is str:
                    if filepath[-4:] != '.kdb' and filepath is not False:
                        filename = self.control.get_string('', 'Filename: ')
                        filepath += '/' + filename + '.kdb'
            return filepath
        if ((ask_for_lf is True and last_file is not None and nav == 3) or
                ((last_file is None or ask_for_lf is False) and nav == 2)):
            while True:
                filepath = self.get_direct_filepath(last_file)
                if filepath is False:
                    return False
                elif filepath == -1:
                    return -1
                elif ((filepath[-4:] != '.kdb' or isdir(filepath)) and
                      keyfile is False):
                    self.control.draw_text(False,
                                           (1, 0, 'Need path to a kdb-file!'),
                                           (3, 0, 'Press any key'))
                    if self.control.any_key() == -1:
                        return -1
                    continue
                else:
                    return filepath
        elif nav == 1:  # it was asked for last file
            return last_file
        elif nav == -1:
            return -1
        else:
            return False

    def get_direct_filepath(self, last_file=None):
        '''Get a direct filepath.'''

        e = ''
        show = 0
        rem = []
        cur_dir = ''
        if last_file is not None:
            edit = last_file
        else:
            edit = ''
        while e != '\n':
            if e == cur.KEY_BACKSPACE or e == chr(DEL) and len(edit) != 0:
                edit = edit[:-1]
                show = 0
                rem = []
                cur_dir = ''
            elif e == cur.KEY_BACKSPACE or e == chr(DEL):
                pass
            elif e == '\x04':
                return -1
            elif e == '':
                pass
            elif e == cur.KEY_F5:
                return False
            elif e == cur.KEY_RESIZE:
                self.control.resize_all()
            elif e == '~':
                edit += expanduser('~/')
                show = 0
                rem = []
                cur_dir = ''
            elif e == '\t':
                if cur_dir == '':
                    last = edit.split('/')[-1]
                    cur_dir = edit[:-len(last)]
                try:
                    dir_cont = listdir(cur_dir)
                except OSError:
                    pass
                else:
                    if len(rem) == 0:
                        for i in dir_cont:
                            if i[:len(last)] == last:
                                rem.append(i)
                    if len(rem) > 0:
                        edit = cur_dir + rem[show]
                    else:
                        edit = cur_dir + last
                    if show + 1 >= len(rem):
                        show = 0
                    else:
                        show += 1
                    if isdir(edit):
                        edit += '/'
            elif type(e) is not int:
                show = 0
                rem = []
                cur_dir = ''
                edit += e

            self.control.draw_text(False, (1, 0, 'Filepath: ' + edit))
            try:
                e = self.control.stdscr.get_wch()
            except KeyboardInterrupt:
                e = '\x04'
        return edit

    def browser(self, mode_new=False, keyfile=False):
        '''A simple file browser.

        mode_new is needed to get a filepath to a new database file.

        '''

        kdb_file = None
        if self.control.cur_dir[-4:] == '.kdb':
            kdb_file = self.control.cur_dir.split('/')[-1]
            self.control.cur_dir = self.control.cur_dir[:-len(kdb_file) - 1]
            kdb_file = self.control.cur_dir + '/' + kdb_file

        hidden = True
        highlight = 0
        dir_cont = self.get_dir_cont(hidden, keyfile)
        if dir_cont == -1 or dir_cont is False:
            return dir_cont
        while True:
            self.control.show_dir(highlight, dir_cont)
            try:
                c = self.control.stdscr.getch()
            except KeyboardInterrupt:
                c = 4
            if c == cur.KEY_DOWN or c == ord('j'):
                if highlight >= len(dir_cont) - 1:
                    continue
                highlight += 1
            elif c == cur.KEY_UP or c == ord('k'):
                if highlight <= 0:
                    continue
                highlight -= 1
            elif c == cur.KEY_LEFT or c == ord('h'):
                last = self.control.cur_dir.split('/')[-1]
                self.control.cur_dir = self.control.cur_dir[:-len(last) - 1]
                if self.control.cur_dir == '':
                    self.control.cur_dir = '/'
                highlight = 0
                dir_cont = self.get_dir_cont(hidden, keyfile)
            elif c == NL or c == cur.KEY_RIGHT or c == ord('l'):
                if dir_cont[highlight] == '..':
                    last = self.control.cur_dir.split('/')[-1]
                    self.control.cur_dir = self.control.cur_dir[:-len(last) - 1]
                    if self.control.cur_dir == '':
                        self.control.cur_dir = '/'
                    highlight = 0
                    dir_cont = self.get_dir_cont(hidden, keyfile)
                elif isdir(self.control.cur_dir + '/' + dir_cont[highlight]):
                    self.control.cur_dir = (self.control.cur_dir + '/' +
                                            dir_cont[highlight])
                    if self.control.cur_dir[:2] == '//':
                        self.control.cur_dir = self.control.cur_dir[1:]
                    highlight = 0
                    dir_cont = self.get_dir_cont(hidden, keyfile)
                else:
                    ret = self.control.cur_dir + '/' + dir_cont[highlight]
                    if kdb_file is not None:
                        self.control.cur_dir = kdb_file
                    return ret
            elif c == cur.KEY_RESIZE:
                self.control.resize_all()
            elif c == cur.KEY_F1:
                self.control.browser_help(mode_new)
            elif c == cur.KEY_F5:
                return False
            elif c == ord('H'):
                if hidden is True:
                    hidden = False
                else:
                    hidden = True
                dir_cont = self.get_dir_cont(hidden, keyfile)
            elif c == 4:
                return -1
            elif c == ord('q') and mode_new is not True:
                return -1
            elif c == ord('e'):
                return False
            elif c == ord('o') and mode_new is True:
                if kdb_file is not None:
                    ret = self.control.cur_dir
                    self.control.cur_dir = kdb_file
                    return ret
                else:
                    return self.control.cur_dir

    def get_dir_cont(self, hidden, keyfile):
        '''Get the content of the current dir'''

        try:
            dir_cont = listdir(self.control.cur_dir)
        except OSError:
            self.control.draw_text(False,
                                   (1, 0, 'Was not able to read directory'),
                                   (2, 0, 'Press any key.'))
            if self.control.any_key() == -1:
                return -1
            last = self.control.cur_dir.split('/')[-1]
            self.control.cur_dir = self.control.cur_dir[:-len(last) - 1]
            if self.control.cur_dir == '':
                self.control.cur_dir = '/'
            return False

        rem = []
        for i in dir_cont:
            if ((not isdir(self.control.cur_dir + '/' + i) and not
                    i[-4:] == '.kdb' and keyfile is False) or
                    (i[0] == '.' and hidden is True)):
                rem.append(i)
        for i in rem:
            dir_cont.remove(i)

        dirs = []
        files = []
        for i in dir_cont:
            if isdir(self.control.cur_dir + '/' + i):
                dirs.append(i)
            else:
                files.append(i)
        dirs.sort()
        files.sort()

        dir_cont = []
        dir_cont.extend(dirs)
        dir_cont.extend(files)
        if not self.control.cur_dir == '/':
            dir_cont.insert(0, '..')
        return dir_cont
