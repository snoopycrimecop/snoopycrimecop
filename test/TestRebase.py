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
from subprocess import *


class TestRebase(SandboxTest):

    def setUp(self):

        super(TestRebase, self).setUp()

        # Open first PR against dev_4_4 branch
        self.source_base = "dev_4_4"
        self.source_branch = self.fake_branch(head=self.source_base)
        self.pr = self.open_pr(self.source_branch, self.source_base)

        # Define target branch for rebasing PR
        self.target_base="develop"
        self.target_branch="rebased/%s/%s" % (self.target_base,
            self.source_branch)

    def tearDown(self):

        # Clean the initial branch. This will close the inital PRs
        self.sandbox.push_branch(":%s"%self.source_branch, remote=self.user)

        super(TestRebase, self).tearDown()

    def testLocalRebase(self):

        # Rebase the PR locally
        main(["rebase", \
            "--token=%s"%self.token, \
            "--no-ask", \
            "--no-push", \
            "--no-pr", \
            str(self.pr.number), \
            self.target_base])

    def testRebasePush(self):

        # Rebase the PR locally
        main(["rebase", \
            "--token=%s"%self.token, \
            "--no-ask", \
            "--no-pr", \
            str(self.pr.number), \
            self.target_base])

    def testRebasePushPR(self):

        # Rebase the PR and push to Github
        main(["rebase", \
            "--token=%s"%self.token, \
            "--no-ask", \
            str(self.pr.number), \
            self.target_base])

        # Check the last opened PR is the rebased one
        prs = list(self.sandbox.origin.get_pulls())
        self.assertEquals(prs[0].head.user.login, self.user)
        self.assertEquals(prs[0].head.ref, self.target_branch)

        # Clean the rebased branch
        self.sandbox.push_branch(":%s"%self.target_branch, remote=self.user)

if __name__ == '__main__':
    unittest.main()
