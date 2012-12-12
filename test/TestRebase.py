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
        self.gh = get_github(get_token_or_user())
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
        except:
            shutil.rmtree(self.path)


class TestRebase(SandboxTest):

    def test(self):

        # Setup
        user = self.gh.get_login()
        gh_repo = GitHubRepository("openmicroscopy", "snoopys-sandbox", self.gh)

        # Create first PR from master
        name = self.fake_branch(head="origin/dev_4_4")
        self.sandbox.add_remote(user)
        self.sandbox.push_branch(name, remote=user)
        try:
            pr = gh_repo.open_pr(
                title="test %s" % name,
                description="This is a call to sandbox.open_pr",
                base="dev_4_4",
                head="%s:%s" % (user, name))

            main(["rebase", str(pr.number), "develop"])
            # If it succeeds, then we immediately close the PR
            self.sandbox.push_branch(":rebased/develop/%s"%name, remote=user)

        finally:
            # This will also clean the first PR
            self.sandbox.push_branch(":%s"%name, remote=user)


if __name__ == '__main__':
    unittest.main()
