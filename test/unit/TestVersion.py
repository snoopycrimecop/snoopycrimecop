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
import unittest
from StringIO import StringIO

from scc.framework import main
from scc.version import call_git_describe, Version


class TestVersion(unittest.TestCase):

    def setUp(self):
        super(TestVersion, self).setUp()
        self.output = StringIO()
        self.saved_stdout = sys.stdout
        sys.stdout = self.output

    def tearDown(self):
        self.output.close()
        sys.stdout = self.saved_stdout
        super(TestVersion, self).tearDown()

    def testVersion(self):
        main(["version"], items=[("version", Version)])
        self.assertEquals(self.output.getvalue().rstrip(),
                          call_git_describe())

if __name__ == '__main__':
    unittest.main()
