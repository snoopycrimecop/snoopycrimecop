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

import os
import uuid
import shutil
import unittest
import tempfile

from scc import *
from subprocess import *

sandbox_url = "git@github.com:openmicroscopy/snoopys-sandbox.git"

class SandboxTest(unittest.TestCase):

    def setUp(self):
        self.gh = get_github()
        self.path = tempfile.mkdtemp("","sandbox-", ".")
        self.path = os.path.abspath(self.path)
        try:
            p = Popen(["git", "clone", sandbox_url, self.path])
            self.assertEquals(0, p.wait())
            self.sandbox = get_git_repo(self.path)
        except:
            shutil.rmtree(self.path)
            raise

    def unique_file(self):
        """
        Call open() with a unique file name
        and "w" for writing
        """

        name = os.path.join(self.path, str(uuid.uuid4()))
        return open(name, "w")

    def tearDown(self):
        try:
            self.sandbox.cleanup()
        except:
            shutil.rmtree(self.path)

class TestRebase(SandboxTest):

    def test(self):
        f = self.unique_file()
        f.write("hi")
        f.close()
        name = f.name
        self.sandbox.add(f.name)

        name = name.split(os.path.sep)[-1]
        self.sandbox.commit("Writing %s" % name)
        self.sandbox.get_status()
        self.sandbox.name_branch(name)
        # This needs to be to a fork!
        #self.sandbox.push_branch(name)

if __name__ == '__main__':
    unittest.main()
