#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2012 University of Dundee & Open Microscopy Environment
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
        self.test_filter = {
            "label": ["test_label"],
            "user": ["test_user"],
            "pr": ["1"],
            }
        self.default_exclude = ['exclude']
        self.default_include = ['include']
        self.default_default = 'org'

    def testIntersect(self):
        self.assertEquals([3], self.gh_repo.intersect([1,2,3], [3,4,5]))

    def testSelfFilter(self):
        self.assertTrue(self.gh_repo.run_filter(self.test_filter, self.test_filter))

    def testWrongFilter(self):
        pr_attributes = {"label": [], "user": [None], "pr": ["0"]}
        self.assertFalse(self.gh_repo.run_filter(self.test_filter, pr_attributes))

    def testLabelFilter(self):
        label_filter = {"label": ["test_label"], "user": [None], "pr": ["0"]}
        self.assertTrue(self.gh_repo.run_filter(self.test_filter, label_filter))

    def testLabelsFilter(self):
        labels_filter = {
            "label": ["test_label","test_label_2"],
            "user": [None],
            "pr": ["0"]
            }
        self.assertTrue(self.gh_repo.run_filter(self.test_filter, labels_filter))

    def testUserFilter(self):
        user_filter = {"label": [], "user": ["test_user"], "pr": ["0"]}
        self.assertTrue(self.gh_repo.run_filter(self.test_filter, user_filter))

    def testUsersFilter(self):
        users_filter = {"label": [], "user": ["test_user","test_user_2"], "pr": ["0"]}
        self.assertTrue(self.gh_repo.run_filter(self.test_filter, users_filter))

    def testPRFilter(self):
        pr_filter = {"label": [], "user": [None], "pr": ["1"]}
        self.assertTrue(self.gh_repo.run_filter(self.test_filter, pr_filter))

    def testPRsFilter(self):
        prs_filter = {"label": [], "user": [None], "pr": ["1","2"]}
        self.assertTrue(self.gh_repo.run_filter(self.test_filter, prs_filter))

    # Default arguments
    def testDefaults(self):
        ns = self.scc_parser.parse_args(["merge", "master"])
        self.assertEqual(ns.exclude, self.default_exclude)
        self.assertEqual(ns.include, self.default_include)

    def testInclude(self):
        ns = self.scc_parser.parse_args(["merge", "master", "-Itest"])
        self.assertEqual(ns.exclude, self.default_exclude)
        self.assertEqual(ns.include, ['test'])

    def testMultipleInclude(self):
        ns = self.scc_parser.parse_args(["merge" ,"master", "-Itest", "-Itest2"])
        self.assertEqual(ns.exclude, self.default_exclude)
        self.assertEqual(ns.include, ['test' ,'test2'])

    def testExclude(self):
        ns = self.scc_parser.parse_args(["merge", "master", "-Etest"])
        self.assertEqual(ns.exclude, ['test'])
        self.assertEqual(ns.include, self.default_include)

    def testMultipleExclude(self):
        ns = self.scc_parser.parse_args(["merge" ,"master", "-Etest", "-Etest2"])
        self.assertEqual(ns.include, self.default_include)
        self.assertEqual(ns.exclude, ['test' ,'test2'])

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
