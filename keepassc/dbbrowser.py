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
import os
import threading
import webbrowser
from curses.ascii import NL, DEL
from os.path import isfile, isdir
from subprocess import Popen, PIPE

from kppy import KPError

class DBBrowser(object):
    '''This class represents the database browser'''

    def __init__(self, control):
        self.control = control
        if self.control.cur_dir[-4:] == '.kdb':
            if not isdir(self.control.last_home[:-5]):
                if isfile(self.control.last_home[:-5]):
                    os.remove(self.control.last_home[:-5])
                os.makedirs(self.control.last_home[:-5])
            handler = open(self.control.last_home, 'w')
            handler.write(self.control.cur_dir)
            handler.close()
        self.db = self.control.db
        self.cur_root = self.db._root_group
        self.lock_timer = None
        self.lock_highlight = 1
        self.clip_timer = None
        self.cb = None
        self.changed = False
        self.g_highlight = 0
        self.e_highlight = 0
        self.g_offset = 0
        self.e_offset = 0
        self.sort_tables(True, False)
        self.changed = False
        self.cur_win = 0
        self.state = 0 # 0 = unlocked, 1 = locked, 2 = pre_lock

        self.control.show_groups(self.g_highlight, self.groups, 
                                 self.cur_win, self.g_offset,
                                 self.changed, self.cur_root)
        self.control.show_entries(self.e_highlight, self.entries,
                                  self.cur_win, self.e_offset)
        self.db_browser()

    def sort_tables(self, groups, results, go2results = False):
        if groups is True: #To prevent senseless sorting
            self.groups = sorted(self.cur_root.children,
                            key=lambda group: group.title.lower())
        if results is True: # To prevent senseless sorting
            for i in self.groups: # 'Results' should be the last group
                if i.id_ == 0:
                    self.groups.remove(i)
                    self.groups.append(i)
        if go2results is True:
            self.g_highlight = len(self.groups) - 1
        self.entries = []
        if self.groups and self.groups[self.g_highlight].entries:
            self.entries = sorted(self.groups[self.g_highlight].entries,
                             key=lambda entry: entry.title.lower())

    def pre_save(self):
        '''Prepare saving'''

        if self.db.filepath is None:
            filepath = self.control.fb.get_filepath()
            if filepath == -1:
                self.close()
            elif filepath is not False:
                self.control.cur_dir = filepath
            else:
                return False
        while True:
            if self.save(self.control.cur_dir) is not False:
                self.changed = False
                break
            elif self.state != 2:
                return False
            else:
                continue
    
    def pre_save_as(self):
        '''Prepare "Save as"'''

        filepath = self.control.fb.get_filepath(False)
        if filepath == -1:
            self.close()
        elif filepath is not False:
            if self.db.filepath is None:
                self.control.cur_dir = filepath
            if isfile(filepath):
                self.overwrite_file(filepath)
            else:
                if self.save(filepath) is not False:
                    self.changed = False
                else:
                    return False
        else: 
            return False

    def save(self, cur_dir):
        '''Save the database. cur_dir is the current directory.'''

        self.remove_results()
        self.sort_tables(True, False)
        self.control.draw_text(False,
                               (1, 0, 'Do not interrupt or '
                                'your file will break!'))
        try:
            self.db.save(cur_dir)
        except KPError as err:
            self.control.draw_text(False,
                           (1, 0, err.__str__()),
                           (4, 0, 'Press any key.'))
            if self.control.any_key() == -1:
                self.close()
            return False

    def save_n_quit(self):
        '''Save database and close KeePassC'''

        if self.db.filepath is None:
            filepath = self.control.fb.get_filepath()
            if filepath == -1:
                self.close()
            elif filepath is not False:
                self.control.cur_dir = filepath
                if self.save(self.control.cur_dir) is not False:
                    self.close()
        elif self.save(self.control.cur_dir) is not False:
            self.close()

    def ask_for_saving(self):
        '''Ask to save the database (e.g. before quitting)'''

        while True:
            self.control.draw_text(self.changed,
                           (1, 0, 'File has changed. Save? [(y)/n]'))
            try:
                e = self.control.stdscr.getch()
            except KeyboardInterrupt:
                e = 4
            if e == 4:
                self.close()
            elif e == cur.KEY_RESIZE:
                self.control.resize_all()
            elif e == cur.KEY_F5:
                return False
            elif e == ord('n'):
                break
            else:
                if self.db.filepath is None:
                    filepath = self.control.fb.get_filepath()
                    if filepath == -1:
                        self.close()
                    elif filepath is not False:
                        self.control.cur_dir = filepath
                        self.save(self.control.cur_dir)
                    else:
                        continue
                else:
                    self.save(self.control.cur_dir)
            break

    def overwrite_file(self, filepath):
        '''Overwrite an existing file'''

        self.control.draw_text(self.changed, 
                       (1, 0, 'File exists. Overwrite? [y/(n)]'))
        while True:
            try:
                c = self.control.stdscr.getch()
            except KeyboardInterrupt:
                c = 4
            if c == ord('y'):
                if self.save(filepath) is not False:
                    return True
                else:
                    return False
            elif c == 4:
                self.close()
            elif c == cur.KEY_RESIZE:
                self.control.resize_all()
            else:
                return False

    def close(self):
        '''Close KeePassC'''

        self.db_close()
        if type(self.clip_timer) is threading.Timer:
            self.clip_timer.cancel()
            self.del_clipboard()
        self.control.close()

    def db_close(self):
        '''Close the database correctly.'''

        if self.db.filepath is not None:
            try:
                self.db.close()
            except KPError as err:
                self.control.draw_text(False,
                               (1, 0, err.__str__()),
                               (4, 0, 'Press any key.'))
                self.control.any_key()
        self.db = None
        self.control.db = None

    def exit2main(self):
        '''Exit to main menu'''

        if self.changed is True:
            if self.ask_for_saving() is False:
                return
        if type(self.clip_timer) is threading.Timer:
            self.clip_timer.cancel()
            self.del_clipboard()
        self.db_close()

    def quit_kpc(self):
        '''Prepare closing of KeePassC'''

        if self.changed is True:
            if self.ask_for_saving() is False:
                return
        self.close()

    def pre_lock(self):
        '''Method is necessary to prevent weird effects due to theading'''

        if self.db.filepath is None:
            self.control.draw_text(self.changed,
                           (1, 0, 'Can only lock an existing db!'),
                           (4, 0, 'Press any key.'))
            if self.control.any_key() == -1:
                self.close()
            return False
        if self.changed is True and self.db.read_only is False:
            self.state = 2
            self.control.draw_text(self.changed,
                           (1, 0, 'File has changed. Save? [(y)/n]'))
        else:
            self.lock_db()

    def lock_db(self):
        '''Lock the database'''

        self.remove_results()
        self.del_clipboard()
        self.db.lock()
        self.state = 1
        self.control.draw_lock_menu(self.changed, self.lock_highlight,
                                    (1, 0, 'Use a password (1)'),
                                    (2, 0, 'Use a keyfile (2)'),
                                    (3, 0, 'Use both (3)'))

    def unlock_with_password(self):
        '''Unlock the database with a password'''
        self.lock_highlight = 1
        self.unlock_db()

    def unlock_with_keyfile(self):
        '''Unlock the database with a keyfile'''
        self.lock_highlight = 2
        self.unlock_db()

    def unlock_with_both(self):
        '''Unlock the database with both'''
        self.lock_highlight = 3
        self.unlock_db()
    
    def unlock_db(self):
        '''Unlock the database'''

        if self.lock_highlight == 1 or self.lock_highlight == 3:
            password = self.control.get_password('Password: ')
            if password is False:
                return False
            elif password == -1:
                self.close()
            if self.lock_highlight != 3: # Only password needed
                keyfile = None
        if self.lock_highlight == 2 or self.lock_highlight == 3:
            while True:
                keyfile = self.control.fb.get_filepath(False, True)
                if keyfile is False:
                    return False
                elif keyfile == -1:
                    self.close()
                elif not isfile(keyfile):
                    self.control.draw_text(self.changed,
                                   (1, 0, 'That\'s not a file'),
                                   (3, 0, 'Press any key.'))
                    if self.control.any_key() == -1:
                        self.close()
                    continue
                break
            if self.lock_highlight != 3: # Only keyfile needed
                password = None
        try:
            self.db.unlock(password, keyfile)
        except KPError as err:
            self.control.draw_text(self.changed,
                           (1, 0, err.__str__()),
                           (4, 0, 'Press any key.'))
            if self.control.any_key() == -1:
                self.close()
        else:
            self.cur_root = self.db._root_group
            self.sort_tables(True, False)
            self.state = 0
            self.control.show_groups(self.g_highlight, self.groups, 
                                     self.cur_win, self.g_offset,
                                     self.changed, self.cur_root)
            self.control.show_entries(self.e_highlight, self.entries, 
                                      self.cur_win, self.e_offset)
    
    def nav_down_lock(self):
        '''Navigate down in lock menu'''

        if self.lock_highlight < 3:
            self.lock_highlight += 1

    def nav_up_lock(self):
        '''Navigate up in lock menu'''

        if self.lock_highlight > 1:
            self.lock_highlight -= 1

    def change_db_password(self):
        '''Change the master key of the database'''

        while True:
            auth = self.control.gen_menu((
                                 (1, 0, 'Use a password (1)'),
                                 (2, 0, 'Use a keyfile (2)'),
                                 (3, 0, 'Use both (3)')))
            if auth == 2 or auth == 3:
                while True:
                    filepath = self.control.fb.get_filepath(False, True)
                    if filepath == -1:
                        self.close()
                    elif not isfile(filepath):
                        self.control.draw_text(self.changed,
                                       (1, 0, "That's not a file!"),
                                       (3, 0, 'Press any key.'))
                        if self.control.any_key() == -1:
                            self.close()
                        continue
                    break
                if filepath is False:
                    continue
                self.db.keyfile = filepath
                if auth != 3:
                    self.db.password = None
            if auth == 1 or auth == 3:
                password = self.control.get_password('New Password: ')
                if password is False:
                    continue
                elif password == -1:
                    self.close()
                confirm = self.control.get_password('Confirm: ')
                if confirm is False:
                    continue
                elif confirm == -1:
                    self.close()
                if password == confirm:
                    self.db.password = password
                else:
                    self.control.draw_text(self.changed,
                                        (3, 0, 'Passwords didn\'t match. '
                                               'Press any key.'))
                    if self.control.any_key() == -1:
                        self.close()
                if auth != 3:
                    self.db.keyfile = None
            if auth is False:
                return False
            elif auth == -1:
                self.close()
            else:
                return True

    def create_group(self):
        '''Create a group in the current root'''

        edit = self.control.get_string('', 'Title: ')
        if edit == -1:
            self.close()
        elif edit is not False:
            if self.groups:
                old_group = self.groups[self.g_highlight]
            else:
                old_group = None

            try:
                if self.cur_root is self.db._root_group:
                    self.db.create_group(edit)
                else:
                    self.db.create_group(edit, self.cur_root)
            except KPError as err:
                self.control.draw_text(self.changed,
                               (1, 0, err.__str__()),
                               (4, 0, 'Press any key.'))
                if self.control.any_key() == -1:
                    self.close()
            else:
                self.changed = True
            self.sort_tables(True, True)
            if (self.groups and 
                self.groups[self.g_highlight] is not old_group and
                old_group is not None):
                self.g_highlight = self.groups.index(old_group)

    def create_sub_group(self):
        '''Create a sub group with marked group as parrent'''

        if self.groups:
            edit = self.control.get_string('', 'Title: ')
            if edit == -1:
                self.close()
            elif edit is not False:
                try:
                    self.db.create_group(edit, self.groups[self.g_highlight])
                except KPError as err:
                    self.control.draw_text(self.changed,
                                   (1, 0, err.__str__()),
                                   (4, 0, 'Press any key.'))
                    if self.control.any_key() == -1:
                        self.close()
                else:
                    self.changed = True

    def create_entry(self):
        '''Create an entry for the marked group'''

        if self.groups:
            if self.entries:
                old_entry = self.entries[self.e_highlight]
            else:
                old_entry = None
            self.control.draw_text(self.changed,
                           (1, 0, 'At least one of the following attributes '
                            'must be given. Press any key'))
            if self.control.any_key() == -1:
                self.close()

            pass_title = False
            pass_url = False
            pass_username = False
            pass_password = False
            pass_comment = False
            goto_last = False
            while True:
                if pass_title is False:
                    title = self.control.get_string('', 'Title: ')
                if title is False:
                    break
                elif title == -1:
                    self.close()
                pass_title = True

                if pass_url is False:
                    url = self.control.get_string('', 'URL: ')
                if url is False:
                    pass_title = False
                    continue
                elif url == -1:
                    self.close()
                pass_url = True

                if pass_username is False:
                    username = self.control.get_string('', 'Username: ')
                if username is False:
                    pass_url = False
                    continue
                elif username == -1:
                    self.close()
                pass_username = True

                if pass_password is False:
                    nav = self.control.gen_menu(
                        ((1, 0, 'Use password generator (1)'),
                         (2, 0, 'Type password by hand (2)'),
                         (3, 0, 'No password (3)')))
                    if nav == 1:
                        password = self.control.gen_pass()
                        if password is False:
                            continue
                        elif password == -1:
                            self.close()
                    elif nav == 2:
                        while True:
                            password = self.control.get_password('Password: ',
                                                                 False)
                            if password is False:
                                break
                            elif password == -1:
                                self.close()
                            confirm = self.control.get_password('Confirm: ',
                                                                False)
                            if confirm is False:
                                continue
                            elif confirm == -1:
                                self.close()

                            if password != confirm:
                                self.control.draw_text(self.changed,
                                               (3, 0, "Passwords didn't match"),
                                               (5, 0, 'Press any key.'))
                                if self.control.any_key() == -1:
                                    self.close()
                            else:
                                break
                        if password is False:
                            continue
                    elif nav == -1:
                        self.close()
                    else:
                        password = ''
                if nav is False:
                    pass_username = False
                    continue
                pass_password = True

                if pass_comment is False:
                    comment = self.control.get_string('', 'Comment: ')
                if comment is False:
                    pass_password = False
                    continue
                elif comment == -1:
                    self.close()
                pass_comment = True

                self.control.draw_text(self.changed,
                               (1, 0, 'Set expiration date? [y/(n)]'))
                while True:
                    try:
                        e = self.control.stdscr.getch()
                    except KeyboardInterrupt:
                        e = 4

                    if e == ord('y'):
                        exp_date = self.control.get_exp_date()
                        break
                    elif e == 4:
                        self.close()
                    elif e == cur.KEY_RESIZE:
                        self.control.resize_all()
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
                elif exp_date == -1:
                    self.close()
                try:
                    self.groups[self.g_highlight].create_entry(title, 1, url,
                                                     username, password,
                                                     comment,
                                                     exp_date[0],
                                                     exp_date[1],
                                                     exp_date[2])
                    self.changed = True
                except KPError as err:
                    self.control.draw_text(self.changed,
                                   (1, 0, err.__str__()),
                                   (4, 0, 'Press any key.'))
                    if self.control.any_key() == -1:
                        self.close()
                self.sort_tables(True, True)
                if (self.entries and 
                    self.entries[self.e_highlight] is not old_entry and
                    old_entry is not None):
                    self.e_highlight = self.entries.index(old_entry)
                break

    def pre_delete(self):
        '''Prepare deletion of group or entry'''

        if self.cur_win == 0 and self.groups:
            self.delete_group()
        elif self.cur_win == 1:
            self.delete_entry()

    def delete_group(self):
        '''Delete the marked group'''

        if len(self.db.groups) > 1:
            title = self.groups[self.g_highlight].title
            self.control.draw_text(self.changed,
                           (1, 0, 'Really delete group ' + title + '? '
                            '[y/(n)]'))
        else:
            self.control.draw_text(self.changed,
                           (1, 0, 'At least one group is needed!'),
                           (3, 0, 'Press any key'))
            if self.control.any_key() == -1:
                self.close()
        while True:
            try:
                e = self.control.stdscr.getch()
            except KeyboardInterrupt:
                e = 4
            if e == ord('y'):
                try:
                    self.groups[self.g_highlight].remove_group()
                except KPError as err:
                    self.control.draw_text(self.changed,
                                   (1, 0, err.__str__()),
                                   (4, 0, 'Press any key.'))
                    if self.control.any_key() == -1:
                        self.close()
                else:
                    if (not self.cur_root.children and
                            self.cur_root is not self.db._root_group):
                        self.cur_root = self.cur_root.parent
                    self.changed = True

                    if (self.g_highlight >= len(self.groups) and
                            self.g_highlight != 0):
                        self.g_highlight -= 1
                    self.e_highlight = 0
                    self.sort_tables(True, True)
                break
            elif e == 4:
                self.close()
            elif e == cur.KEY_RESIZE:
                self.control.resize_all()
            else:
                break

    def delete_entry(self):
        '''Delete marked entry'''

        title = self.entries[self.e_highlight].title
        self.control.draw_text(self.changed,
                       (1, 0,
                        'Really delete entry ' + title + '? [y/(n)]'))
        while True:
            try:
                e = self.control.stdscr.getch()
            except KeyboardInterrupt:
                e = 4
            if e == ord('y'):
                try:
                    self.entries[self.e_highlight].remove_entry()
                except KPError as err:
                    self.control.draw_text(self.changed,
                                   (1, 0, err.__str__()),
                                   (4, 0, 'Press any key.'))
                    if self.control.any_key() == -1:
                        self.close()
                else:
                    self.sort_tables(True, True)
                    self.changed = True
                    if not self.entries:
                        self.cur_win = 0
                    if (self.e_highlight >= len(self.entries) and
                            self.e_highlight != 0):
                        self.e_highlight -= 1
                break
            elif e == 4:
                self.close()
            elif e == cur.KEY_RESIZE:
                self.control.resize_all()
            else:
                break

    def find_entries(self):
        '''Find entries by title'''

        if self.db._entries:
            title = self.control.get_string('', 'Title: ')
            if title == -1:
                self.close()
            elif title is not False and title != '':
                self.remove_results()
                self.db.create_group('Results')
                self.db.groups[-1].id_ = 0

                #Necessary construct to prevent inf loop
                for i in range(len(self.db._entries)):
                    entry = self.db._entries[i]
                    if title.lower() in entry.title.lower():
                        exp = entry.expire.timetuple()
                        self.db.groups[-1].create_entry(
                                entry.title + ' ('+ entry.group.title + ')', 
                                                        entry.image, entry.url,
                                                        entry.username,
                                                        entry.password, 
                                                        entry.comment,
                                                        exp[0], exp[1], exp[2])
                        self.cur_win = 1
                self.cur_root = self.db._root_group
                self.sort_tables(True, True, True)
                self.e_highlight = 0

    def remove_results(self):
        '''Remove possible search result group'''

        for i in self.db.groups:
            if i.id_ == 0:
                try:
                    i.remove_group()
                except KPError as err:
                    self.control.draw_text(self.changed,
                                   (1, 0, err.__str__()),
                                   (4, 0, 'Press any key.'))
                    if self.control.any_key() == -1:
                        self.close()
                    return False
                else:
                    if (self.g_highlight >= len(self.db.groups) and
                            self.g_highlight != 0):
                        self.g_highlight -= 1
                    self.e_highlight = 0
                break

    def edit_title(self):
        '''Edit title of group or entry'''

        if self.groups:
            std = 'Title: '
            if self.cur_win == 0:
                edit = self.control.get_string(
                                        self.groups[self.g_highlight].title, 
                                        std)
                if edit == -1:
                    self.close()
                elif edit is not False:
                    self.groups[self.g_highlight].set_title(edit)
                    self.changed = True
            elif self.cur_win == 1:
                edit = self.control.get_string(
                                        self.entries[self.e_highlight].title,
                                        std)
                if edit == -1:
                    self.close()
                elif edit is not False:
                    self.entries[self.e_highlight].set_title(edit)
                    self.changed = True
            
    def edit_username(self):
        '''Edit username of marked entry'''

        if self.entries:
            std = 'Username: '
            edit = self.control.get_string(
                                    self.entries[self.e_highlight].username,
                                    std)
            if edit == -1:
                self.close()
            elif edit is not False:
                self.entries[self.e_highlight].set_username(edit)
                
    def edit_url(self):
        '''Edit URL of marked entry'''

        if self.entries:
            std = 'URL: '
            edit = self.control.get_string(
                                    self.entries[self.e_highlight].url, std)
            if edit == -1:
                self.close()
            elif edit is not False:
                self.entries[self.e_highlight].set_url(edit)

    def edit_comment(self):
        '''Edit comment of marked entry'''

        if self.entries:
            std = 'Comment: '
            edit = self.control.get_string(
                                    self.entries[self.e_highlight].comment,
                                    std)
            if edit == -1:
                self.close()
            elif edit is not False:
                self.entries[self.e_highlight].set_comment(edit)
    
    def edit_password(self):
        '''Edit password of marked entry'''

        nav = self.control.gen_menu(((1, 0, 'Use password generator (1)'),
                                     (2, 0, 'Type password by hand (2)'),
                                     (3, 0, 'No password (3)')))
        if nav == 1:
            password = self.control.gen_pass()
            if password == -1:
                self.close()
            elif password is False:
                return False
            self.entries[self.e_highlight].set_password(password)
            self.changed = True
        elif nav == 2:
            while True:
                password = self.control.get_password('Password: ', False)
                if password is False:
                    break
                elif password == -1:
                    self.close()
                confirm = self.control.get_password('Confirm: ', False)
                if confirm is False:
                    continue
                elif confirm == -1:
                    self.close()

                if password == confirm:
                    self.entries[self.e_highlight].set_password(password)
                    self.changed = True
                    break
                else:
                    self.control.draw_text(self.changed,
                                        (3, 0, 'Passwords didn\'t match. '
                                               'Press any key.'))
                    if self.control.any_key() == -1:
                        self.close()
                    break
        elif nav == -1:
            self.close()

    def edit_date(self):
        '''Edit expiration date of marked entry'''

        exp = self.entries[self.e_highlight].expire.timetuple()
        exp_date = self.control.get_exp_date(exp[0], exp[1], exp[2])

        if exp_date == -1:
            self.close()
        elif exp_date is not False:
            self.entries[self.e_highlight].set_expire(
                exp_date[0], exp_date[1], exp_date[2],
                exp[3], exp[4], exp[5])
            self.changed = True

    def show_password(self):
        '''Show password of marked entry (e.g. copy it without xsel)'''

        if self.entries:
            self.control.draw_text(self.changed,
                            (1, 0, self.entries[self.e_highlight].password))
            if self.control.any_key() == -1:
                self.close()

    def copy_password(self):
        '''Copy password to clipboard (calls cp2cb)'''

        if self.entries:
            self.cp2cb(self.entries[self.e_highlight].password)

    def copy_username(self):
        '''Copy username to clipboard (calls cp2cb)'''

        if self.entries:
            self.cp2cb(self.entries[self.e_highlight].username)

    def cp2cb(self, stuff):
        '''Copy stuff to clipboard'''

        if stuff is not None:
            try:
                Popen(
                    ['xsel', '-pc'], stderr=PIPE, stdout=PIPE)
                Popen(
                    ['xsel', '-bc'], stderr=PIPE, stdout=PIPE)
                Popen(['xsel', '-pi'], stdin=PIPE, stderr=PIPE,
                        stdout=PIPE).communicate(stuff.encode())
                Popen(['xsel', '-bi'], stdin=PIPE, stderr=PIPE,
                        stdout=PIPE).communicate(stuff.encode())
                if self.control.config['del_clip'] is True:
                    self.clip_timer = threading.Timer(
                                      self.control.config['clip_delay'],
                                      self.del_clipboard).start()
            except FileNotFoundError as err:
                self.control.draw_text(False,
                               (1, 0, err.__str__()),
                               (4, 0, 'Press any key.'))
                if self.control.any_key() == -1:
                    self.close()
            else:
                self.cb = stuff

    def del_clipboard(self):
        '''Delete the X clipboard'''

        try:
            cb_p = Popen('xsel', stdout=PIPE)
            cb = cb_p.stdout.read().decode()
            if cb == self.cb:
                Popen(['xsel', '-pc'])
                Popen(['xsel', '-bc'])
                self.cb = None
        except FileNotFoundError: # xsel not installed
            pass

    def open_url(self):
        '''Open URL in standard webbrowser'''

        if self.entries:
            entry = self.entries[self.e_highlight]
            url = entry.url
            if url != '':
                if url[:7] != 'http://' and url[:8] != 'https://':
                    url = 'http://' + url
                savout = os.dup(1)
                os.close(1)
                os.open(os.devnull, os.O_RDWR)
                try:
                   webbrowser.open(url)
                finally:
                   os.dup2(savout, 1)

    def nav_down(self):
        '''Navigate down'''

        if self.cur_win == 0 and self.g_highlight < len(self.groups) - 1:
            ysize = self.control.group_win.getmaxyx()[0]
            if (self.g_highlight >= ysize - 4 and
                    not self.g_offset >= len(self.groups) - ysize + 4):
                self.g_offset += 1
            self.g_highlight += 1
            self.e_offset = 0
            self.e_highlight = 0
            self.sort_tables(False, True)
        elif self.cur_win == 1 and self.e_highlight < len(self.entries)  - 1:
            ysize = self.control.entry_win.getmaxyx()[0]
            if (self.e_highlight >= ysize - 4 and
                    not self.e_offset >= len(self.entries) - ysize + 3):
                self.e_offset += 1
            self.e_highlight += 1

    def nav_up(self):
        '''Navigate up'''

        if self.cur_win == 0 and self.g_highlight > 0:
            ysize = self.control.group_win.getmaxyx()[0]
            if (self.g_highlight <= len(self.cur_root.children) - ysize + 3 and
                    not self.g_offset <= 0):
                self.g_offset -= 1
            self.g_highlight -= 1
            self.e_offset = 0
            self.e_highlight = 0
            self.sort_tables(False, True)
        elif self.cur_win == 1 and self.e_highlight > 0:
            ysize = self.control.entry_win.getmaxyx()[0]
            if self.e_highlight <= len(self.entries) - ysize + 3 and \
                    not self.e_offset <= 0:
                self.e_offset -= 1
            self.e_highlight -= 1

    def nav_left(self):
        '''Go to groups'''

        self.cur_win = 0

    def nav_right(self):
        '''Go to entries'''

        if self.entries:
            self.cur_win = 1

    def go2sub(self):
        '''Change to subgroups of current root'''

        if self.groups and self.groups[self.g_highlight].children:
            self.cur_root = self.groups[self.g_highlight]
            self.g_highlight = 0
            self.e_highlight = 0
            self.cur_win = 0
            self.sort_tables(True, False)

    def go2parent(self):
        '''Change to parent of current subgroups'''

        if not self.cur_root is self.db._root_group:
            self.g_highlight = 0
            self.e_highlight = 0
            self.cur_win = 0
            self.cur_root = self.cur_root.parent
            self.sort_tables(True, True)

    def db_browser(self):
        '''The database browser.'''

        unlocked_state = {
            cur.KEY_F1: self.control.dbbrowser_help,
            ord('e'): self.exit2main,
            ord('q'): self.quit_kpc,
            4: self.quit_kpc,
            ord('c'): self.copy_password,
            ord('b'): self.copy_username,
            ord('o'): self.open_url,
            ord('s'): self.pre_save,
            ord('S'): self.pre_save_as,
            ord('x'): self.save_n_quit,
            ord('L'): self.pre_lock,
            ord('P'): self.change_db_password,
            ord('g'): self.create_group,
            ord('G'): self.create_sub_group,
            ord('y'): self.create_entry,
            ord('d'): self.pre_delete,
            ord('f'): self.find_entries,
            ord('/'): self.find_entries,
            ord('t'): self.edit_title,
            ord('u'): self.edit_username,
            ord('U'): self.edit_url,
            ord('C'): self.edit_comment,
            ord('p'): self.edit_password,
            ord('E'): self.edit_date,
            ord('H'): self.show_password,
            cur.KEY_RESIZE: self.control.resize_all,
            NL: self.go2sub,
            cur.KEY_BACKSPACE: self.go2parent,
            DEL: self.go2parent,
            cur.KEY_DOWN: self.nav_down,
            ord('j'): self.nav_down,
            cur.KEY_UP: self.nav_up,
            ord('k'): self.nav_up,
            cur.KEY_LEFT: self.nav_left,
            ord('h'): self.nav_left,
            cur.KEY_RIGHT: self.nav_right,
            ord('l'): self.nav_right}

        locked_state = {
            ord('q'): self.quit_kpc,
            4: self.quit_kpc,
            cur.KEY_DOWN: self.nav_down_lock,
            ord('j'): self.nav_down_lock,
            cur.KEY_UP: self.nav_up_lock,
            ord('k'): self.nav_up_lock,
            NL: self.unlock_db,
            ord('1'): self.unlock_with_password,
            ord('2'): self.unlock_with_keyfile,
            ord('3'): self.unlock_with_both}

        while True:
            if (self.control.config['lock_db'] and self.state == 0 and 
                self.db.filepath is not None):
                self.lock_timer = threading.Timer(
                                    self.control.config['lock_delay'],
                                    self.pre_lock)
                self.lock_timer.start()
            try:
                c = self.control.stdscr.getch()
            except KeyboardInterrupt:
                c = 4
            if type(self.lock_timer) is threading.Timer:
                self.lock_timer.cancel()
            if self.state == 0:
                if c == ord('\t'): # Switch group/entry view with tab.
                    if self.cur_win == 0:
                        c = cur.KEY_RIGHT
                    else:
                        c = cur.KEY_LEFT
                if c in unlocked_state:
                    unlocked_state[c]()
                if c == ord('e'):
                    return False
                if self.state == 0: # 'cause 'L' changes state
                    self.control.show_groups(self.g_highlight, self.groups, 
                                             self.cur_win, self.g_offset,
                                             self.changed, self.cur_root)
                    self.control.show_entries(self.e_highlight, self.entries,
                                              self.cur_win, self.e_offset)
            elif self.state == 1 and c in locked_state:
                locked_state[c]()
                if self.state == 1: # 'cause 'L' changes state
                    self.control.draw_lock_menu(self.changed,
                                                self.lock_highlight,
                                                (1, 0, 'Use a password (1)'),
                                                (2, 0, 'Use a keyfile (2)'),
                                                (3, 0, 'Use both (3)'))
            elif self.state == 2:
                if c == ord('n'):
                    self.lock_db()
                else:
                    self.pre_save()
                    self.lock_db()

