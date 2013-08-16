#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2012-2013 University of Dundee & Open Microscopy Environment
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

import os
import uuid
import shutil
import unittest
import tempfile

from scc import *
from Sandbox import *
from subprocess import Popen


class TestTagRelease(SandboxTest):

    def setUp(self):

        super(TestTagRelease, self).setUp()

        import random
        self.new_tag = '%s.%s.%s' % (random.randint(2,100),
            random.randint(0,100), random.randint(0,100))

    def get_tags(self):
        p = Popen(["git","tag"],stdout=subprocess.PIPE).communicate()[0]
        return p.split("\n")

    def testTag(self):
        """Test tagging on repository without submodules"""

        main(["tag-release", "--no-ask", self.new_tag])
        self.assertTrue('v.' + self.new_tag in self.get_tags())

    def testRecursiveTag(self):
        """Test recursive tagging on repository with submodules"""

        self.init_submodules()
        main(["tag-release", "--no-ask", self.new_tag])
        os.chdir(self.path)
        self.assertTrue('v.' + self.new_tag in self.get_tags())
        os.chdir("snoopys-sandbox-2")
        self.assertTrue(self.new_tag in self.get_tags())

    def testShallowTag(self):
        """Test shallow tagging on repository with submodules"""

        self.init_submodules()
        main(["tag-release", "--shallow", "--no-ask", self.new_tag])
        os.chdir(self.path)
        self.assertTrue('v.' + self.new_tag in self.get_tags())
        os.chdir("snoopys-sandbox-2")
        self.assertFalse(self.new_tag in self.get_tags())

    def testInvalidVersionNumber(self):
        """Test invalid version number"""

        self.assertRaises(Stop, main, ["tag-release", "--no-ask",
            'v0.0.0'])

    def testExitingTag(self):
        """Test existing tag"""

        # Create local tag and check local existence
        p = Popen(["git", "tag", 'v.' + self.new_tag], stdout=subprocess.PIPE)
        self.assertTrue('v.' + self.new_tag in self.get_tags())

        # Test Stop is thrown by tag-release command
        self.assertRaises(Stop, main, ["tag-release", "--no-ask",
            self.new_tag])

    def testInvalidTag(self):
        """Test invalid tag reference name"""

        # Test Stop is thrown by tag-release command
        self.assertRaises(Stop, main, ["tag-release", "--no-ask",
            self.new_tag + ".."])

if __name__ == '__main__':
    unittest.main()
