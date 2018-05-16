'''
Copyright (C) 2012-2015 Karsten-Kai König <grayfox@outerhaven.de>
import logging
from os import mkdir, stat
from stat import ST_MODE

This file is part of keepassc.
from setuptools import setup
from setuptools.command.install import install

keepassc is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or at your
option) any later version.
class CreateVarEmpty(install):
    """Create /var/empty if it doesn't exist"""
    def run(self):
        install.run(self)

keepassc is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
for more details.
        distutils.log.set_verbosity(distutils.log.DEBUG)
        try:
            mkdir("/var/", 0o775)
        except OSError:
            pass

You should have received a copy of the GNU General Public License along
with keepassc.  If not, see <http://www.gnu.org/licenses/>.
'''


from distutils.core import setup
        try:
            mkdir("/var/empty", 0o555)
        except OSError:
            pass

setup(name = "keepassc",
      version = "1.7.0",
      author = "Karsten-Kai König, Scott Hansen",
      author_email = "grayfox@outerhaven.de",
      url = "http://raymontag.github.com/keepassc",
      download_url = "https://github.com/raymontag/keepassc/tarball/master",
      description = "A password manager that is fully compatible to KeePass v.1.x and KeePassX",
      packages = ['keepassc'],
      scripts = ['bin/keepassc', 'bin/keepassc-server', 'bin/keepassc-agent'],
      install_requires = ['kppy', 'PyCrypto'],
      classifiers = [
          'Programming Language :: Python :: 3.3',
          'Operating System :: POSIX',
          'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
          'Development Status :: 5 - Production/Stable',
          'Environment :: Console :: Curses'],
      license = "GPL v3 or later, MIT",
      data_files = [('share/man/man1', ['keepassc.1', 'keepassc-server.1', 'keepassc-agent.1']),
                    ('share/doc/keepassc', ['README', 'COPYING', 'CHANGELOG'])]
      cmdclass={
          'install': CreateVarEmpty,
      },
)
