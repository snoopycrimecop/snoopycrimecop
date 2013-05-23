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

class UnitTestFilter(MockTest):

    def setUp(self):
        MockTest.setUp(self)
        self.test_filter = {
            "label": ["test_label"],
            "user": ["test_user"],
            "pr": ["1"],
            }

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

class UnitTestMerge(MockTest):

    def setUp(self):
        MockTest.setUp(self)

        self.scc_parser, self.sub_parser = parsers()
        self.merge = Merge(self.sub_parser)
        self.base = 'master'
        self.default_filters = {'base': 'master', 'default': 'org',
            'include':{}, 'exclude':{}}
        self.default_filters["include"]["label"] = ["include"]
        self.default_filters["include"]["pr"] = None
        self.default_filters["include"]["user"] = None
        self.default_filters["exclude"]["label"] = ["exclude"]
        self.default_filters["exclude"]["pr"] = None
        self.default_filters["exclude"]["user"] = None

    def parse_filters(self, args):
        main_cmd =["merge", self.base]
        ns = self.scc_parser.parse_args(main_cmd + args)
        self.merge._parse_filters(ns)

    # Default arguments
    def testDefaults(self):
        self.parse_filters([])
        self.assertEqual(self.merge.filters, self.default_filters)

    def testBase(self):
        self.base = 'develop'
        self.parse_filters([])
        filters = self.default_filters
        filters["base"] = self.base
        self.assertEqual(self.merge.filters, filters)

    # Default PR sets
    def testNone(self):
        self.parse_filters(['-Dnone'])
        filters = self.default_filters
        filters["default"] = 'none'
        self.assertEqual(self.merge.filters, filters)

    def testAll(self):
        self.parse_filters(['-Dall'])
        filters = self.default_filters
        filters["default"] = 'all'
        self.assertEqual(self.merge.filters, filters)

    # PR inclusion
    def testIncludeLabelNoKey(self):
        self.parse_filters(["-Itest"])
        filters = self.default_filters
        filters["include"]["label"] = ["test"]
        self.assertEqual(self.merge.filters, filters)

    def testIncludeLabelKey(self):
        self.parse_filters(["-Ilabel:test"])
        filters = self.default_filters
        filters["include"]["label"] = ["test"]
        self.assertEqual(self.merge.filters, filters)

    def testIncludeMixedLabels(self):
        self.parse_filters(["-Itest", "-Ilabel:test2"])
        filters = self.default_filters
        filters["include"]["label"] = ['test' ,'test2']
        self.assertEqual(self.merge.filters, filters)

    def testIncludePRHash(self):
        self.parse_filters(["-I#65"])
        filters = self.default_filters
        filters["include"]["label"] = None
        filters["include"]["pr"] = ["65"]
        self.assertEqual(self.merge.filters, filters)

    def testIncludeMixedPRs(self):
        self.parse_filters(["-I#65","-Ipr:66"])
        filters = self.default_filters
        filters["include"]["label"] = None
        filters["include"]["pr"] = ["65", '66']
        self.assertEqual(self.merge.filters, filters)

    def testIncludePR(self):
        self.parse_filters(["-Ipr:65"])
        filters = self.default_filters
        filters["include"]["label"] = None
        filters["include"]["pr"] = ["65"]
        self.assertEqual(self.merge.filters, filters)

    def testIncludeUser(self):
        self.parse_filters(["-Iuser:snoopycrimecop"])
        filters = self.default_filters
        filters["include"]["label"] = None
        filters["include"]["user"] = ["snoopycrimecop"]
        self.assertEqual(self.merge.filters, filters)

    # Label exclusion
    def testExcludeLabelNoKey(self):
        self.parse_filters(["-Etest"])
        filters = self.default_filters
        filters["exclude"]["label"] = ["test"]
        self.assertEqual(self.merge.filters, filters)

    def testExcludeLabelKey(self):
        self.parse_filters(["-Elabel:test"])
        filters = self.default_filters
        filters["exclude"]["label"] = ["test"]
        self.assertEqual(self.merge.filters, filters)

    def testExcludeMultipleLabels(self):
        self.parse_filters(["-Etest", "-Elabel:test2"])
        filters = self.default_filters
        filters["exclude"]["label"] = ['test' ,'test2']
        self.assertEqual(self.merge.filters, filters)

    def testExcludePR(self):
        self.parse_filters(["-Epr:65"])
        filters = self.default_filters
        filters["exclude"]["label"] = None
        filters["exclude"]["pr"] = ["65"]
        self.assertEqual(self.merge.filters, filters)

    def testExcludePRHash(self):
        self.parse_filters(["-E#65"])
        filters = self.default_filters
        filters["exclude"]["label"] = None
        filters["exclude"]["pr"] = ["65"]
        self.assertEqual(self.merge.filters, filters)

    def testExcludeMixedPRs(self):
        self.parse_filters(["-E#65","-Epr:66"])
        filters = self.default_filters
        filters["exclude"]["label"] = None
        filters["exclude"]["pr"] = ["65", '66']
        self.assertEqual(self.merge.filters, filters)

    def testExcludeUser(self):
        self.parse_filters(["-Euser:snoopycrimecop"])
        filters = self.default_filters
        filters["exclude"]["label"] = None
        filters["exclude"]["user"] = ["snoopycrimecop"]
        self.assertEqual(self.merge.filters, filters)

class UnitTestTravisMerge(MockTest):

    def setUp(self):
        MockTest.setUp(self)

        self.scc_parser, self.sub_parser = parsers()
        self.merge = TravisMerge(self.sub_parser)
        self.base = 'master'
        self.default_filters = {'base': 'master', 'default': 'none',
            'include':{}, 'exclude':{}}
        self.default_filters["include"]["label"] = None
        self.default_filters["include"]["pr"] = None
        self.default_filters["include"]["user"] = None
        self.default_filters["exclude"]["label"] = None
        self.default_filters["exclude"]["pr"] = None
        self.default_filters["exclude"]["user"] = None

    def parse_dependencies(self, comments):
        self.merge._parse_dependencies('master', comments)

    # Default arguments
    def testDefaults(self):
        self.parse_dependencies([])
        self.assertEqual(self.merge.filters, self.default_filters)

    def testIncludePRNoHash(self):
        # --depends-on 21 does not change filters
        self.parse_dependencies(['21'])
        self.assertEqual(self.merge.filters, self.default_filters)

    def testIncludeSinglePR(self):
        # --depends-on #21 changes filters
        self.parse_dependencies(['#21'])
        filters = self.default_filters
        filters["include"]["pr"] = ['21']
        self.assertEqual(self.merge.filters, self.default_filters)

    def testIncludeMultiplePRs(self):
        # --depends-on #21 changes filters
        self.parse_dependencies(['#21', '#22'])
        filters = self.default_filters
        filters["include"]["pr"] = ['21','22']
        self.assertEqual(self.merge.filters, self.default_filters)

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
