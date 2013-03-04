#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2012 Glencoe Software, Inc. All Rights Reserved.
# Use is subject to license terms supplied in LICENSE.txt
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""
SCC distribution script
"""

LONG_DESCRIPTION = open("README.rst", "r").read()

CLASSIFIERS = ["Development Status :: 4 - Beta",
               "Environment :: Console",
               "Intended Audience :: Developers",
               "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
               "Operating System :: OS Independent",
               "Programming Language :: Python",
               "Topic :: Software Development :: Version Control"]

from scc import __version__
from setuptools import setup
setup(name='scc',
      version=__version__,

      # Simple strings
      author='The Open Microscopy Team',
      author_email='ome-devel@lists.openmicroscopy.org.uk',
      description='OME tools for managing the git(hub) workflow',
      license='GPLv2',
      url='https://github.com/openmicroscopy/snoopycrimecop',
      download_url = 'https://github.com/openmicroscopy/snoopycrimecop/tarball/%s' % __version__,

      # More complex variables
      py_modules = ['scc'],
      install_requires=['PyGithub', 'argparse'],
      entry_points={ 'console_scripts': ['scc = scc:entry_point'] },
      package_data = {'': ['LICENSE.txt', 'README.rst']},
      zip_safe = True,

      # Using global variables
      long_description=LONG_DESCRIPTION,
      classifiers=CLASSIFIERS,
      )
