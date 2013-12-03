#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2013 University of Dundee & Open Microscopy Environment
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

import pytest
from scc.framework import main, Stop, parsers
from scc.git import UnrebasedPRs, PullRequest
from Sandbox import SandboxTest


class TestUnrebasedPRs(SandboxTest):

    def setup_method(self, method):
        super(TestUnrebasedPRs, self).setup_method(method)
        self.branch1 = "dev_4_4"
        self.args = None

    def unrebased_prs(self, *args):
        self.sandbox.checkout_branch("origin/" + self.branch1)
        args = ["unrebased-prs", self.branch1, self.branch2]
        if self.args:
            args += list(self.args)
        main(args=args, items=[(UnrebasedPRs.NAME, UnrebasedPRs)])

    def create_issue_comment(self, HEAD, target_pr):
        parser, sub_parser = parsers()
        command = UnrebasedPRs(sub_parser)
        o, e = self.sandbox.communicate(
            "git", "log", "--oneline", "-n", "1", HEAD)
        sha1, num, rest = command.parse_pr(o.split("\n")[0])

        pr = PullRequest(self.sandbox.origin.get_pull(num))
        comment = pr.create_issue_comment("--rebased-from #%s" % target_pr)
        return comment

    def testSelf(self):
        """Test unrebased-prs on same branch"""

        self.branch2 = "dev_4_4"
        self.unrebased_prs()

    @pytest.mark.parametrize('shallow', [False, True])
    def testShallow(self, shallow):
        """Test unrebased-prs using last first-parent commit"""

        self.branch2 = "dev_4_4~"
        self.init_submodules()
        if shallow:
            self.args = ['--shallow']
        try:
            self.unrebased_prs()
            pytest.fail('should stop')
        except Stop, s:
            if shallow:
                assert s.rc == 1
            else:
                assert s.rc == 2

    @pytest.mark.parametrize('check', [False, True])
    def testMismatch(self, check):
        """Test unrebased-prs mismatching PRs"""

        self.branch2 = "dev_4_4~2"
        comment = self.create_issue_comment("origin/" + self.branch1, 1)
        if not check:
            self.args = ['--no-check']
        try:
            try:
                self.unrebased_prs()
                pytest.fail('should stop')
            except Stop, s:
                if check:
                    assert s.rc == 2
                else:
                    assert s.rc == 1
        finally:
            comment.delete()
