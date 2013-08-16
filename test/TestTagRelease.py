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
        self.new_version = '5.0.0-beta1'

    def has_new_prefixed_tag(self, repo):

        return repo.has_local_tag(repo.get_tag_prefix() + self.new_version)

    def testTag(self):
        """Test tagging on repository without submodules"""

        main(["tag-release", "--no-ask", self.new_version])
        self.assertTrue(self.has_new_prefixed_tag(self.sandbox))

    def testRecursiveTag(self):
        """Test recursive tagging on repository with submodules"""

        self.init_submodules()
        main(["tag-release", "--no-ask", self.new_version])
        self.assertTrue(self.has_new_prefixed_tag(self.sandbox))
        for submodule in self.sandbox.submodules:
            self.assertTrue(self.has_new_prefixed_tag(submodule))

    def testShallowTag(self):
        """Test shallow tagging on repository with submodules"""

        self.init_submodules()
        main(["tag-release", "--shallow", "--no-ask", self.new_version])
        self.assertTrue(self.has_new_prefixed_tag(self.sandbox))
        for submodule in self.sandbox.submodules:
            self.assertFalse(self.has_new_prefixed_tag(submodule))

    def testInvalidVersionNumber(self):
        """Test invalid version number"""

        self.assertRaises(Stop, main, ["tag-release", "--no-ask",
            'v5.0.0-beta1'])

    def testInvalidVersionPreReleaseNumber(self):
        """Test invalid version pre-release number"""

        self.assertRaises(Stop, main, ["tag-release", "--no-ask",
            '0.0.0beta1'])

    def testExitingTag(self):
        """Test existing tag"""

        # Create local tag and check local existence
        p = Popen(["git", "tag", 'v.' + self.new_version], stdout=subprocess.PIPE)
        self.assertTrue(self.sandbox.has_local_tag('v.' + self.new_version))

        # Test Stop is thrown by tag-release command
        self.assertRaises(Stop, main, ["tag-release", "--no-ask",
            self.new_version])

    def testInvalidTag(self):
        """Test invalid tag reference name"""

        # Test Stop is thrown by tag-release command
        self.assertRaises(Stop, main, ["tag-release", "--no-ask",
            self.new_version + ".."])

if __name__ == '__main__':
    unittest.main()
