#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (C) 2012 Karsten-Kai König <kkoenig@posteo.de>

This file is part of xxx.

xxx is free software: you can redistribute it and/or modify it under the terms
of the GNU General Public License as published by the Free Software Foundation,
either version 3 of the License, or at your option) any later version.

xxx is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
xxx.  If not, see <http://www.gnu.org/licenses/>.
'''

from curses import *
from curses.ascii import NL
from os import *
from os.path import isdir
from socket import gethostname
from sys import exit

from kppy import *

class App(object):
    def __init__(self):
        self.stdscr = initscr()
        curs_set(0)
        cbreak()
        noecho()
        self.stdscr.keypad(1)
        start_color()
        init_pair(1, 7, 0)
        init_pair(2, 2, 0)
        init_pair(3, 0, 1)
        init_pair(4, 4, 0)
        init_pair(5, 0, 4)
        self.stdscr.bkgd(1)

        self.loginname = getlogin()
        self.hostname = gethostname()
        self.cur_dir = getcwd()
        chdir('/var/empty')

        self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', color_pair(2))
        self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), self.cur_dir)

        self.main_loop()

    def main_loop(self):
        self.open_db()

    def open_db(self):
        while True:
            filepath = self.browser()
            
            if filepath is False:
                continue
            else:
                self.stdscr.erase()
                self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', color_pair(2))
                self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                   self.cur_dir)
                self.stdscr.addstr(1,0, 'Password: ')
                self.stdscr.refresh()
                c = ''
                password = ''
                while c != NL:
                    c = self.stdscr.getch()
                    if c > 255 or c < 0:
                        continue
                    password += chr(c)
                
                try:
                    self.db = KPDB(filepath, password)
                except KPError as err:
                    self.stdscr.erase()
                    self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', color_pair(2))
                    self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                                       self.cur_dir)
                    self.stdscr.addstr(1,0, err.__str__())
                    self.stdscr.addstr(4,0, 'Press any key.')
                    self.stdscr.refresh()
                    self.stdscr.getch()
                    continue
                break

    def browser(self):
        self.stdscr.erase()
        self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', color_pair(2))
        self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                           self.cur_dir)
        self.stdscr.refresh()
        try:
            dir_cont = listdir(self.cur_dir)
        except OSError:
            self.stdscr.erase()
            self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', color_pair(2))
            self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                               self.cur_dir)
            self.stdscr.addstr(1,0, 'Was not able to read directory.')
            self.stdscr.addstr(2,0, 'Press any key.')
            self.stdscr.refresh()
            self.stdscr.getch()
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
                return False
            elif c == NL or c == KEY_RIGHT:
                if dir_cont[highlight] == '..':
                    last = self.cur_dir.split('/')[-1]
                    self.cur_dir = self.cur_dir[:-len(last)-1]
                    if self.cur_dir == '': self.cur_dir = '/';
                    return False
                elif isdir(self.cur_dir+'/'+dir_cont[highlight]):
                    self.cur_dir = self.cur_dir+'/'+dir_cont[highlight]
                    if self.cur_dir[:2] == '//':
                        self.cur_dir = self.cur_dir[1:]
                    return False
                else:
                    return self.cur_dir+'/'+dir_cont[highlight]
            elif c == ord('q'):
                self.close()

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

if __name__ == '__main__':
    app = App()
