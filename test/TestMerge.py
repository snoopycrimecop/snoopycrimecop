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

class UnitTestFilteredPullRequestsCommand(object):

    def setUp(self):
        self.scc_parser, self.sub_parser = parsers()
        self.base = 'master'
        self.filters = self.get_default_filters()

    def get_default_filters(self):
        include_default = {'pr': None, 'user': None, 'label': ['include']}
        exclude_default = {'pr': None, 'user': None, 'label': ['exclude']}
        return {'base': self.base, 'default': 'org',
            'include': include_default, 'exclude': exclude_default}

    def parse_filters(self, args):
        ns = self.scc_parser.parse_args(self.get_main_cmd() + args)
        self.command._parse_filters(ns)

    # Default arguments
    def testDefaults(self):
        self.parse_filters([])
        self.assertEqual(self.command.filters, self.filters)

    def testBase(self):
        self.base = 'develop'
        self.filters = self.get_default_filters() # Regenerate default filters
        self.parse_filters([])
        self.assertEqual(self.command.filters, self.filters)

    # Default PR sets
    def testNone(self):
        self.parse_filters(['-Dnone'])
        self.filters["default"] = 'none'
        self.assertEqual(self.command.filters, self.filters)

    def testOrg(self):
        self.parse_filters(['-Dorg'])
        self.filters["default"] = 'org'
        self.assertEqual(self.command.filters, self.filters)

    def testAll(self):
        self.parse_filters(['-Dall'])
        self.filters["default"] = 'all'
        self.assertEqual(self.command.filters, self.filters)

    # PR inclusion
    def testIncludeLabelNoKey(self):
        self.parse_filters(["-Itest"])
        self.filters["include"]["label"] = ["test"]
        self.assertEqual(self.command.filters, self.filters)

    def testIncludeLabelKey(self):
        self.parse_filters(["-Ilabel:test"])
        self.filters["include"]["label"] = ["test"]
        self.assertEqual(self.command.filters, self.filters)

    def testIncludeMixedLabels(self):
        self.parse_filters(["-Itest", "-Ilabel:test2"])
        self.filters["include"]["label"] = ['test' ,'test2']
        self.assertEqual(self.command.filters, self.filters)

    def testIncludePRHash(self):
        self.parse_filters(["-I#65"])
        self.filters["include"]["label"] = None
        self.filters["include"]["pr"] = ["65"]
        self.assertEqual(self.command.filters, self.filters)

    def testIncludePRSubmodule(self):
        self.parse_filters(["-Iome/scripts#65"])
        self.filters["include"]["label"] = None
        self.filters["include"]["pr"] = ["ome/scripts65"]
        self.assertEqual(self.command.filters, self.filters)

    def testIncludeMixedPRs(self):
        self.parse_filters(["-I#65","-Ipr:66","-Iome/scripts#65"])
        self.filters["include"]["label"] = None
        self.filters["include"]["pr"] = ["65", '66', 'ome/scripts65']
        self.assertEqual(self.command.filters, self.filters)

    def testIncludePR(self):
        self.parse_filters(["-Ipr:65"])
        self.filters["include"]["label"] = None
        self.filters["include"]["pr"] = ["65"]
        self.assertEqual(self.command.filters, self.filters)

    def testIncludeUser(self):
        self.parse_filters(["-Iuser:snoopycrimecop"])
        self.filters["include"]["label"] = None
        self.filters["include"]["user"] = ["snoopycrimecop"]
        self.assertEqual(self.command.filters, self.filters)

    # Label exclusion
    def testExcludeLabelNoKey(self):
        self.parse_filters(["-Etest"])
        self.filters["exclude"]["label"] = ["test"]
        self.assertEqual(self.command.filters, self.filters)

    def testExcludeLabelKey(self):
        self.parse_filters(["-Elabel:test"])
        self.filters["exclude"]["label"] = ["test"]
        self.assertEqual(self.command.filters, self.filters)

    def testExcludeMultipleLabels(self):
        self.parse_filters(["-Etest", "-Elabel:test2"])
        self.filters["exclude"]["label"] = ['test' ,'test2']
        self.assertEqual(self.command.filters, self.filters)

    def testExcludePR(self):
        self.parse_filters(["-Epr:65"])
        self.filters["exclude"]["label"] = None
        self.filters["exclude"]["pr"] = ["65"]
        self.assertEqual(self.command.filters, self.filters)

    def testExcludePRHash(self):
        self.parse_filters(["-E#65"])
        self.filters["exclude"]["label"] = None
        self.filters["exclude"]["pr"] = ["65"]
        self.assertEqual(self.command.filters, self.filters)

    def testExcludePRSubmodule(self):
        self.parse_filters(["-Eome/scripts#65"])
        self.filters["exclude"]["label"] = None
        self.filters["exclude"]["pr"] = ["ome/scripts65"]
        self.assertEqual(self.command.filters, self.filters)

    def testExcludeMixedPRs(self):
        self.parse_filters(["-E#65","-Epr:66","-Eome/scripts#65"])
        self.filters["exclude"]["label"] = None
        self.filters["exclude"]["pr"] = ["65", '66', 'ome/scripts65']
        self.assertEqual(self.command.filters, self.filters)

    def testExcludeUser(self):
        self.parse_filters(["-Euser:snoopycrimecop"])
        self.filters["exclude"]["label"] = None
        self.filters["exclude"]["user"] = ["snoopycrimecop"]
        self.assertEqual(self.command.filters, self.filters)

class UnitTestMerge(MockTest, UnitTestFilteredPullRequestsCommand):

    def setUp(self):
        MockTest.setUp(self)
        UnitTestFilteredPullRequestsCommand.setUp(self)
        self.command = Merge(self.sub_parser)

    def get_main_cmd(self):
        return [self.command.NAME, self.base]

class UnitTestSetCommitStatus(MockTest, UnitTestFilteredPullRequestsCommand):

    def setUp(self):
        MockTest.setUp(self)
        UnitTestFilteredPullRequestsCommand.setUp(self)
        self.command = SetCommitStatus(self.sub_parser)
        self.status = 'success'
        self.message = 'test'

    def get_main_cmd(self):
        return [self.command.NAME, self.base, '-s', self.status, '-m',
            self.message]

    # Status tests
    def testSuccess(self):
        self.status = 'success'
        self.parse_filters([])
        self.assertEqual(self.command.filters, self.filters)

    def testFailure(self):
        self.status = 'failure'
        self.parse_filters([])
        self.assertEqual(self.command.filters, self.filters)

    def testError(self):
        self.status = 'error'
        self.parse_filters([])
        self.assertEqual(self.command.filters, self.filters)

    def testPending(self):
        self.status = 'pending'
        self.parse_filters([])
        self.assertEqual(self.command.filters, self.filters)

class UnitTestTravisMerge(MockTest):

    def setUp(self):
        MockTest.setUp(self)

        self.scc_parser, self.sub_parser = parsers()
        self.command = TravisMerge(self.sub_parser)
        self.base = 'master'
        self.filters = self.get_default_filters()

    def get_default_filters(self):
        include_default = {'pr': None, 'user': None, 'label': None}
        exclude_default = {'pr': None, 'user': None, 'label': None}
        return {'base': self.base, 'default': 'none',
            'include': include_default, 'exclude': exclude_default}

    def parse_dependencies(self, comments):
        self.command._parse_dependencies(self.base, comments)

    # Default arguments
    def testDefaults(self):
        self.parse_dependencies([])
        self.assertEqual(self.command.filters, self.filters)

    def testBase(self):
        self.base = 'develop'
        self.filters = self.get_default_filters() # Regenerate default filters
        self.parse_dependencies([])
        self.assertEqual(self.command.filters, self.filters)

    def testIncludePRNoHash(self):
        # --depends-on 21 does not change filters
        self.parse_dependencies(['21'])
        self.assertEqual(self.command.filters, self.filters)

    def testIncludeSinglePR(self):
        # --depends-on #21 changes filters
        self.parse_dependencies(['#21'])
        self.filters["include"]["pr"] = ['21']
        self.assertEqual(self.command.filters, self.filters)

    def testIncludeSubmodulePR(self):
        # --depends-on ome/scripts#21 changes filters
        self.parse_dependencies(['ome/scripts#21'])
        self.filters["include"]["pr"] = ['ome/scripts21']
        self.assertEqual(self.command.filters, self.filters)


    def testIncludeMultiplePRs(self):
        # --depends-on #21 changes filters
        self.parse_dependencies(['#21', '#22', 'ome/scripts#21'])
        self.filters["include"]["pr"] = ['21','22', 'ome/scripts21']
        self.assertEqual(self.command.filters, self.filters)

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

        main(["merge", "--no-ask", "dev_4_4"])

    def testPush(self):

        main(["merge", "--no-ask", "dev_4_4" ,"--push", "test"])
        # This will clean the pushed branch
        remote = "git@github.com:%s/" % (self.user) + "%s.git"
        self.sandbox.rpush(":test", remote=remote)
            

if __name__ == '__main__':
    import logging
    logging.basicConfig()
    unittest.main()
