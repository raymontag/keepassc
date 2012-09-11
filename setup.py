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

setup( 
     name = "keepassc", 
     version = "1.2", 
     author = "Karsten-Kai König", 
     author_email = "kkoenig@posteo.de",
     url = "",
     download_url = "",
     description = "A password manager that is fully compatible to KeePass v.1.x and KeePassX",
     scripts = ['keepassc'],
     classifiers = [
        'Operating System :: POSIX',
        'License :: OSI Approved :: GNU Lesser General Public License v3 or later (GPLv3+)',
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console :: Curses'],
     license = "GPL v3 or later"
     )
