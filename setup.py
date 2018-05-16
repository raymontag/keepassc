from os import mkdir, stat
from stat import ST_MODE

from distutils.core import setup

setup(name = "keepassc",
      version = "1.8.0",
      author = "Karsten-Kai König, Scott Hansen",
      author_email = "grayfox@outerhaven.de",
      url = "http://raymontag.github.com/keepassc",
      download_url = "https://github.com/raymontag/keepassc/tarball/master",
      description = "A password manager that is fully compatible to KeePass v.1.x and KeePassX",
      packages = ['keepassc'],
      scripts = ['bin/keepassc', 'bin/keepassc-server', 'bin/keepassc-agent'],
      install_requires = ['kppy', 'PyCryptodome'],
      classifiers = [
          'Programming Language :: Python :: 3.3',
          'Operating System :: POSIX',
          'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
          'Development Status :: 5 - Production/Stable',
          'Environment :: Console :: Curses'],
      license = "ISC, MIT",
      data_files = [('share/man/man1', ['keepassc.1', 'keepassc-server.1', 'keepassc-agent.1']),
                    ('share/doc/keepassc', ['README.md', 'LICENSE.md', 'CHANGELOG'])],
)
