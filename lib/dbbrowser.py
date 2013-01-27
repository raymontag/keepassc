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
import threading
import webbrowser
from curses.ascii import NL, DEL, SP
from os import makedirs, remove
from os.path import isfile, isdir
from random import sample
from subprocess import Popen, PIPE


class DBBrowser(object):
    def __init(self, control):
        if control.cur_dir[-4:] == '.kdb':
            if not isdir(control.last_home[:-5]):
                if isfile(control.last_home[:-5]):
                    remove(control.last_home[:-5])
                makedirs(control.last_home[:-5])
            handler = open(control.last_home, 'w')
            handler.write(control.cur_dir)
            handler.close()
        self.db_browser(control)

    def save(self, cur_dir):
        '''Save the database. cur_dir is the current directory.'''
        self.draw_text(False,
                       (1, 0, 'Do not interrupt or '
                        'your file will break!'))
        try:
            if cur_dir is False:
                self.db.save()
            else:
                self.db.save(cur_dir)
        except KPError as err:
            self.draw_text(False,
                           (1, 0, err.__str__()),
                           (4, 0, 'Press any key.'))
            self.any_key()
            return False

    def db_close(self):
        '''Close the database correctly.'''

        if self.db.filepath is not None:
            try:
                self.db.close()
            except KPError as err:
                self.draw_text(False,
                               (1, 0, err.__str__()),
                               (4, 0, 'Press any key.'))
                self.any_key()
        self.db = None

    def db_browser(self, control):
        '''The database browser.'''

        hide = True
        changed = False
        cur_win = 0
        g_highlight = 0
        e_highlight = 0
        g_offset = 0
        e_offset = 0
        self.cur_root = self.db._root_group
        groups = sorted(self.cur_root.children,
                        key=lambda group: group.title.lower())
        entries = []
        if groups and groups[g_highlight].entries:
            entries = sorted(groups[g_highlight].entries,
                             key=lambda entry: entry.title.lower())
        else:
            entries = []

        self.show_groups(g_highlight, groups, cur_win, g_offset,
                         changed)
        self.show_entries(e_highlight, entries, cur_win, e_offset,
                          hide)

class UnlockedDB(object):
    while True:
        try:
            c = self.stdscr.getch()
        except KeyboardInterrupt:
            c = 4
        if self.config['lock_db']:
            self.lock_timer.cancel()

        if c == ord('\t'):
            if cur_win == 0:
                c = cur.KEY_RIGHT
            else:
                c = cur.KEY_LEFT

        if c == cur.KEY_F1:
            cur.noraw()
            self.stdscr.keypad(0)
            cur.endwin()
            print('\'e\' - go to main menu')
            print('\'q\' - close program')
            print('\'x\' - save db and close program')
            print('\'s\' - save db')
            print('\'S\' - save db with alternative filepath')
            print('\'c\' - copy password of current entry')
            print('\'b\' - copy username of current entry')
            print('\'H\' - show password of current entry')
            print('\'o\' - open URL of entry in standard webbrowser')
            print('\'P\' - edit db password')
            print('\'g\' - create group')
            print('\'G\' - create subgroup')
            print('\'y\' - create entry')
            print('\'d\' - delete group or entry')
            print('\'t\' - edit title of selected group or entry')
            print('\'u\' - edit username')
            print('\'p\' - edit password')
            print('\'U\' - edit URL')
            print('\'C\' - edit comment')
            print('\'E\' - edit expiration date')
            print('\'f\' - find entry by title')
            print('\'L\' - lock db')
            print('Navigate with arrow keys or h/j/k/l like in vim')
            print('Type \'F5\' in a dialog to return to the previous one')
            print('Type \'return\' to enter subgroups')
            print('Type \'backspace\' to go back')
            try:
                input('Press return.')
            except EOFError:
                if not self.db is None:
                    self.db_close()
                exit()
            self.stdscr = cur.initscr()
            try:
                cur.curs_set(0)
            except:
                print('Invisible cursor not supported')
            cur.raw()
            cur.noecho()
            self.stdscr.keypad(1)
            cur.start_color()
            cur.use_default_colors()
            cur.init_pair(1, -1, -1)
            cur.init_pair(2, 2, -1)
            cur.init_pair(3, 0, 1)
            cur.init_pair(4, 6, -1)
            cur.init_pair(5, 0, 6)
            cur.init_pair(6, 0, 7)
            self.stdscr.bkgd(1)
            self.ysize, self.xsize = self.stdscr.getmaxyx()

            self.group_win = cur.newwin(self.ysize - 1, int(self.xsize / 3),
                                        1, 0)
            self.entry_win = cur.newwin(int(2 * (self.ysize - 1) / 3),
                                        int(2 * self.xsize / 3),
                                        1, int(self.xsize / 3))
            self.info_win = cur.newwin(int((self.ysize - 1) / 3) - 1,
                                       int(2 * self.xsize / 3),
                                       int(2 * (self.ysize - 1) / 3),
                                       int(self.xsize / 3))
            self.group_win.keypad(1)
            self.entry_win.keypad(1)
            self.group_win.bkgd(1)
            self.entry_win.bkgd(1)
            self.info_win.bkgd(1)

            self.draw_text(changed)
            self.show_groups(g_highlight, groups, cur_win, g_offset,
                             changed)
            self.show_entries(e_highlight, entries, cur_win, e_offset,
                              hide)
        # File operations
        elif c == ord('e'):
            if changed is True:
                self.draw_text(changed,
                               (1, 0, 'File has changed. Save? [(y)/n]'))
                no_exit = False
                while True:
                    try:
                        e = self.stdscr.getch()
                    except KeyboardInterrupt:
                        e = 4
                    if e == 4:
                        self.del_clipboard()
                        if self.db is not None:
                            self.db_close()
                        self.close()
                    elif e == -1:
                        self.del_clipboard()
                    elif e == cur.KEY_RESIZE:
                        self.resize_all()
                    elif e == cur.KEY_F5:
                        no_exit = True
                        break
                    elif e == ord('n'):
                        break
                    else:
                        if self.db.filepath is None:
                            filepath = self.get_filepath()
                            if filepath is not False:
                                self.cur_dir = filepath
                                self.save(self.cur_dir)
                        else:
                            self.save(False)
                        break
                if no_exit is True:
                    self.show_groups(
                        g_highlight, groups, cur_win, g_offset,
                        changed)
                    self.show_entries(e_highlight, entries, cur_win,
                                      e_offset, hide)
                    continue

            self.del_clipboard()
            self.db_close()
            self.group_win.clear()
            self.entry_win.clear()
            self.info_win.clear()
            self.group_win.noutrefresh()
            self.entry_win.noutrefresh()
            self.info_win.noutrefresh()
            cur.doupdate()
            break
        elif c == ord('q') or c == 4:
            self.del_clipboard()
            if changed is True:
                self.draw_text(
                    changed, (1, 0, 'File has changed. Save? [(y)/n]'))
                no_exit = False
                while True:
                    try:
                        e = self.stdscr.getch()
                    except KeyboardInterrupt:
                        e = 4
                    if e == 4:
                        self.del_clipboard()
                        if self.db is not None:
                            self.db_close()
                        self.close()
                    elif e == -1:
                        self.del_clipboard()
                    elif e == cur.KEY_RESIZE:
                        self.resize_all()
                    elif e == ord('n'):
                        break
                    elif e == cur.KEY_F5:
                        no_exit = True
                        break
                    else:
                        if self.db.filepath is None:
                            filepath = self.get_filepath()
                            if filepath is not False:
                                self.cur_dir = filepath
                                self.save(self.cur_dir)
                        else:
                            self.save(False)
                        break
                if no_exit is True:
                    self.show_groups(
                        g_highlight, groups, cur_win, g_offset,
                        changed)
                    self.show_entries(e_highlight, entries, cur_win,
                                      e_offset, hide)
                    continue
            self.db_close()
            self.close()
        elif c == ord('c'):
            if entries:
                entry = entries[e_highlight]
                if entry.password is not None:
                    try:
                        Popen(
                            ['xsel', '-pc'], stderr=PIPE, stdout=PIPE)
                        Popen(
                            ['xsel', '-bc'], stderr=PIPE, stdout=PIPE)
                        p = entry.password
                        (
                            Popen(
                                ['xsel', '-pi'], stdin=PIPE, stderr=PIPE,
                                stdout=PIPE).communicate(p.encode()))
                        (
                            Popen(
                                ['xsel', '-bi'], stdin=PIPE, stderr=PIPE,
                                stdout=PIPE).communicate(p.encode()))
                        if self.config['del_clip'] is True:
                            self.clip_timer = threading.Timer(self.config['clip_delay'],
                                            self.del_clipboard).start()
                    except FileNotFoundError as err:
                        self.draw_text(False,
                                       (1, 0, err.__str__()),
                                       (4, 0, 'Press any key.'))
                        self.any_key()
                    else:
                        self.cb = entry.password
                        self.del_cb = True
        elif c == ord('b'):
            if entries:
                entry = entries[e_highlight]
                if entry.username is not None:
                    try:
                        Popen(
                            ['xsel', '-pc'], stderr=PIPE, stdout=PIPE)
                        Popen(
                            ['xsel', '-bc'], stderr=PIPE, stdout=PIPE)
                        p = entry.username
                        (
                            Popen(
                                ['xsel', '-pi'], stdin=PIPE, stderr=PIPE,
                                stdout=PIPE).communicate(p.encode()))
                        (
                            Popen(
                                ['xsel', '-bi'], stdin=PIPE, stderr=PIPE,
                                stdout=PIPE).communicate(p.encode()))
                        threading.Timer(self.config['clip_delay'], 
                                        self.del_clipboard).start()
                    except FileNotFoundError as err:
                        self.draw_text(False,
                                       (1, 0, err.__str__()),
                                       (4, 0, 'Press any key.'))
                        self.any_key()
                    else:
                        self.cb = entry.username
        elif c == ord('o'):
            if entries:
                entry = entries[e_highlight]
                url = entry.url
                if url != '':
                    if url[:7] != 'http://' and url[:8] != 'https://':
                        url = 'http://' + url
                    webbrowser.open(url)
        elif c == -1:
            self.del_clipboard()
        elif c == ord('s'):
            if self.db.filepath is None:
                filepath = self.get_filepath()
                if filepath is not False:
                    self.cur_dir = filepath
            if self.save(self.cur_dir) is not False:
                changed = False
            self.show_groups(
                g_highlight, groups, cur_win, g_offset, changed)
            self.show_entries(e_highlight, entries, cur_win, e_offset,
                              hide)
        elif c == ord('S'):
            filepath = self.get_filepath(False)
            if filepath is not False:
                if self.db.filepath is None:
                    self.cur_dir = filepath
                if isfile(filepath):
                    self.draw_text(changed, (1, 0,
                                             'File exists. Overwrite? [y/(n)]'))
                    while True:
                        try:
                            c = self.stdscr.getch()
                        except KeyboardInterrupt:
                            c = 4
                        if c == ord('y'):
                            if self.save(filepath) is not False:
                                changed = False
                            break
                        elif c == 4:
                            self.del_clipboard()
                            if self.db is not None:
                                self.db_close()
                            self.close()
                        elif c == -1:
                            self.del_clipboard()
                        elif c == cur.KEY_RESIZE:
                            self.resize_all()
                        else:
                            break
                else:
                    if self.save(filepath) is not False:
                        changed = False
            self.show_groups(
                g_highlight, groups, cur_win, g_offset, changed)
            self.show_entries(e_highlight, entries, cur_win, e_offset,
                              hide)
            changed = False
        elif c == ord('x'):
            self.del_clipboard()
            if self.db.filepath is None:
                filepath = self.get_filepath()
                if filepath is not False:
                    self.cur_dir = filepath
                    if self.save(self.cur_dir) is not False:
                        self.db_close()
                        self.close()
            elif self.save(self.cur_dir) is not False:
                self.db_close()
                self.close()
            self.show_groups(
                g_highlight, groups, cur_win, g_offset, changed)
            self.show_entries(e_highlight, entries, cur_win, e_offset,
                              hide)
        elif c == ord('L'):
            if changed is True:
                self.draw_text(changed,
                               (1, 0, 'File has changed. Save? [(y)/n]'))
                no_lock = False
                while True:
                    try:
                        e = self.stdscr.getch()
                    except KeyboardInterrupt:
                        e = 4
                    if e == 4:
                        self.del_clipboard()
                        if self.db is not None:
                            self.db_close()
                        self.close()
                    elif e == -1:
                        self.del_clipboard()
                    elif e == cur.KEY_RESIZE:
                        self.resize_all()
                    elif e == cur.KEY_F5:
                        no_lock = True
                        break
                    elif e == ord('n'):
                        break
                    else:
                        if self.db.filepath is None:
                            filepath = self.get_filepath()
                            if filepath is not False:
                                self.cur_dir = filepath
                                self.save(self.cur_dir)
                                changed = False
                        else:
                            self.save(False)
                            changed = False
                        break
                if no_lock is True:
                    self.show_groups(
                        g_highlight, groups, cur_win, g_offset,
                        changed)
                    self.show_entries(e_highlight, entries, cur_win,
                                      e_offset, hide)
                    continue
            self.del_clipboard()
            if self.db.filepath is None:
                self.draw_text(changed,
                               (1, 0, 'Can only lock an existing db!'),
                               (4, 0, 'Press any key.'))
                self.any_key()
                continue
            self.db.lock()
            while True:
                auth = self.gen_menu((
                                     (1, 0, 'Use a password (1)'),
                                     (2, 0, 'Use a keyfile (2)'),
                                     (3, 0, 'Use both (3)')))
                if auth is False:
                    continue
                if auth == 1 or auth == 3:
                    password = self.get_password('Password: ')
                    if password is False:
                        continue
                    if auth != 3:
                        keyfile = None
                if auth == 2 or auth == 3:
                    while True:
                        keyfile = self.get_direct_filepath()
                        if keyfile is False:
                            break
                        elif not isfile(keyfile):
                            self.draw_text(changed,
                                           (1, 0, 'That\'s not a file'),
                                           (3, 0, 'Press any key.'))
                            self.any_key()
                            continue
                        break
                    if keyfile is False:
                        continue
                    if auth != 3:
                        password = None
                try:
                    self.db.unlock(password, keyfile)
                except KPError as err:
                    self.draw_text(changed,
                                   (1, 0, err.__str__()),
                                   (4, 0, 'Press any key.'))
                    self.any_key()
                else:
                    self.cur_root = self.db._root_group
                    groups = sorted(self.cur_root.children,
                                    key=lambda group: group.title.lower())
                    if groups and groups[g_highlight].entries:
                        entries = sorted(groups[g_highlight].entries,
                                         key=lambda entry:
                                         entry.title.lower())
                    else:
                        entries = []
                    self.show_groups(
                        g_highlight, groups, cur_win, g_offset,
                        changed)
                    self.show_entries(e_highlight, entries, cur_win,
                                      e_offset, hide)
                    break
        # DB editing
        elif c == ord('P'):
            while True:
                auth = self.gen_menu((
                                     (1, 0, 'Use a password (1)'),
                                     (2, 0, 'Use a keyfile (2)'),
                                     (3, 0, 'Use both (3)')))
                if auth == 2 or auth == 3:
                    while True:
                        filepath = self.get_filepath(False, True)
                        if not isfile(filepath):
                            self.draw_text(changed,
                                           (1, 0, "That's not a file!"),
                                           (3, 0, 'Press any key.'))
                            self.any_key()
                            continue
                        break
                    if filepath is False:
                        continue
                    self.db.keyfile = filepath
                    changed = True
                    if auth != 3:
                        self.db.password = None
                if auth == 1 or auth == 3:
                    password = self.get_password('New Password: ')
                    if password is False:
                        continue
                    confirm = self.get_password('Confirm: ')
                    if confirm is False:
                        continue
                    if password == confirm:
                        self.db.password = password
                        changed = True
                    else:
                        try:
                            self.stdscr.addstr(3, 0, 'Passwords didn\'t match. '
                                               'Press any key.')
                        except:
                            pass
                        self.any_key()
                    if auth != 3:
                        self.db.keyfile = None
                break
            self.show_groups(
                g_highlight, groups, cur_win, g_offset, changed)
            self.show_entries(e_highlight, entries, cur_win, e_offset,
                              hide)
        elif c == ord('g'):
            edit = self.get_string('', 'Title: ')
            if edit is not False:
                if groups:
                    old_group = groups[g_highlight]
                else:
                    old_group = None

                try:
                    if self.cur_root is self.db._root_group:
                        self.db.create_group(edit)
                    else:
                        self.db.create_group(edit, self.cur_root)
                except KPError as err:
                    self.draw_text(changed,
                                   (1, 0, err.__str__()),
                                   (4, 0, 'Press any key.'))
                    self.any_key()
                else:
                    changed = True
                groups = sorted(self.cur_root.children,
                                key=lambda group: group.title.lower())
                if groups and groups[g_highlight].entries:
                    entries = sorted(groups[g_highlight].entries,
                                     key=lambda entry: entry.title.lower())
                else:
                    entries = []
                if (groups and (groups[g_highlight] is not old_group) and
                        old_group is not None):
                    g_highlight = groups.index(old_group)
            self.show_groups(g_highlight, groups, cur_win, g_offset,
                             changed)
            self.show_entries(e_highlight, entries, cur_win, e_offset,
                              hide)
        elif c == ord('G'):
            if groups:
                edit = self.get_string('', 'Title: ')
                if edit is not False:
                    try:
                        self.db.create_group(edit, groups[g_highlight])
                    except KPError as err:
                        self.draw_text(changed,
                                       (1, 0, err.__str__()),
                                       (4, 0, 'Press any key.'))
                        self.any_key()
                    else:
                        changed = True
                self.show_groups(g_highlight, groups, cur_win, g_offset,
                                 changed)
                self.show_entries(e_highlight, entries, cur_win,
                                  e_offset, hide)
        elif c == ord('y'):
            if groups:
                if entries:
                    old_entry = entries[e_highlight]
                else:
                    old_entry = None
                self.draw_text(changed,
                               (1, 0, 'At least one of the following attributes '
                                'must be given. Press any key'))
                self.any_key()

                pass_title = False
                pass_url = False
                pass_username = False
                pass_password = False
                pass_comment = False
                goto_last = False
                while True:
                    if pass_title is False:
                        title = self.get_string('', 'Title: ')
                    if title is False:
                        break
                    pass_title = True

                    if pass_url is False:
                        url = self.get_string('', 'URL: ')
                    if url is False:
                        pass_title = False
                        continue
                    pass_url = True

                    if pass_username is False:
                        username = self.get_string('', 'Username: ')
                    if username is False:
                        pass_url = False
                        continue
                    pass_username = True

                    if pass_password is False:
                        nav = self.gen_menu(
                            ((1, 0, 'Use password generator (1)'),
                             (2, 0, 'Type password by hand (2)'),
                             (3, 0, 'No password (3)')))
                        if nav == 1:
                            password = self.gen_pass()
                            if password is False:
                                continue
                        elif nav == 2:
                            while True:
                                password = self.get_password('Password: ', False)
                                if password is False:
                                    break
                                confirm = self.get_password('Confirm: ', False)
                                if confirm is False:
                                    continue

                                if password != confirm:
                                    try:
                                        self.stdscr.addstr(3, 0, 'Passwords didn\'t match. '
                                                           'Press any key.')
                                    except:
                                        pass
                                    self.any_key()
                                else:
                                    break
                            if password is False:
                                continue
                        else:
                            password = ''
                    if nav is False:
                        pass_username = False
                        continue
                    pass_password = True

                    if pass_comment is False:
                        comment = self.get_string('', 'Comment: ')
                    if comment is False:
                        pass_password = False
                        continue
                    pass_comment = True

                    self.draw_text(changed,
                                   (1, 0, 'Set expiration date? [y/(n)]'))
                    while True:
                        try:
                            e = self.stdscr.getch()
                        except KeyboardInterrupt:
                            e = 4

                        if e == ord('y'):
                            exp_date = self.get_exp_date()
                            break
                        elif e == 4:
                            self.del_clipboard()
                            if self.db is not None:
                                self.db_close()
                            self.close()
                        elif e == -1:
                            self.del_clipboard()
                        elif e == cur.KEY_RESIZE:
                            self.resize_all()
                        elif e == cur.KEY_F5:
                            pass_comment = False
                            goto_last = True
                            break
                        else:
                            exp_date = (2999, 12, 28)
                            break
                    if goto_last is True:
                        goto_last = False
                        continue
                    if exp_date is False:
                        pass_comment = False
                        continue
                    try:
                        groups[g_highlight].create_entry(title, 1, url,
                                                         username, password,
                                                         comment,
                                                         exp_date[0],
                                                         exp_date[1],
                                                         exp_date[2])
                        changed = True
                    except KPError as err:
                        self.draw_text(changed,
                                       (1, 0, err.__str__()),
                                       (4, 0, 'Press any key.'))
                        self.any_key()
                    groups = sorted(self.cur_root.children,
                                    key=lambda group: group.title.lower())
                    entries = sorted(groups[g_highlight].entries,
                                     key=lambda entry: entry.title.lower())
                    if (entries and entries[e_highlight] is not old_entry and
                            old_entry is not None):
                        e_highlight = entries.index(old_entry)
                    break
                self.show_groups(g_highlight, groups, cur_win, g_offset,
                                 changed)
                self.show_entries(e_highlight, entries, cur_win,
                                  e_offset, hide)
        elif c == ord('d'):
            if cur_win == 0 and groups:
                title = groups[g_highlight].title
                self.draw_text(changed,
                               (1, 0, 'Really delete group ' + title + '? '
                                '[y/(n)]'))
                while True:
                    try:
                        e = self.stdscr.getch()
                    except KeyboardInterrupt:
                        e = 4
                    if e == ord('y'):
                        try:
                            groups[g_highlight].remove_group()
                        except KPError as err:
                            self.draw_text(changed,
                                           (1, 0, err.__str__()),
                                           (4, 0, 'Press any key.'))
                            self.any_key()
                        else:
                            if (not groups and
                                    self.cur_root is not self.db._root_group):
                                self.cur_root = self.cur_root.parent
                            changed = True

                            if (g_highlight >= len(groups) and
                                    g_highlight != 0):
                                g_highlight -= 1
                            e_highlight = 0
                        finally:
                            break
                    elif e == 4:
                        self.del_clipboard()
                        if self.db is not None:
                            self.db_close()
                        self.close()
                    elif e == -1:
                        self.del_clipboard()
                    elif e == cur.KEY_RESIZE:
                        self.resize_all()
                    else:
                        break
                groups = sorted(self.cur_root.children,
                                key=lambda group: group.title.lower())
                if groups and groups[g_highlight].entries:
                    entries = sorted(groups[g_highlight].entries,
                                     key=lambda entry:
                                     entry.title.lower())
                else:
                    entries = []
                self.show_groups(g_highlight, groups, cur_win, g_offset,
                                 changed)
                self.show_entries(e_highlight, entries, cur_win,
                                  e_offset, hide)
            elif cur_win == 1 and entries:
                title = entries[e_highlight].title
                self.draw_text(changed,
                               (1, 0,
                                'Really delete entry ' + title + '? [y/(n)]'))
                while True:
                    try:
                        e = self.stdscr.getch()
                    except KeyboardInterrupt:
                        e = 4
                    if e == ord('y'):
                        try:
                            entries[e_highlight].remove_entry()
                        except KPError as err:
                            self.draw_text(changed,
                                           (1, 0, err.__str__()),
                                           (4, 0, 'Press any key.'))
                            self.any_key()
                        else:
                            changed = True
                            if not entries:
                                cur_win = 0
                            if (e_highlight >= len(entries) and
                                    e_highlight != 0):
                                e_highlight -= 1
                        finally:
                            break
                    elif e == 4:
                        self.del_clipboard()
                        if self.db is not None:
                            self.db_close()
                        self.close()
                    elif e == -1:
                        self.del_clipboard()
                    elif e == cur.KEY_RESIZE:
                        self.resize_all()
                    else:
                        break
                if groups and groups[g_highlight].entries:
                    entries = sorted(groups[g_highlight].entries,
                                     key=lambda entry: entry.title.lower())
                else:
                    entries = []
                    cur_win = 0
                self.show_groups(g_highlight, groups, cur_win, g_offset,
                                 changed)
                self.show_entries(e_highlight, entries, cur_win,
                                  e_offset, hide)
        elif c == ord('f'):
            if self.db._entries:
                title = self.get_string('', 'Title: ')
                if title is not False:
                    for i in self.db.groups:
                        if i.id_ == 0:
                            i.parent.children.remove(i)
                            self.db.groups.remove(i)
                            break
                    self.db.create_group('Results')
                    self.db.groups[-1].id_ = 0
                    for i in self.db._entries:
                        if title.lower() in i.title.lower():
                            self.db.groups[-1].entries.append(i)
                            cur_win = 1
                    self.cur_root = self.db._root_group
                    groups = sorted(self.cur_root.children,
                                    key=lambda group: group.title.lower())
                    for i in groups:
                        if i.id_ == 0:
                            groups.remove(i)
                            groups.append(i)
                    g_highlight = len(groups) - 1
                    if groups and groups[-1].entries:
                        entries = sorted(groups[-1].entries,
                                         key=lambda entry: entry.title.lower())
                    else:
                        entries = []
                    e_highlight = 0
                self.show_groups(g_highlight, groups, cur_win, g_offset,
                                 changed)
                self.show_entries(e_highlight, entries, cur_win,
                                  e_offset, hide)

        elif (c == ord('t') or c == ord('u') or c == ord('U') or
              c == ord('C')):
            if groups:
                if not entries and cur_win == 1:
                    continue
                if c == ord('t'):
                    std = 'Title: '
                    if cur_win == 0:
                        edit = groups[g_highlight].title
                    elif cur_win == 1:
                        edit = entries[e_highlight].title
                elif c == ord('u') and entries:
                    std = 'Username: '
                    edit = entries[e_highlight].username
                elif c == ord('U') and entries:
                    std = 'URL: '
                    edit = entries[e_highlight].url
                elif c == ord('C') and entries:
                    std = 'Comment: '
                    edit = entries[e_highlight].comment
                else:
                    continue
                edit = self.get_string(edit, std)
                changed = True

                if edit is not False:
                    if c == ord('t'):
                        if cur_win == 0:
                            groups[g_highlight].set_title(edit)
                        elif cur_win == 1:
                            entries[e_highlight].set_title(edit)
                    elif c == ord('u'):
                        entries[e_highlight].set_username(edit)
                    elif c == ord('U'):
                        entries[e_highlight].set_url(edit)
                    elif c == ord('C'):
                        entries[e_highlight].set_comment(edit)
                self.show_groups(g_highlight, groups, cur_win, g_offset,
                                 changed)
                self.show_entries(e_highlight, entries, cur_win,
                                  e_offset, hide)
        elif c == ord('p'):
            if entries:
                nav = self.gen_menu(((1, 0, 'Use password generator (1)'),
                                     (2, 0, 'Type password by hand (2)')))
                if nav == 1:
                    password = self.gen_pass()
                    entries[e_highlight].set_password(password)
                    changed = True
                elif nav == 2:
                    while True:
                        password = self.get_password('Password: ', False)
                        if password is False:
                            break
                        confirm = self.get_password('Confirm: ', False)
                        if confirm is False:
                            continue

                        if password == confirm:
                            entries[e_highlight].set_password(password)
                            changed = True
                            break
                        else:
                            try:
                                self.stdscr.addstr(3, 0, 'Passwords didn\'t match. '
                                                   'Press any key.')
                            except:
                                pass
                            self.any_key()
                            break
                self.show_groups(g_highlight, groups, cur_win, g_offset,
                                 changed)
                self.show_entries(e_highlight, entries, cur_win,
                                  e_offset, hide)
        elif c == ord('E'):
            if entries:
                exp = entries[e_highlight].expire.timetuple()
                exp_date = self.get_exp_date(exp[0], exp[1], exp[2])

                if exp_date is not False:
                    entries[e_highlight].set_expire(
                        exp_date[0], exp_date[1], exp_date[2],
                        exp[3], exp[4], exp[5])
                    changed = True
                self.show_groups(g_highlight, groups, cur_win, g_offset,
                                 changed)
                self.show_entries(e_highlight, entries, cur_win,
                                  e_offset, hide)
        # Navigation
        elif c == ord('H'):
            if hide is True:
                hide = False
            else:
                hide = True
            self.show_entries(e_highlight, entries, cur_win, e_offset,
                              hide)
        elif c == cur.KEY_DOWN or c == ord('j'):
            if cur_win == 0:
                if g_highlight >= len(groups) - 1:
                    continue
                ysize = self.group_win.getmaxyx()[0]
                if (g_highlight >= ysize - 4 and
                        not g_offset >= len(groups) - ysize + 4):
                    g_offset += 1
                g_highlight += 1
                e_offset = 0
                e_highlight = 0
                if groups and groups[g_highlight].entries:
                    entries = sorted(groups[g_highlight].entries,
                                     key=lambda entry:
                                     entry.title.lower())
                else:
                    entries = []
                self.show_groups(g_highlight, groups, cur_win, g_offset,
                                 changed)
                self.show_entries(e_highlight, entries, cur_win,
                                  e_offset, hide)
            elif cur_win == 1:
                if e_highlight >= len(entries) - 1:
                    continue
                ysize = self.entry_win.getmaxyx()[0]
                if (e_highlight >= ysize - 4 and
                        not e_offset >= len(entries) - ysize + 3):
                    e_offset += 1
                e_highlight += 1
                self.show_entries(e_highlight, entries, cur_win,
                                  e_offset, hide)
        elif c == cur.KEY_UP or c == ord('k'):
            if cur_win == 0:
                if g_highlight <= 0:
                    continue
                ysize = self.group_win.getmaxyx()[0]
                if (g_highlight <= len(self.cur_root.children) - ysize + 3 and
                        not g_offset <= 0):
                    g_offset -= 1
                g_highlight -= 1
                e_offset = 0
                e_highlight = 0
                if groups and groups[g_highlight].entries:
                    entries = sorted(groups[g_highlight].entries,
                                     key=lambda entry:
                                     entry.title.lower())
                else:
                    entries = []
                self.show_groups(g_highlight, groups, cur_win, g_offset,
                                 changed)
                self.show_entries(e_highlight, entries, cur_win,
                                  e_offset, hide)
            elif cur_win == 1:
                if e_highlight <= 0:
                    continue
                ysize = self.entry_win.getmaxyx()[0]
                if e_highlight <= len(entries) - ysize + 3 and \
                        not e_offset <= 0:
                    e_offset -= 1
                e_highlight -= 1
                self.show_entries(e_highlight, entries, cur_win,
                                  e_offset, hide)
        elif c == cur.KEY_LEFT or c == ord('h'):
            cur_win = 0
            self.show_groups(
                g_highlight, groups, cur_win, g_offset, changed)
            self.show_entries(e_highlight, entries, cur_win, e_offset,
                              hide)
        elif c == cur.KEY_RIGHT or c == ord('l'):
            if entries:
                cur_win = 1
                self.show_groups(g_highlight, groups, cur_win, g_offset,
                                 changed)
                self.show_entries(e_highlight, entries, cur_win,
                                  e_offset, hide)
        elif c == cur.KEY_RESIZE:
            self.resize_all()
            self.show_groups(
                g_highlight, groups, cur_win, g_offset, changed)
            self.show_entries(e_highlight, entries, cur_win, e_offset,
                              hide)
        elif c == NL:
            if groups and groups[g_highlight].children:
                self.cur_root = groups[g_highlight]
                g_highlight = 0
                e_highlight = 0
                cur_win = 0
                groups = sorted(self.cur_root.children,
                                key=lambda group: group.title.lower())
                if groups and groups[g_highlight].entries:
                    entries = sorted(groups[g_highlight].entries,
                                     key=lambda entry: entry.title.lower(
                                     ))
                else:
                    entries = []
                self.show_groups(g_highlight, groups, cur_win, g_offset,
                                 changed)
                self.show_entries(e_highlight, entries, cur_win,
                                  e_offset, hide)
        elif c == cur.KEY_BACKSPACE or c == DEL:
            if not self.cur_root is self.db._root_group:
                g_highlight = 0
                e_highlight = 0
                cur_win = 0
                self.cur_root = self.cur_root.parent
                groups = sorted(self.cur_root.children,
                                key=lambda group: group.title.lower())
                for i in groups:
                    if i.id_ == 0:
                        groups.remove(i)
                        groups.append(i)
                if groups and groups[g_highlight].entries:
                    entries = sorted(groups[g_highlight].entries,
                                     key=lambda entry: entry.title.lower(
                                     ))
                else:
                    entries = []
                self.show_groups(g_highlight, groups, cur_win, g_offset,
                                 changed)
                self.show_entries(e_highlight, entries, cur_win,
                                  e_offset, hide)

class LockedDB(object):

