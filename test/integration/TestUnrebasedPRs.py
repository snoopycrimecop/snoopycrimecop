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

import unittest

from scc.framework import main, Stop, parsers
from scc.git import UnrebasedPRs
from Sandbox import SandboxTest


class TestUnrebasedPRs(SandboxTest):

    def setUp(self):
        super(TestUnrebasedPRs, self).setUp()
        self.branch1 = "dev_4_4"

    def unrebased_prs(self, *args):
        self.sandbox.checkout_branch("origin/" + self.branch1)
        args = ["unrebased-prs", self.branch1, self.branch2] + list(args)
        main(args=args, items=[(UnrebasedPRs.NAME, UnrebasedPRs)])

    def create_comment(self, HEAD, target_pr):
        parser, sub_parser = parsers()
        command = UnrebasedPRs(sub_parser)
        o, e = self.sandbox.communicate(
            "git", "log", "--oneline", "-n", "1", HEAD)
        sha1, num, rest = command.parse_pr(o.split("\n")[0])

        pr = self.sandbox.origin.get_issue(num)
        comment = pr.create_comment("--rebased-from #%s" % target_pr)
        return comment

    def testSelf(self):
        """Test unrebased-prs on same branch"""

        self.branch2 = "dev_4_4"
        self.unrebased_prs()

    def testShallow(self):
        """Test shallow unrebased-prs using last first-parent commit"""

        self.branch2 = "dev_4_4~"
        self.init_submodules()
        try:
            self.unrebased_prs("--shallow")
            self.fail()
        except Stop, s:
            self.assertEqual(s.rc, 1)

    def testRecursive(self):
        """Test unrebased-prs using last first-parent commit"""

        self.branch2 = "dev_4_4~"
        self.init_submodules()
        try:
            self.unrebased_prs()
            self.fail()
        except Stop, s:
            self.assertEqual(s.rc, 2)

    def testMismatch(self):
        """Test unrebased-prs mismatching PRs"""

        self.branch2 = "dev_4_4~2"
        comment = self.create_comment("origin/" + self.branch1, 1)

        try:
            try:
                self.unrebased_prs()
                self.fail()
            except Stop, s:
                self.assertEqual(s.rc, 2)
        finally:
            comment.delete()

    def testMismatchNoCheck(self):
        """Test unrebased-prs mismatching PRs"""

        self.branch2 = "dev_4_4~2"
        comment = self.create_comment("origin/" + self.branch1, 1)

        try:
            try:
                self.unrebased_prs("--no-check")
                self.fail()
            except Stop, s:
                self.assertEqual(s.rc, 1)
        finally:
            comment.delete()

if __name__ == '__main__':
    import logging
    logging.basicConfig()
    unittest.main()
