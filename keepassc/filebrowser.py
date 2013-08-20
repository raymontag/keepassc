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

from keepassc.editor import Editor

class FileBrowser(object):
    '''This class represents the file browser'''

    def __init__(self, control, ask_for_lf, keyfile, last_file, mode_new = False):

        self.control = control
        self.ask_for_lf = ask_for_lf
        self.keyfile = keyfile
        self.last_file = last_file
        self.mode_new = mode_new
        self.highlight = 0
        self.kdb_file = None
        if self.control.cur_dir[-4:] == '.kdb':
            self.kdb_file = self.control.cur_dir.split('/')[-1]
            self.control.cur_dir = self.control.cur_dir[:-len(self.kdb_file) - 1]
            self.kdb_file = self.control.cur_dir + '/' + self.kdb_file
        self.hidden = True
        self.dir_cont = []
        self.return_flag = False
        self.lookup = {
            cur.KEY_DOWN:   self.nav_down,
            ord('j'):       self.nav_down,
            cur.KEY_UP:     self.nav_up,
            ord('k'):       self.nav_up,
            cur.KEY_LEFT:   self.nav_left,
            ord('h'):       self.nav_left,
            cur.KEY_RIGHT:  self.nav_right,
            ord('l'):       self.nav_right,
            NL:             self.nav_right,
            cur.KEY_RESIZE: self.control.resize_all,
            cur.KEY_F1:     self.browser_help,
            ord('H'):       self.show_hidden,
            ord('o'):       self.open_file,
            cur.KEY_F5:     self.cancel,
            ord('e'):       self.cancel,
            4:              self.close,
            ord('q'):       self.close,
            ord('G'):       self.G_typed,
            ord('/'):       self.find}
        self.find_rem = []
        self.find_pos = 0

    def __call__(self):
        ret = self.get_filepath()
        if self.kdb_file is not None:
            self.control.cur_dir = self.kdb_file
        return ret

    def get_filepath(self):
        '''This method is used to get a filepath, e.g. for 'Save as' '''

        if (self.ask_for_lf is False or self.last_file is None or 
            self.control.config['rem_db'] is False):
            nav = self.control.gen_menu(1, (
                    (1, 0, 'Use the file browser (1)'),
                    (2, 0, 'Type direct path (2)')))
        else:
            nav = self.control.gen_menu(1, (
                    (1, 0, 'Use ' + self.last_file + ' (1)'),
                    (2, 0, 'Use the file browser (2)'),
                    (3, 0, 'Type direct path (3)')))
        if ((self.ask_for_lf is True and self.last_file is not None and 
             nav == 2) or
            ((self.last_file is None or self.ask_for_lf is False) and 
             nav == 1)):
            if self.keyfile is True:
                filepath = self.browser()
            else:
                filepath = self.browser()
                if type(filepath) is str:
                    if filepath[-4:] != '.kdb' and filepath is not False:
                        filename = Editor(self.control.stdscr, max_text_size=1,
                                          win_location=(0, 1), win_size=(1, 80),
                                          title="Filename: ")()
                        if filename == "":
                            return False
                        filepath += '/' + filename + '.kdb'
            return filepath
        if ((self.ask_for_lf is True and self.last_file is not None and 
             nav == 3) or
            ((self.last_file is None or self.ask_for_lf is False) and 
             nav == 2)):
            while True:
                if self.last_file:
                    init = self.last_file
                else:
                    init = ''
                filepath = self.get_direct_filepath()
                if filepath is False:
                    return False
                elif filepath == -1:
                    return -1
                elif ((filepath[-4:] != '.kdb' or isdir(filepath)) and
                      self.keyfile is False):
                    self.control.draw_text(False,
                                           (1, 0, 'Need path to a kdb-file!'),
                                           (3, 0, 'Press any key'))
                    if self.control.any_key() == -1:
                        return -1
                    continue
                else:
                    return filepath
        elif nav == 1:  # it was asked for last file
            return self.last_file
        elif nav == -1:
            return -1
        else:
            return False

    def get_direct_filepath(self):
        '''Get a direct filepath.'''

        e = ''
        show = 0
        rem = []
        cur_dir = ''
        if self.last_file is not None:
            edit = self.last_file
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

    def nav_down(self):
        '''Navigate down'''

        if self.highlight < len(self.dir_cont) - 1:
            self.highlight += 1

    def nav_up(self):
        '''Navigate up'''

        if self.highlight > 0:
            self.highlight -= 1

    def nav_left(self):
        '''Navigate left'''

        last = self.control.cur_dir.split('/')[-1]
        self.control.cur_dir = self.control.cur_dir[:-len(last) - 1]
        if self.control.cur_dir == '':
            self.control.cur_dir = '/'
        self.highlight = 0
        self.get_dir_cont()
        self.find_rem = []
        self.find_pos = 0

    def nav_right(self):
        '''Navigate right'''

        self.find_rem = []
        self.find_pos = 0
        if self.dir_cont[self.highlight] == '..':
            last = self.control.cur_dir.split('/')[-1]
            self.control.cur_dir = self.control.cur_dir[:-len(last) - 1]
            if self.control.cur_dir == '':
                self.control.cur_dir = '/'
            self.highlight = 0
            self.get_dir_cont()
        elif isdir(self.control.cur_dir + '/' + self.dir_cont[self.highlight]):
            self.control.cur_dir = (self.control.cur_dir + '/' +
                                    self.dir_cont[self.highlight])
            if self.control.cur_dir[:2] == '//':
                self.control.cur_dir = self.control.cur_dir[1:]
            self.highlight = 0
            self.get_dir_cont()
        else:
            ret = self.control.cur_dir + '/' + self.dir_cont[self.highlight]
            if self.kdb_file is not None:
                self.control.cur_dir = self.kdb_file
            self.return_flag = True
            return ret

    def show_hidden(self):
        '''Show hidden files'''

        if self.hidden is True:
            self.hidden = False
        else:
            self.hidden = True
        self.get_dir_cont()

    def browser_help(self):
        '''Show help'''

        self.control.browser_help(self.mode_new)

    def open_file(self):
        '''Return dir or file for "save as..."'''

        if self.mode_new is True:
            if self.kdb_file is not None:
                ret = self.control.cur_dir
                self.control.cur_dir = self.kdb_file
                self.return_flag = True
                return ret
            else:
                self.return_flag = True
                return self.control.cur_dir

    def cancel(self):
        '''Cancel browser'''

        self.return_flag = True
        return False

    def close(self):
        '''Close KeePassC'''

        self.return_flag = True
        return -1

    def start_gg(self, c):
        '''Enable gg like in vim'''

        gg = chr(c)
        while True:
            try:
                c = self.control.stdscr.getch()
            except KeyboardInterrupt:
                c = 4

            if gg[-1] == 'g' and c == ord('g') and gg[:-1] != '':
                if int(gg[:-1]) > len(self.dir_cont):
                    self.highlight = len(self.dir_cont) -1
                else:
                    self.highlight = int(gg[:-1]) -1
                return True
            elif gg[-1] == 'g' and c == ord('g') and gg[:-1] == '':
                self.highlight = 0
                return True
            elif gg[-1] != 'g' and c == ord('g'):
                gg += 'g'
            elif 48 <= c <= 57 and gg[-1] != 'g':
                gg += chr(c)
            elif c in self.lookup:
                return c

    def G_typed(self):
        '''G typed => last entry (like in vim)'''

        self.highlight = len(self.dir_cont) - 1

    def find(self):
        '''Find a directory or file like in ranger'''

        filename = Editor(self.control.stdscr, max_text_size=1,
                          win_location=(0, 1), win_size=(1, 80),
                          title="Filename to find: ")()
        if filename == '' and self.find_pos < len(self.find_rem) - 1:
            self.find_pos += 1
        elif filename == '':
            self.find_pos = 0
        else:
            self.find_rem = []
            self.find_pos = 0
            for i in self.dir_cont:
                if filename.lower() in i.lower():
                    self.find_rem.append(i)
        if self.find_rem:
            self.highlight = self.dir_cont.index(self.find_rem[self.find_pos])

    def browser(self):
        '''A simple file browser.'''

        self.get_dir_cont()
        if self.dir_cont == -1 or self.dir_cont is False:
            return self.dir_cont

        old_highlight = None
        while True:
            if old_highlight != self.highlight:
                self.control.show_dir(self.highlight, self.dir_cont)
            try:
                c = self.control.stdscr.getch()
            except KeyboardInterrupt:
                c = 4

            if 49 <= c <= 57 or c == ord('g'):
                c = self.start_gg(c)

            old_highlight = self.highlight
            if c in self.lookup:
                ret = self.lookup[c]()
                if self.return_flag is True:
                    return ret

    def get_dir_cont(self):
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
                    i[-4:] == '.kdb' and self.keyfile is False) or
                    (i[0] == '.' and self.hidden is True)):
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

        self.dir_cont = []
        self.dir_cont.extend(dirs)
        self.dir_cont.extend(files)
        if not self.control.cur_dir == '/':
            self.dir_cont.insert(0, '..')
