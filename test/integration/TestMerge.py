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

from scc import main, Stop
from Sandbox import SandboxTest


class TestMerge(SandboxTest):

    def setUp(self):

        super(TestMerge, self).setUp()
        self.init_submodules()
        self.base = "dev_4_4"
        self.merge_branch = "merge/dev_4_4/test"
        self.branch = self.fake_branch(head=self.base)
        self.pr = self.open_pr(self.branch, self.base)
        self.sandbox.checkout_branch(self.base)
        self.assertFalse(self.isMerged())

    def isMerged(self, ref='HEAD'):
        revlist, o = self.sandbox.communicate("git", "rev-list", ref)
        return self.pr.head.sha in revlist.splitlines()

    def tearDown(self):
        # Clean the initial branch. This will close the inital PRs
        self.sandbox.push_branch(":%s" % self.branch, remote=self.user)
        super(TestMerge, self).tearDown()

    def testMerge(self):

        main(["merge", "--no-ask", self.base])
        self.assertTrue(self.isMerged())

    def testShallowMerge(self):

        pre_merge = self.sandbox.communicate("git", "submodule", "status")[0]
        main(["merge", "--no-ask", "--shallow", self.base])
        self.assertTrue(self.isMerged())
        post_merge = self.sandbox.communicate("git", "submodule", "status")[0]
        self.assertEqual(pre_merge, post_merge)

    def testMergePush(self):

        main(["merge", "--no-ask", self.base, "--push", self.merge_branch])
        self.sandbox.fetch(self.user)
        self.assertTrue(self.isMerged("%s/%s"
                                      % (self.user, self.merge_branch)))
        self.sandbox.push_branch(":%s" % self.merge_branch, remote=self.user)

    def testRemote(self):

        self.sandbox.call("git", "remote", "rename", "origin", "gh")
        # scc merge without --remote should fail
        self.assertRaises(Stop, main, ["merge", "--no-ask", self.base])
        # scc merge with --remote setup should pass
        main(["merge", "--no-ask", self.base, "--remote", "gh"])
        self.assertTrue(self.isMerged())

    def testStatus(self):

        from github.GithubObject import NotSet
        commit = self.pr.head.repo.get_commit(self.pr.head.sha)
        # no status
        main(["merge", "--no-ask", "-S", self.base])
        self.assertFalse(self.isMerged())

        # pending state
        commit.create_status("pending", NotSet, "Pending state test")
        main(["merge", "--no-ask", "-S", self.base])
        self.assertFalse(self.isMerged())

        # failure state
        commit.create_status("failure", NotSet, "Failure state test")
        main(["merge", "--no-ask", "-S", self.base])
        self.assertFalse(self.isMerged())

        # success state
        commit.create_status("success", NotSet, "Success state test")
        main(["merge", "--no-ask", "-S", self.base])
        self.assertTrue(self.isMerged())

if __name__ == '__main__':
    import logging
    logging.basicConfig()
    unittest.main()
