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

import unittest

from scc import main
from Sandbox import SandboxTest


class TestUpdateSubmodules(SandboxTest):

    def setUp(self):

        super(TestUpdateSubmodules, self).setUp()
        self.init_submodules()
        self.add_remote()
        self.branch = "dev_4_4"
        self.sandbox.checkout_branch(self.branch)
        self.sandbox.reset()
        self.submodules_branch = "merge/%s/submodules" % self.branch

    def testMultipleUpdates(self):

        main(["update-submodules", "--no-ask", self.branch])
        p0 = self.sandbox.communicate("git", "log", "--oneline", "-n", "1",
                                      "HEAD")[0]
        main(["update-submodules", "--no-ask", self.branch])
        p1 = self.sandbox.communicate("git", "log", "--oneline", "-n", "1",
                                      "HEAD")[0]
        self.assertEqual(p0, p1)

    def testPushNoPR(self):

        main(["update-submodules", "--no-ask", self.branch, "--push",
              self.submodules_branch, "--no-pr"])
        self.sandbox.push_branch(":%s" % self.submodules_branch,
                                 remote=self.user)

    def testPushOpenPR(self):

        main(["update-submodules", "--no-ask", self.branch, "--push",
              self.submodules_branch])
        prs = list(self.sandbox.origin.get_pulls())
        self.assertEquals(prs[0].head.user.login, self.user)
        self.assertEquals(prs[0].head.ref, self.submodules_branch)
        self.sandbox.push_branch(":%s" % self.submodules_branch,
                                 remote=self.user)

    def testPushUpdatePR(self):

        main(["update-submodules", "--no-ask", self.branch, "--push",
              self.submodules_branch])
        prs = list(self.sandbox.origin.get_pulls())
        pr = prs[0]

        self.sandbox.checkout_branch(self.branch)
        self.sandbox.reset()
        main(["update-submodules", "--no-ask", self.branch, "--push",
              self.submodules_branch])
        prs = list(self.sandbox.origin.get_pulls())
        self.assertEqual(prs[0].number, pr.number)
        self.sandbox.push_branch(":%s" % self.submodules_branch,
                                 remote=self.user)

if __name__ == '__main__':
    import logging
    logging.basicConfig()
    unittest.main()
