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

from scc.framework import main
from scc.git import UpdateSubmodules
from Sandbox import SandboxTest


class TestUpdateSubmodules(SandboxTest):

    def setup_method(self, method):

        super(TestUpdateSubmodules, self).setup_method(method)
        self.init_submodules()
        self.add_remote()
        self.branch = "dev_4_4"
        self.sandbox.checkout_branch(self.branch)
        self.sandbox.reset()
        self.submodules_branch = "merge/%s/submodules" % self.branch

    def teardown_method(self, method):
        if self.sandbox.has_remote_branch(
                self.submodules_branch, remote=self.user):
            self.sandbox.push_branch(":%s" % self.submodules_branch,
                                     remote=self.user)
        super(TestUpdateSubmodules, self).teardown_method(method)

    def update_submodules(self, *args):
        args = ["update-submodules", "--no-ask", self.branch] + list(args)
        main(args=args, items=[(UpdateSubmodules.NAME, UpdateSubmodules)])

    def testMultipleUpdates(self):

        self.update_submodules()
        p0 = self.sandbox.communicate("git", "log", "--oneline", "-n", "1",
                                      "HEAD")[0]
        self.update_submodules()
        p1 = self.sandbox.communicate("git", "log", "--oneline", "-n", "1",
                                      "HEAD")[0]
        assert p0 == p1

    def testPushNoPR(self):

        self.update_submodules("--push", self.submodules_branch, "--no-pr")

    def testPushOpenPR(self):

        self.update_submodules("--push", self.submodules_branch)
        pr = self.sandbox.origin.get_pulls()[0]
        assert pr.head.user.login == self.user
        assert pr.head.ref == self.submodules_branch

    def testPushUpdatePR(self):

        self.update_submodules("--push", self.submodules_branch)
        pr = self.sandbox.origin.get_pulls()[0]

        self.sandbox.checkout_branch(self.branch)
        self.sandbox.reset()
        self.update_submodules("--push", self.submodules_branch)
        assert self.sandbox.origin.get_pulls()[0].number == pr.number
