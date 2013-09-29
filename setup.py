#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2012 University of Dundee & Open Microscopy Environment
# All Rights Reserved.
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

from setuptools import setup
from scc.version import get_git_version


VERSION = get_git_version()
ZIP_SAFE = False

LONG_DESCRIPTION = open("README.rst", "r").read()

CLASSIFIERS = ["Development Status :: 4 - Beta",
               "Environment :: Console",
               "Intended Audience :: Developers",
               "License :: OSI Approved :: GNU General Public License v2"
               " (GPLv2)",
               "Operating System :: OS Independent",
               "Programming Language :: Python",
               "Topic :: Software Development :: Version Control"]

setup(name='scc',

      # Simple strings
      author='The Open Microscopy Team',
      author_email='ome-devel@lists.openmicroscopy.org.uk',
      description='OME tools for managing the git(hub) workflow',
      license='GPLv2',
      url='https://github.com/openmicroscopy/snoopycrimecop',

      # More complex variables
      packages=['scc'],
      include_package_data=True,
      install_requires=['PyGithub', 'argparse'],
      entry_points={'console_scripts': ['scc = scc.main:entry_point']},
      zip_safe=ZIP_SAFE,

      # Using global variables
      long_description=LONG_DESCRIPTION,
      classifiers=CLASSIFIERS,
      version=VERSION,
      )
