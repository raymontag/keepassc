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
import os
import threading
import webbrowser
from curses.ascii import NL, DEL, ESC
from os.path import isfile, isdir
from subprocess import Popen, PIPE

from kppy.database import KPDBv1
from kppy.exceptions import KPError

from keepassc.client import Client
from keepassc.editor import Editor
from keepassc.filebrowser import FileBrowser


class DBBrowser(object):
    '''This class represents the database browser'''

    def __init__(self, control, remote = False, address = None, port = None,
                 ssl = False, tls_dir = None):
        self.control = control
        if (self.control.cur_dir[-4:] == '.kdb' and 
            self.control.config['rem_db'] is True and
            remote is False):
            if not isdir(self.control.data_home):
                if isfile(self.control.data_home):
                    os.remove(self.control.data_home)
                os.makedirs(self.control.data_home)
            with open(self.control.last_home, 'w') as handler:
                handler.write(self.control.cur_dir)

        if remote is True and self.control.config['rem_db'] is True:
            if not isdir(self.control.data_home):
                if isfile(self.control.data_home):
                    os.remove(self.control.data_home)
                os.makedirs(self.control.data_home)
            with open(self.control.remote_home, 'w') as handler:
                handler.write(address+'\n')
                handler.write(str(port))
            
        self.db = self.control.db
        self.cur_root = self.db.root_group
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
        # 0 = unlocked, 1 = locked, 2 = pre_lock,
        # 3 = move group, 4 = move entry
        self.state = 0
        self.move_object = None

        self.remote = remote
        self.address = address
        self.port = port
        self.ssl = ssl
        self.tls_dir = tls_dir

        self.control.show_groups(self.g_highlight, self.groups,
                                 self.cur_win, self.g_offset,
                                 self.changed, self.cur_root)
        self.control.show_entries(self.e_highlight, self.entries,
                                  self.cur_win, self.e_offset)
        self.db_browser()

    def sort_tables(self, groups, results, go2results=False):
        if groups is True:  # To prevent senseless sorting
            self.groups = sorted(self.cur_root.children,
                                 key=lambda group: group.title.lower())
        if results is True:  # To prevent senseless sorting
            for i in self.groups:  # 'Results' should be the last group
                if i.id_ == 0:
                    self.groups.remove(i)
                    self.groups.append(i)
        if go2results is True:
            self.g_highlight = len(self.groups) - 1
        self.entries = []
        if self.groups:
            if self.groups[self.g_highlight].entries:
                self.entries = sorted(self.groups[self.g_highlight].entries,
                                      key=lambda entry: entry.title.lower())

    def pre_save(self):
        '''Prepare saving'''

        if self.remote is True:
            return True

        if self.db.filepath is None:
            filepath = FileBrowser(self.control, False, False, None, True)()
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

        if self.remote is True:
            return True

        filepath = FileBrowser(self.control, False, False, None, True)()
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
            filepath = FileBrowser(self.control, False, False, None, True)()
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
                    filepath = FileBrowser(self.control, False, False, None, 
                                           True)()
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

        if self.db.filepath is None and self.remote is False:
            self.control.draw_text(self.changed,
                                   (1, 0, 'Can only lock an existing db!'),
                                   (4, 0, 'Press any key.'))
            if self.control.any_key() == -1:
                self.close()
            return False
        if ((self.changed is True and self.db.read_only is False) and
            self.remote is False):
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

    def reload_remote_db(self, db_buf = None):
        if self.remote is True:
            old_root = self.cur_root
            if self.groups:
                old_group_id = self.groups[self.g_highlight].id_
            else:
                old_group_id = None
            if self.entries:
                old_entry_uuid = self.entries[self.e_highlight].uuid
            else:
                old_entry_uuid = None

            if db_buf == None:
                db_buf = self.client().get_db()
                if self.check_answer(db_buf) is False:
                    return False
            self.db = KPDBv1(None, self.db.password, self.db.keyfile)
            self.db.load(db_buf)
            self.control.db = self.db

            # This loop has to be executed _before_ sort_tables is called
            for i in self.db.groups:
                if i.id_ == old_root.id_:
                    self.cur_root = i
                    break
                else:
                    self.cur_root = self.db.root_group

            self.sort_tables(True, True)

            if self.groups and old_group_id:
                for i in self.groups:
                    if i.id_ == old_group_id:
                        self.g_highlight = self.groups.index(i)
                        break
                    else:
                        self.g_highlight = 0
            else:
                self.g_highlight = 0

            if self.entries and old_entry_uuid:
                for i in self.entries:
                    if i.uuid == old_entry_uuid:
                        self.e_highlight = self.entries.index(i)
                        break
                    else:
                        self.e_highlight = 0
            else:
                self.e_highlight = 0

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
            if self.lock_highlight != 3:  # Only password needed
                keyfile = None
        if self.lock_highlight == 2 or self.lock_highlight == 3:
            while True:
                if self.control.config['rem_key'] is True:
                    self.control.get_last_key()
                if (self.control.last_key is None or
                        self.control.config['rem_key'] is False):
                    ask_for_lf = False
                else:
                    ask_for_lf = True

                keyfile = FileBrowser(self.control, ask_for_lf, True, 
                                      self.control.last_key)()
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
            if self.lock_highlight != 3:  # Only keyfile needed
                password = None

        if self.remote is True:
            db_buf = self.client().get_db()
            if self.check_answer(db_buf) is False:
                return False
        else:
            db_buf = None

        try:
            self.db.unlock(password, keyfile, db_buf)
        except KPError as err:
            self.control.draw_text(self.changed,
                                   (1, 0, err.__str__()),
                                   (4, 0, 'Press any key.'))
            if self.control.any_key() == -1:
                self.close()
        else:
            self.cur_root = self.db.root_group
            # If last shown group was Results
            if self.g_highlight >= len(self.groups):
                self.g_highlight = len(self.groups) - 1 
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

        if (self.address != "127.0.0.1" and self.address != "localhost" and
            self.remote is True):
            self.control.draw_text(False,
                           (1, 0, "Password change from remote is not "
                                  "allowed"),
                           (3, 0, "Press any key."))
            if self.control.any_key() == -1:
                self.close()

        while True:
            auth = self.control.gen_menu(1, (
                                         (1, 0, 'Use a password (1)'),
                                         (2, 0, 'Use a keyfile (2)'),
                                         (3, 0, 'Use both (3)')))
            if auth == 2 or auth == 3:
                while True:
                    filepath = FileBrowser(self.control, False, True, None)()
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
                if self.remote is False:
                    self.db.keyfile = filepath
                else:
                    tmp_keyfile = filepath
                if auth != 3:
                    password = None
                    tmp_password = None

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
                    if self.remote is False:
                        self.db.password = password
                    else:
                        tmp_password = password
                else:
                    self.control.draw_text(self.changed,
                                           (1, 0, 'Passwords didn\'t match. '
                                               'Press any key.'))
                    if self.control.any_key() == -1:
                        self.close()
                    continue
                if auth != 3:
                    filepath = None
                    tmp_keyfile = None

            if auth is False:
                return False
            elif auth == -1:
                self.close()
            elif self.remote is True:
                if tmp_password is None:
                    tmp_password = b''
                else:
                    tmp_password = tmp_password.encode()
                if tmp_keyfile is None:
                    tmp_keyfile = b''
                else:
                    tmp_keyfile = tmp_keyfile.encode()

                answer = self.client().change_password(tmp_password, 
                                                       tmp_keyfile)
                if self.check_answer(answer) is False:
                    return False
                else:
                    self.db.password = password
                    self.db.keyfile = filepath
                return True
            else:
                self.changed = True
                return True

    def create_group(self):
        '''Create a group in the current root'''

        edit = Editor(self.control.stdscr, max_text_size=1, win_location=(0, 1),
                      win_size=(1, 80), title="Group Name: ")()
        if edit == -1:
            self.close()
        elif edit is not False:
            if self.groups:
                old_group = self.groups[self.g_highlight]
            else:
                old_group = None

            if self.remote is True:
                if self.cur_root is self.db.root_group:
                    root = 0
                else:
                    root = self.cur_root.id_
                db_buf = self.client().create_group(edit.encode(), 
                                                    str(root).encode())
                if self.check_answer(db_buf) is not False:
                    self.reload_remote_db(db_buf)
            else:
                try:
                    if self.cur_root is self.db.root_group:
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
        '''Create a sub group with marked group as parent'''

        if self.groups:
            edit = Editor(self.control.stdscr, max_text_size=1,
                          win_location=(0, 1),
                          win_size=(1, 80), title="Group Name: ")()
            if edit == -1:
                self.close()
            elif edit is not False:
                if self.remote is True:
                    root = self.groups[self.g_highlight].id_
                    db_buf = self.client().create_group(edit.encode(),
                                                        (str(root)
                                                         .encode()))
                    if self.check_answer(db_buf) is not False:
                        self.reload_remote_db(db_buf)
                else:
                    try:
                        self.db.create_group(edit, 
                                             self.groups[self.g_highlight])
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
                                   (1, 0, 'At least one of the following '
                                    'attributes must be given. Press any key'))
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
                    title = Editor(self.control.stdscr, max_text_size=1,
                                   win_location=(0, 1),
                                   win_size=(1, 80), title="Title: ")()
                if title is False:
                    break
                elif title == -1:
                    self.close()
                pass_title = True

                if pass_url is False:
                    url = Editor(self.control.stdscr, max_text_size=1,
                                 win_location=(0, 1),
                                 win_size=(1, 80), title="URL: ")()
                if url is False:
                    pass_title = False
                    continue
                elif url == -1:
                    self.close()
                pass_url = True

                if pass_username is False:
                    username = Editor(self.control.stdscr, max_text_size=1,
                                      win_location=(0, 1),
                                      win_size=(1, 80), title="Username: ")()
                if username is False:
                    pass_url = False
                    continue
                elif username == -1:
                    self.close()
                pass_username = True

                if pass_password is False:
                    nav = self.control.gen_menu(1,
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
                                                    (3, 0,
                                                    "Passwords didn't match"),
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
                    comment = Editor(self.control.stdscr, win_location=(0, 1),
                                     title="Comment: ")()
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

                if self.remote is True:
                    root = self.groups[self.g_highlight].id_

                    db_buf = self.client().create_entry(title.encode(),
                                                 url.encode(),
                                                 username.encode(),
                                                 password.encode(),
                                                 comment.encode(),
                                                 str(exp_date[0]).encode(),
                                                 str(exp_date[1]).encode(),
                                                 str(exp_date[2]).encode(),
                                                 str(root).encode())
                    if self.check_answer(db_buf) is not False:
                        self.reload_remote_db(db_buf)
                    break
                else:
                    try:
                        self.groups[self.g_highlight].create_entry(title, 1, 
                                                                   url,
                                                                   username,
                                                                   password,
                                                                   comment,
                                                                   exp_date[0],
                                                                   exp_date[1],
                                                                   exp_date[2])
                    except KPError as err:
                        self.control.draw_text(self.changed,
                                               (1, 0, err.__str__()),
                                               (4, 0, 'Press any key.'))
                        if self.control.any_key() == -1:
                            self.close()
                    else:
                        self.changed = True

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
                if self.remote is True:
                    root = self.groups[self.g_highlight].id_
                    last_mod = (self.groups[self.g_highlight]
                                    .last_mod.timetuple())
                    db_buf = self.client().delete_group(str(root).encode(),
                                                        last_mod)
                    if self.check_answer(db_buf) is not False:
                        self.reload_remote_db(db_buf)
                else:
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
                                self.cur_root is not self.db.root_group):
                            self.cur_root = self.cur_root.parent
                        self.changed = True

                        if (self.g_highlight >= len(self.groups) - 1 and
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
                if self.remote is True:
                    entry_uuid = self.entries[self.e_highlight].uuid
                    last_mod = (self.entries[self.e_highlight]
                                    .last_mod.timetuple())

                    db_buf = self.client().delete_entry(entry_uuid, last_mod)
                    if self.check_answer(db_buf) is not False:
                        self.reload_remote_db(db_buf)

                        if not self.entries:
                            self.cur_win = 0
                        if (self.e_highlight >= len(self.entries) and
                                self.e_highlight != 0):
                            self.e_highlight -= 1
                else:
                    try:
                        self.entries[self.e_highlight].remove_entry()
                    except KPError as err:
                        self.control.draw_text(self.changed,
                                               (1, 0, err.__str__()),
                                               (4, 0, 'Press any key.'))
                        if self.control.any_key() == -1:
                            self.close()
                    else:
                        if self.groups[self.g_highlight].id_ == 0:
                            del (self.groups[self.g_highlight]
                                     .entries[self.e_highlight]) 
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

    def move(self):
        '''Enable move state'''

        if self.cur_win == 0:
            self.state = 3
            self.move_object = self.groups[self.g_highlight]
        elif self.cur_win == 1:
            self.state = 4
            self.cur_win = 0
            self.move_object = self.entries[self.e_highlight]

    def move_group_or_entry(self):
        '''Move group to subgroup or entry to new group'''
        
        if (self.state == 3 and 
            self.groups[self.g_highlight] is not self.move_object and
            self.groups):  # e.g. there is actually a group
            if self.remote is True:
                group_id = self.move_object.id_
                root = self.groups[self.g_highlight].id_

                db_buf = self.client().move_group(str(group_id).encode(), 
                                                  str(root).encode())
                if self.check_answer(db_buf) is not False:
                    self.reload_remote_db(db_buf)
            else:
                self.move_object.move_group(self.groups[self.g_highlight])
        elif (self.state == 4 and 
              self.groups[self.g_highlight] is not self.move_object.group and
              self.groups):
            if self.remote is True:
                uuid = self.move_object.uuid
                root = self.groups[self.g_highlight].id_

                db_buf = self.client().move_entry(uuid, 
                                                  str(root).encode())
                if self.check_answer(db_buf) is not False:
                    self.reload_remote_db(db_buf)
            else:
                self.move_object.move_entry(self.groups[self.g_highlight])
        self.changed = True
        self.move_object = None
        self.state = 0
        self.sort_tables(True, True)
            
    def move2root(self):
        if self.state == 3:
            if self.remote is True:
                group_id = self.move_object.id_
                root = 0

                db_buf = self.client().move_group(str(group_id).encode(), 
                                                  str(root).encode())
                if self.check_answer(db_buf) is not False:
                    self.reload_remote_db(db_buf)
            else:
                self.move_object.move_group(self.db.root_group)
            self.move_object = None
            self.state = 0
            self.sort_tables(True, True)

    def move_abort(self):
        self.move_object = None
        self.state = 0
        self.sort_tables(True, True)

    def find_entries(self):
        '''Find entries by title'''

        if self.db.entries:
            title = Editor(self.control.stdscr, max_text_size=1,
                           win_location=(0, 1),
                           win_size=(1, 80), title="Title Search: ")()
            if title == -1:
                self.close()
            elif title is not False and title != '':
                self.remove_results()
                self.db.create_group('Results')
                result_group = self.db.groups[-1]
                result_group.id_ = 0

                for i in self.db.entries:
                    if title.lower() in i.title.lower():
                        result_group.entries.append(i)
                        self.cur_win = 1
                self.cur_root = self.db.root_group
                self.sort_tables(True, True, True)
                self.e_highlight = 0

    def remove_results(self):
        '''Remove possible search result group'''

        for i in self.db.groups:
            if i.id_ == 0:
                try:
                    i.entries.clear()
                    i.remove_group()
                except KPError as err:
                    self.control.draw_text(self.changed,
                                           (1, 0, err.__str__()),
                                           (4, 0, 'Press any key.'))
                    if self.control.any_key() == -1:
                        self.close()
                    return False
                else:
                    if (self.g_highlight >= len(self.cur_root.children) and
                            self.g_highlight != 0):
                        self.g_highlight -= 1
                    self.e_highlight = 0
                break

    def edit_title(self):
        '''Edit title of group or entry'''

        if self.groups:
            std = 'Title: '
            if self.cur_win == 0:
                edit = Editor(self.control.stdscr, max_text_size=1,
                              inittext=self.groups[self.g_highlight].title,
                              win_location=(0, 1),
                              win_size=(1, self.control.xsize), title=std)()
                if edit == -1:
                    self.close()
                elif edit is not False:
                    if self.remote is True:
                        group_id = self.groups[self.g_highlight].id_
                        last_mod = (self.groups[self.g_highlight]
                                        .last_mod.timetuple())
                        db_buf = self.client().set_g_title(edit.encode(),
                                                           (str(group_id)
                                                            .encode()),
                                                           last_mod)
                        if self.check_answer(db_buf) is not False:
                            self.reload_remote_db(db_buf)
                    else:
                        self.groups[self.g_highlight].set_title(edit)
                        self.changed = True
            elif self.cur_win == 1:
                edit = Editor(self.control.stdscr, max_text_size=1,
                              inittext=self.entries[self.e_highlight].title,
                              win_location=(0, 1),
                              win_size=(1, self.control.xsize), title=std)()
                if edit == -1:
                    self.close()
                elif edit is not False:
                    if self.remote is True:
                        uuid = self.entries[self.e_highlight].uuid
                        last_mod = (self.entries[self.e_highlight]
                                        .last_mod.timetuple())
                        db_buf = self.client().set_e_title(edit.encode(),
                                                           uuid, last_mod)
                        if self.check_answer(db_buf) is not False:
                            self.reload_remote_db(db_buf)
                    else:
                        self.entries[self.e_highlight].set_title(edit)
                        self.changed = True

    def edit_username(self):
        '''Edit username of marked entry'''

        if self.entries:
            std = 'Username: '
            edit = Editor(self.control.stdscr, max_text_size=1,
                          inittext=self.entries[self.e_highlight].username,
                          win_location=(0, 1), win_size=(1, self.control.xsize),
                          title=std)()
            if edit == -1:
                self.close()
            elif edit is not False:
                if self.remote is True:
                    uuid = self.entries[self.e_highlight].uuid
                    last_mod = (self.entries[self.e_highlight]
                                    .last_mod.timetuple())
                    db_buf = self.client().set_e_user(edit.encode(),
                                                       uuid, last_mod)
                    if self.check_answer(db_buf) is not False:
                        self.reload_remote_db(db_buf)
                else:
                    self.changed = True
                    self.entries[self.e_highlight].set_username(edit)

    def edit_url(self):
        '''Edit URL of marked entry'''

        if self.entries:
            std = 'URL: '
            edit = Editor(self.control.stdscr, max_text_size=1,
                          inittext=self.entries[self.e_highlight].url,
                          win_location=(0, 1), win_size=(1, 
                          self.control.xsize), 
                          title=std)()
            if edit == -1:
                self.close()
            elif edit is not False:
                if self.remote is True:
                    uuid = self.entries[self.e_highlight].uuid
                    last_mod = (self.entries[self.e_highlight]
                                    .last_mod.timetuple())
                    db_buf = self.client().set_e_url(edit.encode(),
                                                     uuid, last_mod)
                    if self.check_answer(db_buf) is not False:
                        self.reload_remote_db(db_buf)
                else:
                    self.changed = True
                    self.entries[self.e_highlight].set_url(edit)

    def edit_comment(self):
        '''Edit comment of marked entry'''

        if self.entries:
            std = 'Comment: '
            edit = Editor(self.control.stdscr, title=std, win_location=(0, 1),
                          inittext=self.entries[self.e_highlight].comment)()
            if edit == -1:
                self.close()
            elif edit is not False:
                if self.remote is True:
                    uuid = self.entries[self.e_highlight].uuid
                    last_mod = (self.entries[self.e_highlight]
                                    .last_mod.timetuple())
                    db_buf = self.client().set_e_comment(edit.encode(),
                                                         uuid, last_mod)
                    if self.check_answer(db_buf) is not False:
                        self.reload_remote_db(db_buf)
                else:
                    self.changed = True
                    self.entries[self.e_highlight].set_comment(edit)

    def edit_password(self):
        '''Edit password of marked entry'''

        nav = self.control.gen_menu(1, ((1, 0, 'Use password generator (1)'),
                                     (2, 0, 'Type password by hand (2)'),
                                     (3, 0, 'No password (3)')))
        if nav == 1:
            password = self.control.gen_pass()
            if password == -1:
                self.close()
            elif password is False:
                return False
            if self.remote is True:
                uuid = self.entries[self.e_highlight].uuid
                last_mod = (self.entries[self.e_highlight]
                                .last_mod.timetuple())
                db_buf = self.client().set_e_pass(password.encode(),
                                                  uuid, last_mod)
                if self.check_answer(db_buf) is not False:
                    self.reload_remote_db(db_buf)
            else:
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
                    if self.remote is True:
                        uuid = self.entries[self.e_highlight].uuid
                        last_mod = (self.entries[self.e_highlight]
                                        .last_mod.timetuple())
                        db_buf = self.client().set_e_pass(password.encode(),
                                                          uuid, last_mod)
                        if self.check_answer(db_buf) is not False:
                            self.reload_remote_db(db_buf)
                    else:
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
            if self.remote is True:
                uuid = self.entries[self.e_highlight].uuid
                last_mod = (self.entries[self.e_highlight]
                                .last_mod.timetuple())
                db_buf = self.client().set_e_exp(
                    str(exp_date[0]).encode(), str(exp_date[1]).encode(), 
                    str(exp_date[2]).encode(), uuid, last_mod)
                if self.check_answer(db_buf) is not False:
                    self.reload_remote_db(db_buf)
            else:
                self.entries[self.e_highlight].set_expire(
                    exp_date[0], exp_date[1], exp_date[2],
                    exp[3], exp[4], exp[5])
                self.changed = True

    def client(self):
        return Client(logging.ERROR, 'client.log', 
                      self.address, 
                      self.port, self.db.password, 
                      self.db.keyfile, self.ssl, 
                      self.tls_dir)

    def check_answer(self, answer):
        if answer[:4] == 'FAIL' or answer[:4] == "[Err":
            self.control.draw_text(False,
                                   (1, 0, answer),
                                   (3, 0, 'Press any key.'))
            if self.control.any_key() == -1:
                self.close()
            return False

    def show_password(self):
        '''Show password of marked entry (e.g. copy it without xsel)'''

        if self.entries:
            self.control.draw_text(self.changed,
                                   (1, 0,
                                    self.entries[self.e_highlight].password))
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
                    if type(self.clip_timer) is threading.Timer:
                        self.clip_timer.cancel()
                    self.clip_timer = threading.Timer(
                        self.control.config['clip_delay'],
                        self.del_clipboard)
                    self.clip_timer.start()
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
        except FileNotFoundError:  # xsel not installed
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
                saverr = os.dup(2)
                os.close(1)
                os.close(2)
                os.open(os.devnull, os.O_RDWR)
                try:
                    webbrowser.open(url)
                finally:
                    os.dup2(saverr, 2)
                    os.dup2(savout, 1)

    def nav_down(self):
        '''Navigate down'''

        if self.cur_win == 0 and self.g_highlight < len(self.groups) - 1:
            ysize = self.control.group_win.getmaxyx()[0]
            if (self.g_highlight >= ysize - 4 + self.g_offset and
                not self.g_offset >= len(self.groups) - ysize + 4):
                self.g_offset += 1
            self.g_highlight += 1
            self.e_offset = 0
            self.e_highlight = 0
            self.sort_tables(False, True)
        elif self.cur_win == 1 and self.e_highlight < len(self.entries) - 1:
            ysize = self.control.entry_win.getmaxyx()[0]
            if (self.e_highlight >= ysize - 4 + self.e_offset and
                not self.e_offset >= len(self.entries) - ysize + 3):
                self.e_offset += 1
            self.e_highlight += 1

    def nav_up(self):
        '''Navigate up'''

        if self.cur_win == 0 and self.g_highlight > 0:
            if self.g_offset > 0 and self.g_highlight == self.g_offset:
                self.g_offset -= 1
            self.g_highlight -= 1
            self.e_offset = 0
            self.e_highlight = 0
            self.sort_tables(False, True)
        elif self.cur_win == 1 and self.e_highlight > 0:
            if self.e_offset > 0 and self.e_highlight == self.e_offset:
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

        # To prevent that a parent group is moved to a subgroup
        if (self.state == 3 and 
            self.move_object is self.groups[self.g_highlight]):
            return 

        if self.groups and self.groups[self.g_highlight].children:
            self.cur_root = self.groups[self.g_highlight]
            self.g_highlight = 0
            self.e_highlight = 0
            self.cur_win = 0
            self.sort_tables(True, False)

    def go2parent(self):
        '''Change to parent of current subgroups'''

        if not self.cur_root is self.db.root_group:
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
            ord('m'): self.move,
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
            ord('l'): self.nav_right,
            ord('r'): self.reload_remote_db}

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

        move_states = {
            ord('e'): self.exit2main,
            ord('q'): self.quit_kpc,
            4: self.quit_kpc,
            cur.KEY_DOWN: self.nav_down,
            ord('j'): self.nav_down,
            cur.KEY_UP: self.nav_up,
            ord('k'): self.nav_up,
            cur.KEY_LEFT: self.go2parent,
            ord('h'): self.go2parent,
            cur.KEY_RIGHT: self.go2sub,
            ord('l'): self.go2sub,
            NL: self.move_group_or_entry,
            cur.KEY_BACKSPACE: self.move2root,
            DEL: self.move2root,
            ESC: self.move_abort,
            cur.KEY_F1: self.control.move_help}

        exceptions = (ord('s'), ord('S'), ord('P'), ord('t'), ord('p'), 
                      ord('u'), ord('U'), ord('C'), ord('E'), ord('H'), 
                      ord('g'), ord('d'), ord('y'), ord('f'), ord('/'),
                      cur.KEY_F1, cur.KEY_RESIZE)

        while True:
            old_g_highlight = self.g_highlight
            old_e_highlight = self.e_highlight
            old_window = self.cur_win
            old_root = self.cur_root
    
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
                if c == ord('\t'):  # Switch group/entry view with tab.
                    if self.cur_win == 0:
                        c = cur.KEY_RIGHT
                    else:
                        c = cur.KEY_LEFT
                if c in unlocked_state:
                    unlocked_state[c]()
                if c == ord('e'):
                    return False
                # 'cause 'L' changes state
                if self.state == 0 or self.state == 4:  
                    if ((self.cur_win == 0 and
                         old_g_highlight != self.g_highlight) or
                        c in exceptions or
                        old_window != self.cur_win or
                        old_root is not self.cur_root):
                        self.control.show_groups(self.g_highlight, self.groups,
                                                 self.cur_win, self.g_offset,
                                                 self.changed, self.cur_root)
                    if ((self.cur_win == 1 and
                         old_e_highlight != self.e_highlight) or
                        c in exceptions or
                        old_window != self.cur_win or
                        old_g_highlight != self.g_highlight or
                        old_root is not self.cur_root):
                        self.control.show_entries(self.e_highlight, 
                                                  self.entries,
                                                  self.cur_win, self.e_offset)
            elif self.state == 1 and c in locked_state:
                locked_state[c]()
                if self.state == 1:  # 'cause 'L' changes state
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
            elif self.state > 2 and c in move_states:
                move_states[c]()
                if ((self.cur_win == 0 and
                     old_g_highlight != self.g_highlight) or
                    old_window != self.cur_win or
                    c == NL):
                    self.control.show_groups(self.g_highlight, self.groups,
                                             self.cur_win, self.g_offset,
                                             self.changed, self.cur_root)
                self.control.show_entries(self.e_highlight, self.entries,
                                          self.cur_win, self.e_offset)
