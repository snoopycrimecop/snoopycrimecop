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

import unittest

from scc import main, Stop
from Sandbox import SandboxTest


class TestCheckMilestone(SandboxTest):

    def testNonExistingTag(self):
        self.assertRaises(Stop, main, ["check-milestone", "--no-ask",
                                       "v.0.0.0", "HEAD"])

    def testNonExistingMilestone(self):
        self.assertRaises(Stop, main, ["check-milestone", "--no-ask",
                                       "v.1.0.0", "HEAD", "--set", "0.0.0"])

    def testCheckMilestone(self):
        main(["check-milestone", "--no-ask", "v.1.0.0", "v.1.1.1-TEST"])

if __name__ == '__main__':
    unittest.main()
