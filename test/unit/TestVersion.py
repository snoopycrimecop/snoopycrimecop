#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2013 University of Dundee & Open Microscopy Environment
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

import sys
import os
import unittest
from StringIO import StringIO

from scc.framework import main
from scc.version import call_git_describe, Version, version_file


class TestVersion(unittest.TestCase):

    def setUp(self):
        super(TestVersion, self).setUp()
        self.output = StringIO()
        self.saved_stdout = sys.stdout
        sys.stdout = self.output
        if os.path.isfile(version_file):
            os.rename(version_file, version_file + '.bak')
        self.assertFalse(os.path.isfile(version_file))

    def tearDown(self):
        self.output.close()
        sys.stdout = self.saved_stdout
        if os.path.isfile(version_file + '.bak'):
            os.rename(version_file + '.bak', version_file)
        super(TestVersion, self).tearDown()

    def read_version_file(self):
        version = None
        f = open(version_file)
        try:
            version = f.readlines()[0]
        finally:
            f.close()
        return version.strip()

    def testVersionOutput(self):
        main(["version"], items=[("version", Version)])
        self.assertEquals(self.output.getvalue().rstrip(),
                          call_git_describe())

    def testVersionFile(self):
        main(["version"], items=[("version", Version)])
        self.assertTrue(os.path.isfile(version_file))
        self.assertEquals(self.output.getvalue().rstrip(),
                          self.read_version_file())

    def testVersionOverwrite(self):
        f = open(version_file, 'w')
        f.write('test\n')
        f.close()
        self.assertEquals('test', self.read_version_file())
        try:
            main(["version"], items=[("version", Version)])
            self.assertEquals(self.output.getvalue().rstrip(),
                              self.read_version_file())
        finally:
            os.remove(version_file)

    def testNonGitRepository(self):
        cwd = os.getcwd()
        try:
            # Move to a non-git repository and ensure call_git_describe
            # returns None
            os.chdir('..')
            self.assertTrue(call_git_describe() is None)
            main(["version"], items=[("version", Version)])
            self.assertFalse(self.output.getvalue().rstrip() is None)
        finally:
            os.chdir(cwd)

if __name__ == '__main__':
    unittest.main()
