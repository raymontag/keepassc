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
        init_pair(1, 7, 0)
        init_pair(2, 2, 0)
        init_pair(3, 0, 1)
        init_pair(4, 6, 0)
        init_pair(5, 0, 6)
        init_pair(6, 0, 7)
        self.stdscr.bkgd(1)

        self.loginname = getlogin()
        self.hostname = gethostname()
        self.cur_dir = getcwd()
        chdir('/var/empty')

        self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                           color_pair(2))
        self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                           self.cur_dir)

        self.term_size = self.stdscr.getmaxyx()
        self.db = None

    def main_loop(self):
        while True:
            self.stdscr.addstr(1,0, 'To open an existing database type \'o\',')
            self.stdscr.addstr(2,0, 'to create a new one type \'n\'.')
            self.stdscr.addstr(4,0, 'Type \'q\' to quit.')
            self.stdscr.refresh()

            c = self.stdscr.getch()
            if c == ord('o'):
                self.open_db()
                self.db_browser()
            elif c == ord('n'):
                pass
            elif c == ord('q'):
                self.close()

    def open_db(self):
        while True:
            filepath = self.browser()
            
            if filepath is False:
                continue
            else:
                self.stdscr.erase()
                self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                   color_pair(2))
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
                
                password = password[:-1]

                try:
                    self.db = KPDB(filepath, password)
                except KPError as err:
                    self.stdscr.erase()
                    self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                                       color_pair(2))
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
        self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':',  
                           color_pair(2))
        self.stdscr.addstr(0, len(self.loginname+'@'+self.hostname+':'), 
                           self.cur_dir)
        self.stdscr.refresh()

        try:
            dir_cont = listdir(self.cur_dir)
        except OSError:
            self.stdscr.erase()
            self.stdscr.addstr(0,0, self.loginname+'@'+self.hostname+':', 
                               color_pair(2))
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

    def db_browser(self):
        self.group_win = newwin(self.term_size[0]-1, int(self.term_size[1]/3), 
                                1, 0)
        self.entry_win = newwin(2*int((self.term_size[0]-1)/3), 
                                2*int(self.term_size[1]/3)-2, 
                                1, int(self.term_size[0]/3)+2)
        self.info_win = newwin(int((self.term_size[0]-1)/3)-1,
                               int(self.term_size[1]/3)-2,
                               2*int((self.term_size[0]-1)/3)+1,
                               int(self.term_size[0]/3)+2)
        self.group_win.keypad(1)
        self.entry_win.keypad(1)
        self.group_win.bkgd(1)
        self.entry_win.bkgd(1)
        self.info_win.bkgd(1)

        cur_root = self.db._root_group
        cur_win = 0
        g_highlight = 0
        e_highlight = 0

        self.show_groups(g_highlight, cur_root, cur_win)
        self.show_entries(g_highlight, e_highlight, cur_root, cur_win)

        while True:
            c = self.group_win.getch()

            if c == ord('e'):
                self.db.close()
                self.group_win.erase()
                self.entry_win.erase()
                self.group_win.refresh()
                self.entry_win.refresh()
                break
            elif c == ord('q'):
                self.db.close()
                self.close()
            elif c == KEY_DOWN:
                if cur_win == 0:
                    if g_highlight >= len(cur_root.children)-1:
                        continue
                    g_highlight += 1
                    self.show_groups(g_highlight, cur_root, cur_win)
                    e_highlight = 0
                    self.show_entries(g_highlight, e_highlight, cur_root, cur_win)
                elif cur_win == 1:
                    if e_highlight >= len(cur_root.children[g_highlight].entries):
                        continue
                    e_highlight += 1
                    self.show_entries(g_highlight, e_highlight, cur_root, cur_win)
            elif c == KEY_UP:
                if cur_win == 0:
                    if g_highlight <= 0:
                        continue
                    g_highlight -= 1
                    self.show_groups(g_highlight, cur_root, cur_win)
                    e_highlight = 0
                    self.show_entries(g_highlight, e_highlight, cur_root, cur_win)
                elif cur_win == 1:
                    if e_highlight <= 0:
                        continue
                    e_highlight -= 1
                    self.show_entries(g_highlight, e_highlight, cur_root, cur_win)
            elif c == KEY_LEFT:
                cur_win = 0
                self.show_groups(g_highlight, cur_root, cur_win)
                self.show_entries(g_highlight, e_highlight, cur_root, cur_win)
            elif c == KEY_RIGHT:
                cur_win = 1
                self.show_groups(g_highlight, cur_root, cur_win)
                self.show_entries(g_highlight, e_highlight, cur_root, cur_win)
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
                self.show_groups(g_highlight, cur_root, cur_win)
                self.show_entries(g_highlight, e_highlight, cur_root, cur_win)

    def show_groups(self, highlight, root, cur_win):
        self.group_win.erase()
        groups = root.children
        if cur_win == 0:
            h_color = 5
            n_color = 4
        else:
            h_color = 6
            n_color = 1
        ysize = self.group_win.getmaxyx()[0]
        for i in range(len(groups)):
            if highlight == i:
                if groups[i].children:
                    title = '+'+groups[i].title
                else:
                    title = ' '+groups[i].title
                self.group_win.addnstr(i, 0, title, ysize,
                                      color_pair(h_color))
            else:
                if groups[i].children:
                    title = '+'+groups[i].title
                else:
                    title = ' '+groups[i].title
                self.group_win.addnstr(i, 0, title, ysize,
                                      color_pair(n_color))
        self.group_win.refresh()

    def show_entries(self, g_highlight, e_highlight, root, cur_win):
        self.entry_win.erase()
        entries = root.children[g_highlight].entries
        ysize = self.entry_win.getmaxyx()[0]
        if cur_win == 1:
            h_color = 5
            n_color = 4
        else:
            h_color = 6
            n_color = 1
        for i in range(len(entries)):
            if e_highlight == i:
                self.entry_win.addnstr(i, 0, entries[i].title, ysize,
                                      color_pair(h_color))
            else:
                self.entry_win.addnstr(i, 0, entries[i].title, ysize,
                                      color_pair(n_color))
        self.entry_win.refresh()

        self.info_win.erase()
        entry = entries[e_highlight]
        self.info_win.addnstr(0,0, entry.title, ysize, A_BOLD)
        self.info_win.addnstr(1,0, "Group: "+entry.title, ysize)
        self.info_win.addnstr(2,0, "URL: "+entry.url, ysize)
        self.info_win.addnstr(3,0, "Creation: "+entry.creation.__str__(), ysize)
        self.info_win.addnstr(4,0, "Access: "+entry.last_access.__str__(), ysize)
        self.info_win.addnstr(5,0, "Modification: "+entry.last_mod.__str__(), ysize)
        self.info_win.addnstr(6,0, "Expiration: "+entry.expire.__str__(), ysize)
        self.info_win.addnstr(7,0, "Comment: "+entry.comment, ysize)
        self.info_win.refresh()
        
if __name__ == '__main__':
    if len(argv) > 1:
        if argv[1] == '--help' or argv[1] == '-h':
            pass
        else:
            print('Type \'xxx -h\'')
    else:
        app = App()
        app.main_loop()

