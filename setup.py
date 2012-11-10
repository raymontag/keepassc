'''
Copyright (C) 2012 Karsten-Kai König <kkoenig@posteo.de>

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


from distutils.core import setup
from distutils.command.install import install
from os import makedirs
from os.path import isdir
from shutil import copyfile

class manpage_install(install):
    def run(self):
        install.run(self)
        if not isdir('/usr/share/man/man1/'):
            makedirs('/usr/share/man/man1/')
        copyfile('keepassc.1', '/usr/share/man/man1/keepassc.1')

setup( 
     name = "keepassc", 
     version = "1.4", 
     author = "Karsten-Kai König", 
     author_email = "kkoenig@posteo.de",
     url = "www.nongnu.org/keepassc",
     download_url = "http://download-mirror.savannah.gnu.org/releases/keepassc/",
     description = "A password manager that is fully compatible to KeePass v.1.x and KeePassX",
     scripts = ['keepassc'],
     classifiers = [
        'Operating System :: POSIX',
        'License :: OSI Approved :: GNU Lesser General Public License v3 or later (GPLv3+)',
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console :: Curses'],
     license = "GPL v3 or later",
     cmdclass={'install':manpage_install}
     )
