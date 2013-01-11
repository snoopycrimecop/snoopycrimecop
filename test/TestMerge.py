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
import unittest

from subprocess import Popen

from scc import *
from Sandbox import SandboxTest
from Mock import MockTest


class UnitTestMerge(MockTest):

    def setUp(self):
        MockTest.setUp(self)

        self.scc_parser, self.sub_parser = parsers()
        self.merge = Merge(self.sub_parser)

    def testIntersect(self):
        self.assertEquals([3], self.gh_repo.intersect([1,2,3], [3,4,5]))

    def testFiltering(self):
        test_filter = {
            "label": ["test_label"],
            "user": ["test_user"],
            "pr": ["1"],
            }
        self.assertFalse(self.gh_repo.run_filter(test_filter, [], None, "0"))
        self.assertTrue(self.gh_repo.run_filter(test_filter, ["test_label"], None, "0"))
        self.assertTrue(self.gh_repo.run_filter(test_filter, ["test_label", "test_label_2"], None, "0"))
        self.assertTrue(self.gh_repo.run_filter(test_filter, [], "test_user", "0"))
        self.assertTrue(self.gh_repo.run_filter(test_filter, [], None, "1"))
        self.assertTrue(self.gh_repo.run_filter(test_filter, ["test_label"], "test_user", "1"))

class TestMerge(SandboxTest):

    def setUp(self):
        
        super(TestMerge, self).setUp()
        
        # Setup
        self.user = self.gh.get_login()
        gh_repo = self.gh.gh_repo("snoopys-sandbox", "openmicroscopy")

        try:
            p = Popen(["git", "submodule", "update", "--init"])
            self.assertEquals(0, p.wait())
        except:
            os.chdir(self.path)
            raise
            
    def test(self):

        main(["merge","dev_4_4"])

    def testPush(self):

        main(["merge","dev_4_4" ,"--push", "test"])
        # This will clean the pushed branch
        remote = "git@github.com:%s/" % (self.user) + "%s.git"
        self.sandbox.rpush(":test", remote=remote)
            

if __name__ == '__main__':
    import logging
    logging.basicConfig()
    unittest.main()
