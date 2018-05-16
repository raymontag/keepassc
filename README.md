KeePassC v.1.8.0
================

* License: ISC
* Author: Karsten-Kai König <grayfox@outerhaven.de>
** License of editor.py: MIT
** Author of editor.py: Scott Hansen <firecat four one five three at gmail dot com>
** Github: https://github.com/firecat53/py_curses_editor
* Stable download: https://github.com/raymontag/keepassc/tarball/master
* Website: http://raymontag.github.com/keepassc
* Bug tracker: https://github.com/raymontag/keepassc/issues?state=open
* Git: git://github.com/raymontag/keepassc.git

Features:
---------
KeePassC is a password manager fully compatible to KeePass v.1.x and KeePassX. That is, your
password database is fully encrypted with AES.

KeePassC is written in Python 3 and comes with a curses-interface. It is completely controlled
with the keyboard.

Since v.1.6.0 network usage is implemented.

Install:
--------

First check if Python 3 is executed on your system with 'python' (e.g. ArchLinux) or with 'python3' (e.g. Fedora). If the latter applies open bin/keepassc with an editor of your choice and edit the first line to '#!/usr/bin/env python3', if the former do nothing.

If all dependencies are fulfilled type 'python setup.py install' resp. 'python3 setup.py install' in the root directory of KeePassC.

Furthermore check if the directory /var/empty exists (normally it should but it seems that is doesn't on Debian and derivates). If not execute as root user 'mkdir -m 755 /var/empty'.

Usage:
------
Start the program with 'keepassc'. To get help type 'F1' while KeePassC is executed and you will see usage
information to the current window (not in main menu).

For a short introduction have a look at http://raymontag.github.com/keepassc/docu.html. Also use 'man keepassc'.

For help using the server have a look at http://raymontag.github.com/keepassc/server.html, 'man keepassc-server' and 'man keepassc-agent'.

You can get help at any time by pressing F1 in the file or database browser.

Dependencies:
-------------

* Python 3 (>= 3.3)
* kppy http://www.nongnu.org/kppy
* 
* xsel (optional but necessary if you want to copy usernames and passwords to clipboard)  http://www.vergenet.net/~conrad/software/xsel/
* A POSIX-compatible operating system

Copyright (c) 2012-2018 Karsten-Kai König <grayfox@outerhaven.de>

Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is hereby granted, provided that the above copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

