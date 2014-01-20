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
        self.branch2 = ""
        self.args = ["unrebased-prs"]

    def unrebased_prs(self):
        self.sandbox.checkout_branch("origin/" + self.branch1)
        self.args += [self.branch1, self.branch2]
        main(args=self.args, items=[(UnrebasedPRs.NAME, UnrebasedPRs)])

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
    @pytest.mark.parametrize('checklinks', [False, True])
    def testMultiBranch(self, shallow, checklinks):
        """Test unrebased-prs mismatching PRs"""

        self.branch2 = "develop"
        self.init_submodules()
        comment = self.create_issue_comment("origin/" + self.branch1, 1)
        if not checklinks:
            self.args += ['--no-check']
        if shallow:
            self.args += ['--shallow']
        try:
            try:
                self.unrebased_prs()
                pytest.fail('should stop')
            except Stop, s:
                unrebased_count = 3
                if checklinks:
                    unrebased_count += 1
                if not shallow:
                    unrebased_count += 1
                assert s.rc == unrebased_count
        finally:
            comment.delete()
