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

from scc.framework import main, Stop
from scc.git import Rebase
from Sandbox import SandboxTest
from subprocess import Popen


class RebaseTest(SandboxTest):

    def setUp(self):

        super(RebaseTest, self).setUp()
        self.source_base = "dev_4_4"
        self.target_base = "develop"

    def rebase(self, *args):
        args = ["rebase", "--no-ask", str(self.pr.number),
                self.target_base] + list(args)
        main(args=args, items=[(Rebase.NAME, Rebase)])


class MockPR(object):

    def __init__(self, number):
        self.number = number


class TestRebaseStop(RebaseTest):

    def testUnfoundPR(self):

        self.pr = MockPR(0)
        self.assertRaises(Stop, self.rebase)

    def testNoCommonCommits(self):

        self.pr = MockPR(79)
        self.assertRaises(Stop, self.rebase)

    def testBadObject(self):

        self.pr = MockPR(112)
        self.assertRaises(Stop, self.rebase)


class TestRebaseNewBranch(RebaseTest):

    def setUp(self):

        super(TestRebaseNewBranch, self).setUp()

        # Open first PR against dev_4_4 branch
        self.source_branch = self.fake_branch(head=self.source_base)
        self.pr = self.open_pr(self.source_branch, self.source_base)

        # Define target branch for rebasing PR
        self.target_branch = "rebased/%s/%s" \
            % (self.target_base, self.source_branch)

    def tearDown(self):

        # Clean the initial branch. This will close the inital PRs
        self.sandbox.push_branch(":%s" % self.source_branch, remote=self.user)

        super(TestRebaseNewBranch, self).tearDown()

    def rebase(self, *args):
        args = ["rebase", "--no-ask", str(self.pr.number),
                self.target_base] + list(args)
        main(args=args, items=[(Rebase.NAME, Rebase)])

    def testPushExistingLocalBranch(self):

        # Rebase the PR locally
        self.sandbox.new_branch(self.target_branch)
        self.assertRaises(Stop, self.rebase)

    def testPushExistingRemoteBranch(self):

        self.sandbox.push_branch("HEAD:refs/heads/%s" % (self.target_branch),
                                 remote=self.user)
        self.assertRaises(Stop, self.rebase)
        self.sandbox.push_branch(":%s" % self.target_branch, remote=self.user)

    def testPushLocalRebase(self):

        # Rebase the PR locally
        self.rebase("--no-push", "--no-pr")

    def testPushNoFetch(self):

        # Rebase the PR locally
        self.rebase("--no-fetch", "--no-push", "--no-pr")

    def testPushRebaseNoPr(self):

        # Rebase the PR locally
        self.rebase("--no-pr")

    def testPushFullRebase(self):

        # Rebase the PR and push to Github
        self.rebase()

        # Check the last opened PR is the rebased one
        prs = list(self.sandbox.origin.get_pulls())
        self.assertEquals(prs[0].head.user.login, self.user)
        self.assertEquals(prs[0].head.ref, self.target_branch)

        # Clean the rebased branch
        self.sandbox.push_branch(":%s" % self.target_branch, remote=self.user)


class TestConflictingRebase(RebaseTest):

    def setUp(self):

        super(TestConflictingRebase, self).setUp()

        # Open first PR against dev_4_4 branch
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
        self.target_branch = "rebased/%s/%s" \
            % (self.target_base, self.source_branch)

    def tearDown(self):

        # Clean the initial branch. This will close the inital PRs
        self.sandbox.push_branch(":%s" % self.source_branch, remote=self.user)

        super(TestConflictingRebase, self).tearDown()

    def testPushRebaseContinue(self):

        # Rebase the PR locally
        self.assertRaises(Stop, self.rebase)

        f = open(self.filename, "w")
        f.write("hi")
        f.close()

        self.sandbox.add(self.filename)
        p = Popen(["git", "rebase", "--continue"])
        self.assertEquals(0, p.wait())

        self.rebase("--continue")

        # Clean the rebased branch
        self.sandbox.push_branch(":%s" % self.target_branch, remote=self.user)

if __name__ == '__main__':
    unittest.main()
