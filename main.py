#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (C) 2012 Karsten-Kai König <kkoenig@posteo.de>

This file is part of keepassc.

keepassc is free software: you can redistribute it and/or modify it under the terms
of the GNU General Public License as published by the Free Software Foundation,
either version 3 of the License, or at your option) any later version.

keepassc is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
keepassc.  If not, see <http://www.gnu.org/licenses/>.
'''

from curses import *
from curses.ascii import NL
from datetime import date
from os import *
from os.path import isdir, isfile
from socket import gethostname
from subprocess import Popen, PIPE
from sys import exit, argv

from kppy import *

class App(object):
    def __init__(self):
        self.stdscr = initscr()
        curs_set(0)
        cbreak()
        noecho()
        self.stdscr.keypad(1)
        start_color()
        use_default_colors()
        init_pair(1, -1, -1)
        init_pair(2, 2, -1)
        init_pair(3, 0, 1)
        init_pair(4, 6, -1)
        init_pair(5, 0, 6)
        init_pair(6, 0, 7)
        self.stdscr.bkgd(1)

        self.loginname = getlogin()
        self.hostname = gethostname()
        self.cur_dir = getcwd()
        chdir('/var/empty')

        self.term_size = self.stdscr.getmaxyx()
        self.db = None

    def get_string(self, edit, std):
        offset = len(std)
        e = ''
        while e != NL:
            if e == KEY_BACKSPACE and len(edit) != 0:
                edit = edit[:-1]
            elif e == KEY_BACKSPACE:
                pass
            elif e == -1:
                Popen(['xsel', '-bi'], stdin = PIPE).communicate(''.encode())
                Popen(['xsel', '-pi'], stdin = PIPE).communicate(''.encode())
            elif e == '':
                pass
            else:
                edit += chr(e)
            self.stdscr.clear()
            self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                               color_pair(2))
            self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                               self.cur_dir)
            self.stdscr.addstr(1,0, std)
            self.stdscr.addstr(1,offset, edit)
            self.stdscr.refresh()
            e = self.stdscr.getch()
        return edit

    def get_password(self, std, needed = True):
        self.stdscr.clear()
        self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                           color_pair(2))
        self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'),
                           self.cur_dir)
        self.stdscr.addstr(1,0, std)
        self.stdscr.refresh()
        
        password = ''
        e = ''
        while e != NL or (len(password) == 0 and needed is True):
            e = self.stdscr.getch()
            if e == KEY_BACKSPACE and len(password) != 0:
                password = password[:-1]
            elif e == KEY_BACKSPACE:
                pass
            elif e == '':
                pass
            elif e == -1:
                Popen(['xsel', '-bi'], stdin = PIPE).communicate(''.encode())
                Popen(['xsel', '-pi'], stdin = PIPE).communicate(''.encode())
            else:
                password += chr(e)
                if ord(password[-1]) == NL:
                    password = password[:-1]
        return password

    def main_loop(self):
        while True:
            self.stdscr.clear()
            self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                               color_pair(2))
            self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                               self.cur_dir)
            self.stdscr.addstr(1,0, 'To open an existing database type \'o\',')
            self.stdscr.addstr(2,0, 'to create a new one type \'n\'.')
            self.stdscr.addstr(4,0, 'Type \'q\' to quit.')
            self.stdscr.refresh()

            c = self.stdscr.getch()
            if c == ord('o'):
                ret = self.open_db()
                if ret is False:
                    continue
                self.db_browser()
                last = self.cur_dir.split('/')[-1]
                self.cur_dir = self.cur_dir[:-len(last)-1]
            elif c == ord('n'):
                self.db = KPDB(new = True)
                self.db.masterkey = self.get_password('Password: ')
                self.db_browser()
                last = self.cur_dir.split('/')[-1]
                self.cur_dir = self.cur_dir[:-len(last)-1]
            elif c == ord('q'):
                self.close()

    def open_db(self):
        while True:
            filepath = self.browser()
            
            if filepath is False:
                continue
            elif filepath == ord('e'):
                return False
            else:
                self.cur_dir = filepath
                password = self.get_password('Password: ')

                try:
                    if isfile(self.cur_dir+'.lock'):
                        self.stdscr.clear()
                        self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                           color_pair(2))
                        self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                           self.cur_dir)
                        self.stdscr.addstr(1,0, 'Database seems to be opened. Open file in read-only mode? [(y)/n]')
                        self.stdscr.refresh()
                        e = self.stdscr.getch()
                        self.stdscr.clear()
                        self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                           color_pair(2))
                        self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                           self.cur_dir)
                        self.stdscr.refresh()
                        if e == ord('n'):
                            self.db = KPDB(self.cur_dir, password, False)
                        else:
                            self.db = KPDB(self.cur_dir, password, True)
                    else:
                        self.db = KPDB(self.cur_dir, password, False)
                except KPError as err:
                    self.stdscr.clear()
                    self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                       color_pair(2))
                    self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                       self.cur_dir)
                    self.stdscr.addstr(1,0, err.__str__())
                    self.stdscr.addstr(4,0, 'Press any key.')
                    self.stdscr.refresh()
                    self.stdscr.getch()
                    self.stdscr.clear()
                    self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                       color_pair(2))
                    self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                       self.cur_dir)
                    self.stdscr.refresh()
                    last = self.cur_dir.split('/')[-1]
                    self.cur_dir = self.cur_dir[:-len(last)-1]
                    continue
                break

    def get_filepath(self):
        while True:
            filepath = self.browser(True)
            if filepath is False:
                continue
            elif filepath == ord('e'):
                return False
            else:
                break

        filename = self.get_string('', 'Filename: ')

        self.stdscr.clear()
        self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':',  
                           color_pair(2))
        self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                           self.cur_dir)
        self.stdscr.refresh()
        filepath += '/'+filename+'.kdb'
        return filepath

    def browser(self, mode_new = False):
        kdb_file = None
        if self.cur_dir[-4:] == '.kdb':
            kdb_file = self.cur_dir.split('/')[-1]
            self.cur_dir = self.cur_dir[:-len(kdb_file)-1]

        self.stdscr.clear()
        self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':',  
                           color_pair(2))
        self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                           self.cur_dir)
        self.stdscr.refresh()

        try:
            dir_cont = listdir(self.cur_dir)
        except OSError:
            self.stdscr.clear()
            self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                               color_pair(2))
            self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                               self.cur_dir)
            self.stdscr.addstr(1,0, 'Was not able to read directory.')
            self.stdscr.addstr(2,0, 'Press any key.')
            self.stdscr.refresh()
            self.stdscr.getch()
            self.stdscr.clear()
            self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                               color_pair(2))
            self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                               self.cur_dir)
            self.stdscr.refresh()
            last = self.cur_dir.split('/')[-1]
            self.cur_dir = self.cur_dir[:-len(last)-1]
            if self.cur_dir == '': self.cur_dir = '/';
            return False
            
        rem = []
        for i in dir_cont:
            if (not isdir(self.cur_dir+'/'+i) and not i[-3:] == 'kdb') \
                or i[0] == '.':
                rem.append(i)
        for i in rem:
            dir_cont.remove(i)
        
        dirs = []
        files = []
        for i in dir_cont:
            if isdir(self.cur_dir+'/'+i):
                dirs.append(i)
            else:
                files.append(i)
        dirs.sort()
        files.sort()

        dir_cont = []
        dir_cont.extend(dirs)
        dir_cont.extend(files)
        if not self.cur_dir == '/': dir_cont.insert(0, '..');

        highlight = 0
        self.show_dir(highlight, dir_cont)

        while True:
            c = self.stdscr.getch()
            if c == KEY_DOWN:
                if highlight >= len(dir_cont)-1:
                    continue
                highlight += 1
                self.show_dir(highlight, dir_cont)
            elif c == KEY_UP:
                if highlight <= 0:
                    continue
                highlight -= 1
                self.show_dir(highlight, dir_cont)
            elif c == KEY_LEFT:
                last = self.cur_dir.split('/')[-1]
                self.cur_dir = self.cur_dir[:-len(last)-1]
                if self.cur_dir == '': self.cur_dir = '/';
                if kdb_file is not None:
                    self.cur_dir += '/'+kdb_file
                return False
            elif c == NL or c == KEY_RIGHT:
                if dir_cont[highlight] == '..':
                    last = self.cur_dir.split('/')[-1]
                    self.cur_dir = self.cur_dir[:-len(last)-1]
                    if self.cur_dir == '': self.cur_dir = '/';
                    if kdb_file is not None:
                        self.cur_dir += '/'+kdb_file
                    return False
                elif isdir(self.cur_dir+'/'+dir_cont[highlight]):
                    self.cur_dir = self.cur_dir+'/'+dir_cont[highlight]
                    if self.cur_dir[:2] == '//':
                        self.cur_dir = self.cur_dir[1:]
                    if kdb_file is not None:
                        self.cur_dir += '/'+kdb_file
                    return False
                else:
                    if mode_new is False:
                        return self.cur_dir+'/'+dir_cont[highlight]
                    else:
                        if kdb_file is not None:
                            self.cur_dir += '/'+kdb_file
                        return False
            elif c == -1:
                Popen(['xsel', '-bi'], stdin = PIPE).communicate(''.encode())
                Popen(['xsel', '-pi'], stdin = PIPE).communicate(''.encode())
                return False
            elif c == ord('h') and mode_new is True:
                endwin()
                print('Navigate with arrow keys.')
                print('\'o\' - choose directory')
                print('\'e\' - abort')
                input('Press any key')
                self.stdscr = initscr()
                curs_set(0)
                cbreak()
                noecho()
                self.stdscr.keypad(1)
                start_color()
                use_default_colors()
                init_pair(1, -1, -1)
                init_pair(2, 2, -1)
                init_pair(3, 0, 1)
                init_pair(4, 6, -1)
                init_pair(5, 0, 6)
                init_pair(6, 0, 7)
                self.stdscr.bkgd(1)
                self.term_size = self.stdscr.getmaxyx()

                self.stdscr.clear()
                self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                   color_pair(2))
                self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                   self.cur_dir)
                self.stdscr.refresh()

                self.group_win = newwin(self.term_size[0]-1, int(self.term_size[1]/3), 
                                        1, 0)
                self.entry_win = newwin(int(2*(self.term_size[0]-1)/3), 
                                        int(2*self.term_size[1]/3)-2, 
                                        1, int(self.term_size[1]/3)+2)
                self.info_win = newwin(int((self.term_size[0]-1)/3)-1,
                                       int(2*self.term_size[1]/3)-2,
                                       int(2*(self.term_size[0]-1)/3)+1,
                                       int(self.term_size[1]/3)+2)
                self.group_win.keypad(1)
                self.entry_win.keypad(1)
                self.group_win.bkgd(1)
                self.entry_win.bkgd(1)
                self.info_win.bkgd(1)
                self.group_win.timeout(20000)
                self.stdscr.timeout(20000)
                return False
            elif c == ord('h'):
                endwin()
                print('Navigate with arrow keys.')
                print('\'q\' - quit program')
                print('\'e\' - abort')
                input('Press any key')
                self.stdscr = initscr()
                curs_set(0)
                cbreak()
                noecho()
                self.stdscr.keypad(1)
                start_color()
                use_default_colors()
                init_pair(1, -1, -1)
                init_pair(2, 2, -1)
                init_pair(3, 0, 1)
                init_pair(4, 6, -1)
                init_pair(5, 0, 6)
                init_pair(6, 0, 7)
                self.stdscr.bkgd(1)
                self.term_size = self.stdscr.getmaxyx()

                self.stdscr.clear()
                self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                   color_pair(2))
                self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                   self.cur_dir)
                self.stdscr.refresh()
                return False
            elif c == ord('q') and mode_new is not True:
                self.close()
            elif c == ord('e'):
                return c
            elif c == ord('o') and mode_new is True:
                if kdb_file is not None:
                    ret = self.cur_dir
                    self.cur_dir += '/'+kdb_file
                    return ret
                else:
                    return self.cur_dir

    def close(self):
        nocbreak()
        self.stdscr.keypad(0)
        endwin()
        exit()

    def show_dir(self, highlight, dir_cont):
        for i in range(len(dir_cont)):
            if i == highlight:
                if isdir(self.cur_dir+'/'+dir_cont[i]):
                    self.stdscr.addstr(i+1, 0, dir_cont[i], color_pair(5))
                else:
                    self.stdscr.addstr(i+1, 0, dir_cont[i], color_pair(3))
            else:
                if isdir(self.cur_dir+'/'+dir_cont[i]):
                    self.stdscr.addstr(i+1, 0, dir_cont[i], color_pair(4))
                else:    
                    self.stdscr.addstr(i+1, 0, dir_cont[i])
        self.stdscr.refresh()

    def save(self, cur_dir):
        if isfile(cur_dir):
            self.stdscr.clear()
            self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                               color_pair(2))
            self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                               self.cur_dir)
            self.stdscr.addstr(1,0, 'File exists. Overwrite? [y/(n)]')
            self.stdscr.refresh()
            c = self.stdscr.getch()
            if c != ord('y'):
                self.stdscr.clear()
                self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                   color_pair(2))
                self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                   self.cur_dir)
                self.refresh()
                return False
        try:
            if cur_dir is False:
                self.db.save()
            else:
                self.db.save(cur_dir)
        except KPError as err:
            self.stdscr.clear()
            self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                               color_pair(2))
            self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                               self.cur_dir)
            self.stdscr.addstr(1,0, err.__str__())
            self.stdscr.addstr(4,0, 'Press any key.')
            self.stdscr.refresh()
            self.stdscr.getch()
            self.stdscr.clear()
            self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                               color_pair(2))
            self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                               self.cur_dir)
            self.stdscr.refresh()
            return False

    def db_close(self):
        try:
            self.db.close()
        except KPError as err:
            self.stdscr.clear()
            self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                           color_pair(2))
            self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                           self.cur_dir)
            self.stdscr.addstr(1,0, err.__str__())
            self.stdscr.addstr(4,0, 'Press any key.')
            self.stdscr.refresh()
            self.stdscr.getch()
            self.stdscr.clear()
            self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                           color_pair(2))
            self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                           self.cur_dir)
            self.stdscr.refresh()

    def db_browser(self):
        self.group_win = newwin(self.term_size[0]-1, int(self.term_size[1]/3), 
                                1, 0)
        self.entry_win = newwin(int(2*(self.term_size[0]-1)/3), 
                                int(2*self.term_size[1]/3)-2, 
                                1, int(self.term_size[1]/3)+2)
        self.info_win = newwin(int((self.term_size[0]-1)/3)-1,
                               int(2*self.term_size[1]/3)-2,
                               int(2*(self.term_size[0]-1)/3)+1,
                               int(self.term_size[1]/3)+2)
        self.group_win.keypad(1)
        self.entry_win.keypad(1)
        self.group_win.bkgd(1)
        self.entry_win.bkgd(1)
        self.info_win.bkgd(1)
        self.group_win.timeout(20000)
        self.stdscr.timeout(20000)

        changed = False
        cur_root = self.db._root_group
        cur_win = 0
        g_highlight = 0
        e_highlight = 0
        g_offset = 0
        e_offset = 0
        self.show_groups(g_highlight, cur_root, cur_win, g_offset)
        self.show_entries(g_highlight, e_highlight, cur_root, cur_win, e_offset)

        while True:
            c = self.group_win.getch()
            
            if c == ord('\t'):
                if cur_win == 0:
                    c = KEY_RIGHT
                else:
                    c = KEY_LEFT

            if c == ord('h'):
                endwin()
                print('\'e\' - go to main menu')
                print('\'q\' - close program')
                print('\'x\' - save db and close program')
                print('\'s\' - save db')
                print('\'S\' - save db with alternative filepath')
                print('\'c\' - copy password of current entry')
                print('\'P\' - edit db password')
                print('\'g\' - create group')
                print('\'y\' - create entry')
                print('\'d\' - delete group or entry')
                print('\'t\' - edit title')
                print('\'u\' - edit username')
                print('\'p\' - edit password')
                print('\'U\' - edit URL')
                print('\'C\' - edit comment')
                print('\'E\' - edit expiration date')
                print('\'l\' - lock db')
                print('Navigate with arrow keys')
                print('Type \'return\' to enter subgroups')
                print('Type \'backspace\' to go back')
                input('Press any key.')
                self.stdscr = initscr()
                curs_set(0)
                cbreak()
                noecho()
                self.stdscr.keypad(1)
                start_color()
                use_default_colors()
                init_pair(1, -1, -1)
                init_pair(2, 2, -1)
                init_pair(3, 0, 1)
                init_pair(4, 6, -1)
                init_pair(5, 0, 6)
                init_pair(6, 0, 7)
                self.stdscr.bkgd(1)
                self.term_size = self.stdscr.getmaxyx()

                self.stdscr.clear()
                self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                   color_pair(2))
                self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                   self.cur_dir)
                self.stdscr.refresh()

                self.group_win = newwin(self.term_size[0]-1, int(self.term_size[1]/3), 
                                        1, 0)
                self.entry_win = newwin(int(2*(self.term_size[0]-1)/3), 
                                        int(2*self.term_size[1]/3)-2, 
                                        1, int(self.term_size[1]/3)+2)
                self.info_win = newwin(int((self.term_size[0]-1)/3)-1,
                                       int(2*self.term_size[1]/3)-2,
                                       int(2*(self.term_size[0]-1)/3)+1,
                                       int(self.term_size[1]/3)+2)
                self.group_win.keypad(1)
                self.entry_win.keypad(1)
                self.group_win.bkgd(1)
                self.entry_win.bkgd(1)
                self.info_win.bkgd(1)
                self.group_win.timeout(20000)
                self.stdscr.timeout(20000)

                self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                self.show_entries(g_highlight, e_highlight, cur_root, cur_win, e_offset)
            # File operations
            elif c == ord('e'):
                if changed is True:
                    self.stdscr.clear()
                    self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                       color_pair(2))
                    self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                       self.cur_dir)
                    self.stdscr.addstr(1,0, 'File has changed. Save? [(y)/n]')
                    self.stdscr.refresh()
                    e = self.stdscr.getch()
                    if not e == ord('n'):
                        if self.db.filepath is None:
                            filepath = self.get_filepath()
                            if filepath is not False:
                                self.cur_dir = filepath
                                self.save(self.cur_dir)
                        else:
                            self.save(False)
                self.db_close()
                Popen(['xsel', '-bi'], stdin = PIPE).communicate(''.encode())
                Popen(['xsel', '-pi'], stdin = PIPE).communicate(''.encode())
                self.group_win.clear()
                self.entry_win.clear()
                self.info_win.clear()
                self.group_win.noutrefresh()
                self.entry_win.noutrefresh()
                self.info_win.noutrefresh()
                doupdate()
                self.stdscr.timeout(-1)
                break
            elif c == ord('q'):
                Popen(['xsel', '-bi'], stdin = PIPE).communicate(''.encode())
                Popen(['xsel', '-pi'], stdin = PIPE).communicate(''.encode())
                if changed is True:
                    self.stdscr.clear()
                    self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                       color_pair(2))
                    self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                       self.cur_dir)
                    self.stdscr.addstr(1,0, 'File has changed. Save? [(y)/n]')
                    self.stdscr.refresh()
                    e = self.stdscr.getch()
                    if not e == ord('n'):
                        if self.db.filepath is None:
                            filepath = self.get_filepath()
                            if filepath is not False:
                                self.cur_dir = filepath
                                self.save(self.cur_dir)
                        else:
                            self.save(False)
                self.db_close()
                self.close()
            elif c == ord('c'):
                p = cur_root.children[g_highlight].entries[e_highlight].password
                Popen(['xsel', '-bi'], stdin = PIPE).communicate(p.encode())
                Popen(['xsel', '-pi'], stdin = PIPE).communicate(p.encode())
            elif c == -1:
                Popen(['xsel', '-bi'], stdin = PIPE).communicate(''.encode())
                Popen(['xsel', '-pi'], stdin = PIPE).communicate(''.encode())
            elif c == ord('s'):
                if self.db.filepath is None:
                    filepath = self.get_filepath()
                    if filepath is False:
                        self.stdscr.clear()
                        self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                           color_pair(2))
                        self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                           self.cur_dir)
                        self.stdscr.refresh()
                        self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                        self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                          e_offset)
                        continue
                    self.cur_dir = filepath
                    if self.save(self.cur_dir) is False:
                        self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                        self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                          e_offset)
                        continue
                self.stdscr.clear()
                self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                   color_pair(2))
                self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                   self.cur_dir)
                self.stdscr.refresh()
                self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                  e_offset)
                changed = False
            elif c == ord('S'):
                filepath = self.get_filepath()
                if filepath is False:
                    self.stdscr.clear()
                    self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                       color_pair(2))
                    self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                       self.cur_dir)
                    self.stdscr.refresh()
                    self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                    self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                      e_offset)
                    continue
                if self.db.filepath is None:
                    self.cur_dir = filepath
                if self.save(filepath) is False:
                    self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                    self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                      e_offset)
                    continue
                self.stdscr.clear()
                self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                   color_pair(2))
                self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                   self.cur_dir)
                self.stdscr.refresh()
                self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                  e_offset)
                changed = False
            elif c == ord('x'):
                Popen(['xsel', '-bi'], stdin = PIPE).communicate(''.encode())
                Popen(['xsel', '-pi'], stdin = PIPE).communicate(''.encode())

                if self.db.filepath is None:
                    filepath = self.get_filepath()
                    if filepath is False:
                        self.stdscr.clear()
                        self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                           color_pair(2))
                        self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                           self.cur_dir)
                        self.stdscr.refresh()
                        self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                        self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                          e_offset)
                        continue
                    else:
                        self.cur_dir = filepath
                if self.save(self.cur_dir) is False:
                    self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                    self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                      e_offset)
                    continue
                self.db_close()
                self.close()
            # DB editing
            elif c == ord('P'):
                password = self.get_password('New Password: ')
                confirm = self.get_password('Confirm: ')
                
                if password == confirm:
                    self.db.masterkey = password
                else:
                    self.stdscr.addstr(3,0, 'Passwords didn\'t match. Press any key.')
                    e = self.stdscr.getch()

                self.stdscr.clear()
                self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                   color_pair(2))
                self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'),
                                   self.cur_dir)
                self.stdscr.refresh()

                self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                  e_offset)
            elif c == ord('g'):
                edit = self.get_string('', 'Title: ')

                try: 
                    if cur_root is self.db._root_group:
                        self.db.create_group(edit)
                    else:
                        self.db.create_group(edit, cur_root)
                except KPError as err:
                    self.stdscr.clear()
                    self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                       color_pair(2))
                    self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                       self.cur_dir)
                    self.stdscr.addstr(1,0, err.__str__())
                    self.stdscr.addstr(4,0, 'Press any key.')
                    self.stdscr.refresh()
                    self.stdscr.getch()
                    self.stdscr.clear()
                    self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                       color_pair(2))
                    self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                       self.cur_dir)
                    self.stdscr.refresh()
                    self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                    self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                      e_offset)
                    continue
                changed = True
                self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                  e_offset)
            elif c == ord('y'):
                if cur_root.children:
                    self.stdscr.clear()
                    self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                       color_pair(2))
                    self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                       self.cur_dir)
                    self.stdscr.addstr(1,0, 'At least one of the following attributes must be given. Press any key.')
                    self.stdscr.refresh()
                    self.stdscr.getch()
                    title = self.get_string('', 'Title: ')
                    url = self.get_string('', 'URL: ')
                    username = self.get_string('', 'Username: ')
                    password = self.get_password('Password: ', False)
                    if password != '':
                        confirm = self.get_password('Confirm: ', False)
                    else:
                        confirm = ''

                    if password != confirm:
                        self.stdscr.clear()
                        self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                           color_pair(2))
                        self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                           self.cur_dir)
                        self.stdscr.addstr(1,0, 'Passwords didn\'t match. Will not set this attribute. Press any key.')
                        self.stdscr.refresh()
                        self.stdscr.getch()
                        password = ''
                    comment = self.get_string('', 'Comment: ')
                    
                    self.stdscr.clear()
                    self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                       color_pair(2))
                    self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                       self.cur_dir)
                    self.stdscr.addstr(1,0, 'Set expiration date? [y/(n)]')
                    self.stdscr.refresh()
                    e = self.stdscr.getch()

                    if e == ord('y'):
                        edit = ''
                        e = KEY_BACKSPACE
                        while e != NL:
                            if e == KEY_BACKSPACE and len(edit) != 0:
                                edit = edit[:-1]
                            elif e == KEY_BACKSPACE:
                                pass
                            elif len(edit) < 4 and e >= 48 and e <= 57:
                                edit += chr(e)
                            self.stdscr.clear()
                            self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                               color_pair(2))
                            self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                               self.cur_dir)
                            self.stdscr.addstr(1,0, 'Special date 2999-12-28 means that the entry expires never.')
                            self.stdscr.addstr(3,0, 'Year: ')
                            self.stdscr.addstr(3,6, edit)
                            self.stdscr.refresh()
                            e = self.stdscr.getch()
                        y = int(edit)
                            
                        edit = ''
                        e = KEY_BACKSPACE
                        while e != NL:
                            if e == KEY_BACKSPACE and len(edit) != 0:
                                edit = edit[:-1]
                            elif e == KEY_BACKSPACE:
                                pass
                            elif len(edit) < 2 and e >= 48 and e <= 57:
                                edit += chr(e)
                            self.stdscr.clear()
                            self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                               color_pair(2))
                            self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                               self.cur_dir)
                            self.stdscr.addstr(1,0, 'Special date 2999-12-28 means that the entry expires never.')
                            self.stdscr.addstr(3,0, 'Year: '+str(y))
                            self.stdscr.addstr(4,0, 'Month: ')
                            self.stdscr.addstr(4,7, edit)
                            self.stdscr.refresh()
                            e = self.stdscr.getch()

                            if e == NL and (int(edit) > 12 or int(edit) < 1):
                                self.stdscr.clear()
                                self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                                   color_pair(2))
                                self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                                   self.cur_dir)
                                self.stdscr.addstr(1,0, 'Month must be between 1 and 12. Press any key.')
                                self.stdscr.getch()
                                e = ''
                        mon = int(edit)

                        edit = ''
                        e = KEY_BACKSPACE
                        while e != NL:
                            if e == KEY_BACKSPACE and len(edit) != 0:
                                edit = edit[:-1]
                            elif e == KEY_BACKSPACE:
                                pass
                            elif len(edit) < 2 and e >= 48 and e <= 57:
                                edit += chr(e)
                            self.stdscr.clear()
                            self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                               color_pair(2))
                            self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                               self.cur_dir)
                            self.stdscr.addstr(1,0, 'Special date 2999-12-28 means that the entry expires never.')
                            self.stdscr.addstr(3,0, 'Year: '+str(y))
                            self.stdscr.addstr(4,0, 'Month: '+str(mon))
                            self.stdscr.addstr(5,0, 'Day: ')
                            self.stdscr.addstr(5,5, edit)
                            self.stdscr.refresh()
                            e = self.stdscr.getch()
                           
                            if e == NL and (mon == 1 or mon == 3 or mon == 5 or mon == 7 or mon == 8 or mon == 10 or mon == 12) \
                                and (int(edit) > 31 or int(edit) < 0):
                                self.stdscr.clear()
                                self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                                   color_pair(2))
                                self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                                   self.cur_dir)
                                self.stdscr.addstr(1,0, 'Day must be between 1 and 31. Press any key.')
                                self.stdscr.refresh()
                                self.stdscr.getch()
                                e = ''
                            elif e == NL and mon == 2 \
                                and (int(edit) > 28 or int(edit) < 0):
                                self.stdscr.clear()
                                self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                                   color_pair(2))
                                self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                                   self.cur_dir)
                                self.stdscr.addstr(1,0, 'Day must be between 1 and 28. Press any key.')
                                self.stdscr.refresh()
                                self.stdscr.getch()
                                e = ''
                            elif e == NL and (mon == 4 or mon == 6 or mon == 9 or mon == 11) \
                                and (int(edit) > 30 or int(edit) < 0):
                                self.stdscr.clear()
                                self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                                   color_pair(2))
                                self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                                   self.cur_dir)
                                self.stdscr.addstr(1,0, 'Day must be between 1 and 30. Press any key.')
                                self.stdscr.refresh()
                                self.stdscr.getch()
                                e = ''
                        d = int(edit)
                    else:
                        y = 2999
                        mon = 12
                        d = 28

                    try:
                        cur_root.children[g_highlight].create_entry(title, 1, url, username, password, comment, y, mon, d)
                    except KPError as err:
                        self.stdscr.clear()
                        self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                           color_pair(2))
                        self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                           self.cur_dir)
                        self.stdscr.addstr(1,0, err.__str__())
                        self.stdscr.addstr(4,0, 'Press any key.')
                        self.stdscr.refresh()
                        self.stdscr.getch()
                    self.stdscr.clear()
                    self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                       color_pair(2))
                    self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                       self.cur_dir)
                    self.stdscr.refresh()
                    self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                    self.show_entries(g_highlight, e_highlight, cur_root, cur_win, e_offset)
            elif c == ord('d'):
                if cur_win == 0 and cur_root.children:
                    self.stdscr.clear()
                    self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                       color_pair(2))
                    self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                       self.cur_dir)
                    self.stdscr.addstr(1,0, 'Really delete group '+cur_root.children[g_highlight].title+'? [y/(n)]')
                    self.stdscr.refresh()
                    e = self.stdscr.getch()
                    if not e == ord('y'):
                        self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                        self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                          e_offset)
                        continue
                    try:
                        cur_root.children[g_highlight].remove_group()
                    except KPError as err:
                        self.stdscr.clear()
                        self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                           color_pair(2))
                        self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                           self.cur_dir)
                        self.stdscr.addstr(1,0, err.__str__())
                        self.stdscr.addstr(4,0, 'Press any key.')
                        self.stdscr.refresh()
                        self.stdscr.getch()
                        self.stdscr.clear()
                        self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                           color_pair(2))
                        self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                           self.cur_dir)
                        self.stdscr.refresh()
                        self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                        self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                          e_offset)
                        continue

                    changed = True
                    self.stdscr.clear()
                    self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                       color_pair(2))
                    self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'),
                                       self.cur_dir)
                    self.stdscr.refresh()

                    if g_highlight >= len(cur_root.children) and g_highlight != 0:
                        g_highlight -= 1
                    self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                    e_highlight = 0
                    self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                      e_offset)
                elif cur_win == 1 and cur_root.children:
                    if not cur_root.children[g_highlight].entries:
                        continue
                    self.stdscr.clear()
                    self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                       color_pair(2))
                    self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                       self.cur_dir)
                    self.stdscr.addstr(1,0, 'Really delete entry '+cur_root.children[g_highlight].entries[e_highlight].title+'? [y/(n)]')
                    self.stdscr.refresh()
                    e = self.stdscr.getch()
                    if not e == ord('y'):
                        self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                        self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                          e_offset)
                        continue
                    try:
                        cur_root.children[g_highlight].entries[e_highlight].remove_entry()
                    except KPError as err:
                        self.stdscr.clear()
                        self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                           color_pair(2))
                        self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                           self.cur_dir)
                        self.stdscr.addstr(1,0, err.__str__())
                        self.stdscr.addstr(4,0, 'Press any key.')
                        self.stdscr.refresh()
                        self.stdscr.getch()
                        self.stdscr.clear()
                        self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                           color_pair(2))
                        self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                           self.cur_dir)
                        self.stdscr.refresh()
                        self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                        self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                          e_offset)
                        continue

                    changed = True
                    self.stdscr.clear()
                    self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                       color_pair(2))
                    self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'),
                                       self.cur_dir)
                    self.stdscr.refresh()

                    if e_highlight >= len(cur_root.children[g_highlight].entries) \
                        and e_highlight != 0:
                        e_highlight -= 1
                    self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                      e_offset)
            # Edit attributes
            elif c == ord('t') or c == ord('u') or c == ord('U') or c == ord('C'):
                if cur_root.children:
                    if not cur_root.children[g_highlight].entries and cur_win == 1:
                        continue
                    self.stdscr.clear()
                    self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                       color_pair(2))
                    self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                       self.cur_dir)
                    if c == ord('t'):
                        std = 'Title: '
                        if cur_win == 0:
                            edit= cur_root.children[g_highlight].title
                        elif cur_win == 1:
                            edit = cur_root.children[g_highlight].entries[e_highlight].title
                    elif c == ord('u') and cur_root.children[g_highlight].entries:
                        std = 'Username: '
                        edit = cur_root.children[g_highlight].entries[e_highlight].username
                    elif c == ord('U') and cur_root.children[g_highlight].entries:
                        std = 'URL: '
                        edit = cur_root.children[g_highlight].entries[e_highlight].url
                    elif c == ord('C') and cur_root.children[g_highlight].entries:
                        std = 'Comment: '
                        edit = cur_root.children[g_highlight].entries[e_highlight].comment
                    else:
                        continue
                    offset = len(std)

                    edit = self.get_string(edit, std)

                    self.stdscr.clear()
                    self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                       color_pair(2))
                    self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'),
                                       self.cur_dir)
                    self.stdscr.refresh()
                    changed = True

                    if c == ord('t'):
                        if cur_win == 0:
                            cur_root.children[g_highlight].set_title(edit)
                            self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                            self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                              e_offset)
                        elif cur_win == 1:
                            cur_root.children[g_highlight].entries[e_highlight].set_title(edit)
                            self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                            self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                              e_offset)
                    elif c == ord('u'):
                        cur_root.children[g_highlight].entries[e_highlight].set_username(edit)
                        self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                        self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                          e_offset)
                    elif c == ord('U'):
                        cur_root.children[g_highlight].entries[e_highlight].set_url(edit)
                        self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                        self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                          e_offset)
                    elif c == ord('C'):
                        cur_root.children[g_highlight].entries[e_highlight].set_comment(edit)
                        self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                        self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                          e_offset)
            elif c == ord('p'):
                if cur_root.children:
                    if not cur_root.children[g_highlight].entries:
                        continue
                    password = self.get_password('Password: ')
                    confirm = self.get_password('Confirm: ')
                    
                    if password == confirm:
                        cur_root.children[g_highlight].entries[e_highlight].set_password(password)
                        changed = True
                    else:
                        self.stdscr.addstr(3,0, 'Passwords didn\'t match. Press any key.')
                        e = self.stdscr.getch()

                    self.stdscr.clear()
                    self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                       color_pair(2))
                    self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'),
                                       self.cur_dir)
                    self.stdscr.refresh()

                    self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                    self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                      e_offset)
            elif c == ord('E'):
                if cur_root.children:
                    if not cur_root.children[g_highlight].entries:
                        continue
                    exp = cur_root.children[g_highlight].entries[e_highlight].expire.timetuple()
                    self.stdscr.clear()
                    self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                       color_pair(2))
                    self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'),
                                       self.cur_dir)

                    edit = ''
                    e = KEY_BACKSPACE
                    while e != NL:
                        if e == KEY_BACKSPACE and len(edit) != 0:
                            edit = edit[:-1]
                        elif e == KEY_BACKSPACE:
                            pass
                        elif len(edit) < 4 and e >= 48 and e <= 57:
                            edit += chr(e)
                        self.stdscr.clear()
                        self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                           color_pair(2))
                        self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                           self.cur_dir)
                        self.stdscr.addstr(1,0, 'Special date 2999-12-28 means that the entry expires never.')
                        self.stdscr.addstr(2,0, 'Actual expiration date: '+str(exp[0])+'-'+str(exp[1])+'-'+str(exp[2]))
                        self.stdscr.addstr(3,0, 'Year: ')
                        self.stdscr.addstr(3,6, edit)
                        self.stdscr.refresh()
                        e = self.stdscr.getch()
                    y = int(edit)
                        
                    edit = ''
                    e = KEY_BACKSPACE
                    while e != NL:
                        if e == KEY_BACKSPACE and len(edit) != 0:
                            edit = edit[:-1]
                        elif e == KEY_BACKSPACE:
                            pass
                        elif len(edit) < 2 and e >= 48 and e <= 57:
                            edit += chr(e)
                        self.stdscr.clear()
                        self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                           color_pair(2))
                        self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                           self.cur_dir)
                        self.stdscr.addstr(1,0, 'Special date 2999-12-28 means that the entry expires never.')
                        self.stdscr.addstr(2,0, 'Actual expiration date: '+str(exp[0])+'-'+str(exp[1])+'-'+str(exp[2]))
                        self.stdscr.addstr(3,0, 'Year: '+str(y))
                        self.stdscr.addstr(4,0, 'Month: ')
                        self.stdscr.addstr(4,7, edit)
                        self.stdscr.refresh()
                        e = self.stdscr.getch()

                        if e == NL and (int(edit) > 12 or int(edit) < 1):
                            self.stdscr.clear()
                            self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                               color_pair(2))
                            self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                               self.cur_dir)
                            self.stdscr.addstr(1,0, 'Month must be between 1 and 12. Press any key.')
                            self.stdscr.getch()
                            e = ''
                    mon = int(edit)

                    edit = ''
                    e = KEY_BACKSPACE
                    while e != NL:
                        if e == KEY_BACKSPACE and len(edit) != 0:
                            edit = edit[:-1]
                        elif e == KEY_BACKSPACE:
                            pass
                        elif len(edit) < 2 and e >= 48 and e <= 57:
                            edit += chr(e)
                        self.stdscr.clear()
                        self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                           color_pair(2))
                        self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                           self.cur_dir)
                        self.stdscr.addstr(1,0, 'Special date 2999-12-28 means that the entry expires never.')
                        self.stdscr.addstr(2,0, 'Actual expiration date: '+str(exp[0])+'-'+str(exp[1])+'-'+str(exp[2]))
                        self.stdscr.addstr(3,0, 'Year: '+str(y))
                        self.stdscr.addstr(4,0, 'Month: '+str(mon))
                        self.stdscr.addstr(5,0, 'Day: ')
                        self.stdscr.addstr(5,5, edit)
                        self.stdscr.refresh()
                        e = self.stdscr.getch()
                       
                        if e == NL and (mon == 1 or mon == 3 or mon == 5 or mon == 7 or mon == 8 or mon == 10 or mon == 12) \
                            and (int(edit) > 31 or int(edit) < 0):
                            self.stdscr.clear()
                            self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                               color_pair(2))
                            self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                               self.cur_dir)
                            self.stdscr.addstr(1,0, 'Day must be between 1 and 31. Press any key.')
                            self.stdscr.refresh()
                            self.stdscr.getch()
                            e = ''
                        elif e == NL and mon == 2 \
                            and (int(edit) > 28 or int(edit) < 0):
                            self.stdscr.clear()
                            self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                               color_pair(2))
                            self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                               self.cur_dir)
                            self.stdscr.addstr(1,0, 'Day must be between 1 and 28. Press any key.')
                            self.stdscr.refresh()
                            self.stdscr.getch()
                            e = ''
                        elif e == NL and (mon == 4 or mon == 6 or mon == 9 or mon == 11) \
                            and (int(edit) > 30 or int(edit) < 0):
                            self.stdscr.clear()
                            self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                               color_pair(2))
                            self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                               self.cur_dir)
                            self.stdscr.addstr(1,0, 'Day must be between 1 and 30. Press any key.')
                            self.stdscr.refresh()
                            self.stdscr.getch()
                            e = ''
                    d = int(edit)

                    self.stdscr.clear()
                    self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                       color_pair(2))
                    self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'),
                                       self.cur_dir)
                    self.stdscr.refresh()
                    cur_root.children[g_highlight].entries[e_highlight].set_expire(y, mon, d, 
                        exp[3], exp[4], exp[5])
                    changed = True
                    self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                    self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                      e_offset)
            # Navigation
            elif c == KEY_DOWN:
                if cur_win == 0:
                    if g_highlight >= len(cur_root.children)-1:
                        continue
                    ysize = self.group_win.getmaxyx()[0]
                    if g_highlight >= ysize-4 and \
                        not g_offset >= len(cur_root.children)-ysize+4:
                        g_offset += 1
                    g_highlight += 1
                    self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                    e_highlight = 0
                    self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                      e_offset)
                elif cur_win == 1:
                    if e_highlight >= len(cur_root.children[g_highlight].entries)-1:
                        continue
                    ysize = self.entry_win.getmaxyx()[0]
                    if e_highlight >= ysize-4 and \
                        not e_offset >= len(cur_root.children[g_highlight].entries)-ysize+3:
                        e_offset += 1
                    e_highlight += 1
                    self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                      e_offset)
            elif c == KEY_UP:
                if cur_win == 0:
                    if g_highlight <= 0:
                        continue
                    ysize = self.group_win.getmaxyx()[0]
                    if g_highlight <= len(cur_root.children)-ysize+4 and \
                        not g_offset <= 0:
                        g_offset -= 1
                    g_highlight -= 1
                    self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                    e_highlight = 0
                    self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                      e_offset)
                elif cur_win == 1:
                    if e_highlight <= 0:
                        continue
                    ysize = self.entry_win.getmaxyx()[0]
                    if e_highlight <= len(cur_root.children[g_highlight].entries)-ysize+6 and \
                        not e_offset <= 0:
                        e_offset -= 1
                    e_highlight -= 1
                    self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                      e_offset)
            elif c == KEY_LEFT:
                cur_win = 0
                self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                  e_offset)
            elif c == KEY_RIGHT:
                if cur_root.children[g_highlight].entries:
                    cur_win = 1
                    self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                    self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                      e_offset)
            elif c == KEY_RESIZE:
                self.term_size = self.stdscr.getmaxyx()
                self.group_win.resize(self.term_size[0]-1, int(self.term_size[1]/3))
                self.entry_win.resize(2*int((self.term_size[0]-1)/3),
                                      2*int(self.term_size[1]/3)-2)
                self.info_win.resize(int((self.term_size[0]-1)/3)-1,
                                     int(self.term_size[1]/3)-2)
                self.group_win.mvwin(1,0)
                self.entry_win.mvwin(1, int(self.term_size[0]/3)+2)
                self.info_win.mvwin(2*int((self.term_size[0]-1)/3)+1,
                                    int(self.term_size[0]/3)+2)
                self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                  e_offset)
            elif c == NL:
                if cur_root.children[g_highlight].children:
                    cur_root = cur_root.children[g_highlight]
                    g_highlight = 0
                    e_highlight = 0
                    cur_win = 0
                    self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                    self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                      e_offset)
            elif c == KEY_BACKSPACE:
                if not cur_root is self.db._root_group:
                    cur_root = cur_root.parent
                    g_highlight = 0
                    e_highlight = 0
                    cur_win = 0
                    self.show_groups(g_highlight, cur_root, cur_win, g_offset)
                    self.show_entries(g_highlight, e_highlight, cur_root, cur_win,
                                      e_offset)
                    
    def show_groups(self, highlight, root, cur_win, offset):
        self.group_win.clear()
        if root is  self.db._root_group:
            root_title = 'Parent: _ROOT_'
        else:
            root_title = 'Parent: '+root.title
        if cur_win == 0:
            h_color = 5
            n_color = 4
        else:
            h_color = 6
            n_color = 1

        ysize = self.group_win.getmaxyx()[0]
        self.group_win.addnstr(0,0, root_title, ysize,
                               color_pair(n_color))

        if root.children:
            groups = root.children

            if len(groups) <= ysize-3:
                num = len(groups)
            else:
                num = ysize-3
                
            for i in range(num):
                if highlight == i+offset:
                    if groups[i].children:
                        title = '+'+groups[i+offset].title
                    else:
                        title = ' '+groups[i+offset].title
                    self.group_win.addnstr(i+1, 0, title, ysize,
                                          color_pair(h_color))
                else:
                    if groups[i].children:
                        title = '+'+groups[i+offset].title
                    else:
                        title = ' '+groups[i+offset].title
                    self.group_win.addnstr(i+1, 0, title, ysize,
                                          color_pair(n_color))
            self.group_win.addnstr(ysize-2,0, str(highlight+1)+' of '+str(len(groups)),
                                   ysize)
        self.group_win.noutrefresh()

    def show_entries(self, g_highlight, e_highlight, root, cur_win, offset):
        self.entry_win.clear()
        if root.children:
            entries = root.children[g_highlight].entries
            if entries:
                if cur_win == 1:
                    h_color = 5
                    n_color = 4
                else:
                    h_color = 6
                    n_color = 1

                ysize = self.entry_win.getmaxyx()[0]
                if len(entries) <= ysize-3:
                    num = len(entries)
                else:
                    num = ysize-3
                    
                for i in range(num):
                    if e_highlight == i+offset:
                        self.entry_win.addnstr(i, 0, entries[i+offset].title, ysize,
                                               color_pair(h_color))
                    else:
                        self.entry_win.addnstr(i, 0, entries[i+offset].title, ysize,
                                               color_pair(n_color))
                self.entry_win.addnstr(ysize-2, 0, str(e_highlight+1)+' of '+str(len(entries)),
                                       ysize)
        self.entry_win.noutrefresh()

        self.info_win.clear()
        if root.children:
            if entries:
                entry = entries[e_highlight]
                self.info_win.addnstr(0,0, entry.title, ysize, A_BOLD)
                self.info_win.addnstr(1,0, "Group: "+entry.title, ysize)
                self.info_win.addnstr(2,0, "Username: "+entry.username, ysize)
                self.info_win.addnstr(3,0, "URL: "+entry.url, ysize)
                self.info_win.addnstr(4,0, "Creation: "+entry.creation.__str__()[:10],
                                      ysize)
                self.info_win.addnstr(5,0, "Access: "+entry.last_access.__str__()[:10],
                                      ysize)
                self.info_win.addnstr(6,0, "Modification: "+entry.last_mod.__str__()[:10],
                                      ysize)
                if entry.expire.__str__()[:19] == '2999-12-28 23:59:59':
                    self.info_win.addnstr(7,0, "Expiration: Never",
                                          ysize)
                else:
                    self.info_win.addnstr(7,0, "Expiration: "+entry.expire.__str__()[:10],
                                          ysize)
                    if date.today() > entry.expire.date():
                        self.info_win.addnstr(7,22, ' (expired)', ysize)
                self.info_win.addnstr(8,0, "Comment: "+entry.comment, ysize)
        self.info_win.noutrefresh()
        doupdate()
        
if __name__ == '__main__':
    if len(argv) > 1:
        print('Usage: keepassc')
        print('Type \'h\' while running the program to get help.')
    else:
        app = App()
        app.main_loop()

