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
        unittest.TestCase.setUp(self)
        self.cwd = os.getcwd()
        # Only read from the invoking repository which will
        # usually be the scc.git itself.
        self.token = get_token_or_user(local=True)
        self.gh = get_github(self.token, dont_ask=True)
        self.path = tempfile.mkdtemp("","sandbox-", ".")
        self.path = os.path.abspath(self.path)
        try:
            p = Popen(["git", "clone", sandbox_url, self.path])
            self.assertEquals(0, p.wait())
            self.sandbox = self.gh.git_repo(self.path)
        except:
            shutil.rmtree(self.path)
            raise
        # If we succeed, then we change to this dir.
        os.chdir(self.path)

    def uuid(self):
        """
        Return a string representing a uuid.uuid4
        """
        return str(uuid.uuid4())

    def unique_file(self):
        """
        Call open() with a unique file name
        and "w" for writing
        """

        name = os.path.join(self.path, self.uuid())
        return open(name, "w")

    def fake_branch(self, head="master"):
        f = self.unique_file()
        f.write("hi")
        f.close()

        path = f.name
        name = f.name.split(os.path.sep)[-1]

        self.sandbox.new_branch(name, head=head)
        self.sandbox.add(path)

        self.sandbox.commit("Writing %s" % name)
        self.sandbox.get_status()
        return name

    def tearDown(self):
        try:
            self.sandbox.cleanup()
        finally:
            try:
                shutil.rmtree(self.path)
            finally:
                # Return to cwd regardless.
                os.chdir(self.cwd)
        unittest.TestCase.tearDown(self)
