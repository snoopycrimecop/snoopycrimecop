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
from subprocess import Popen


class TestRebase(SandboxTest):

    def setUp(self):

        super(TestRebase, self).setUp()
        self.target_base = "develop"

    def testUnfoundPR(self):

        self.assertRaises(Stop, main,
                          ["rebase", "--no-ask", "0", self.target_base])

    def testNoCommonCommits(self):

        self.assertRaises(Stop, main, ["rebase", "--no-ask", "79",
                          self.target_base])

    def testBadObject(self):

        self.assertRaises(Stop, main, ["rebase", "--no-ask", "112",
                          self.target_base])


class TestRebaseNewBranch(SandboxTest):

    def setUp(self):

        super(TestRebaseNewBranch, self).setUp()

        # Open first PR against dev_4_4 branch
        self.source_base = "dev_4_4"
        self.source_branch = self.fake_branch(head=self.source_base)
        self.pr = self.open_pr(self.source_branch, self.source_base)

        # Define target branch for rebasing PR
        self.target_base = "develop"
        self.target_branch = "rebased/%s/%s" \
            % (self.target_base, self.source_branch)

    def tearDown(self):

        # Clean the initial branch. This will close the inital PRs
        self.sandbox.push_branch(":%s" % self.source_branch, remote=self.user)

        super(TestRebaseNewBranch, self).tearDown()

    def testPushExistingLocalBranch(self):

        # Rebase the PR locally
        self.sandbox.new_branch(self.target_branch)
        self.assertRaises(Stop, main,
                          ["rebase", "--no-ask", str(self.pr.number),
                           self.target_base])

    def testPushExistingRemoteBranch(self):

        self.sandbox.push_branch("HEAD:refs/heads/%s" % (self.target_branch),
                                 remote=self.user)
        self.assertRaises(Stop, main,
                          ["rebase", "--no-ask", str(self.pr.number),
                           self.target_base])
        self.sandbox.push_branch(":%s" % self.target_branch, remote=self.user)

    def testPushLocalRebase(self):

        # Rebase the PR locally
        main(["rebase",
              "--no-ask",
              "--no-push",
              "--no-pr",
              str(self.pr.number),
              self.target_base])

    def testPushNoFetch(self):

        # Rebase the PR locally
        main(["rebase",
              "--no-fetch",
              "--no-ask",
              "--no-push",
              "--no-pr",
              str(self.pr.number),
              self.target_base])

    def testPushRebaseNoPr(self):

        # Rebase the PR locally
        main(["rebase",
              "--no-ask",
              "--no-pr",
              str(self.pr.number),
              self.target_base])

    def testPushFullRebase(self):

        # Rebase the PR and push to Github
        main(["rebase",
              "--no-ask",
              str(self.pr.number),
              self.target_base])

        # Check the last opened PR is the rebased one
        prs = list(self.sandbox.origin.get_pulls())
        self.assertEquals(prs[0].head.user.login, self.user)
        self.assertEquals(prs[0].head.ref, self.target_branch)

        # Clean the rebased branch
        self.sandbox.push_branch(":%s" % self.target_branch, remote=self.user)


class TestConflictingRebase(SandboxTest):

    def setUp(self):

        super(TestConflictingRebase, self).setUp()

        # Open first PR against dev_4_4 branch
        self.source_base = "dev_4_4"
        self.source_branch = 'readme'
        self.filename = 'README.md'

        f = open(self.filename, "w")
        f.write("hi")
        f.close()

        self.sandbox.new_branch(self.source_branch, head=self.source_base)
        self.sandbox.add(self.filename)

        self.sandbox.commit("Writing %s" % self.filename)
        self.sandbox.get_status()

        self.pr = self.open_pr(self.source_branch, self.source_base)

        # Define target branch for rebasing PR
        self.target_base = "develop"
        self.target_branch = "rebased/%s/%s" \
            % (self.target_base, self.source_branch)

    def tearDown(self):

        # Clean the initial branch. This will close the inital PRs
        self.sandbox.push_branch(":%s" % self.source_branch, remote=self.user)

        super(TestConflictingRebase, self).tearDown()

    def testPushRebaseContinue(self):

        # Rebase the PR locally
        self.assertRaises(Stop, main, ["rebase",
                                       "--no-ask",
                                       str(self.pr.number),
                                       self.target_base])

        f = open(self.filename, "w")
        f.write("hi")
        f.close()

        self.sandbox.add(self.filename)
        p = Popen(["git", "rebase", "--continue"])
        self.assertEquals(0, p.wait())

        main(["rebase",
              "--no-ask",
              "--continue",
              str(self.pr.number),
              self.target_base])

        # Clean the rebased branch
        self.sandbox.push_branch(":%s" % self.target_branch, remote=self.user)

if __name__ == '__main__':
    unittest.main()
