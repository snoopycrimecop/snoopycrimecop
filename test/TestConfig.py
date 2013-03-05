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

import os
import unittest

from scc import git_config
from scc import get_token_or_user
from scc import get_github
from Sandbox import SandboxTest


class TestGithub(unittest.TestCase):

    def testFailingConnection(self):
        self.assertRaises(SystemExit,  get_github, "openmicroscopy",
            dont_ask=True)
        self.assertRaises(SystemExit,  get_github, "openmicroscopy",
            password ="bad_password")
        self.assertRaises(SystemExit,  get_github, "openmicroscopy",
            password ="bad_password", dont_ask=True)

class TestEmptyConfig(SandboxTest):

    def testChecksForNoUser(self):
        os.chdir(self.path)
        self.assertEquals(None, get_token_or_user(local=True))


class TestSetConfig(SandboxTest):

    def testChecksForNoUser(self):
        os.chdir(self.path)
        uuid = self.uuid()
        git_config("github.user", value=uuid, local=True)
        self.assertEquals(uuid, get_token_or_user(local=True))

if __name__ == '__main__':
    unittest.main()
