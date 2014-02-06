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

import pytest

from scc.framework import parsers
from scc.git import Merge, SetCommitStatus, TravisMerge
from Mock import MoxTestBase, MockTest


class TestFilter(MockTest):

    def setup_method(self, method):
        super(TestFilter, self).setup_method(method)
        self.input = {
            "label": ["test_label"],
            "user": ["test_user"],
            "pr": ["1"],
            }
        self.filters = {}

    def run_filter(self):
        status, reason = self.gh_repo.run_filter(
            self.filters, self.input)
        return status, reason

    def testIntersect(self):
        assert self.gh_repo.intersect([1, 2, 3], [3, 4, 5]) == [3]

    def testSelfFilter(self):
        self.filters = self.input
        status, reason = self.run_filter()
        assert status

    @pytest.mark.parametrize(
        'labels', [[], ["test_label"], ["test_label", "test_label_2"]])
    @pytest.mark.parametrize(
        'users', [[], ["test_user"], ["test_user", "test_user_2"]])
    @pytest.mark.parametrize('prs', [[], ["1"], ["1", "2"]])
    def testStatus(self, labels, users, prs):
        self.filters = {"label": labels, "user": users, "pr": prs}
        status, reason = self.run_filter()
        assert status is ("test_label" in labels) or ("test_user" in users) \
            or ("1" in prs)


class FilteredPullRequestsCommandTest(MoxTestBase):

    def setup_method(self, method):
        super(FilteredPullRequestsCommandTest, self).setup_method(method)
        self.scc_parser, self.sub_parser = parsers()
        self.base = 'master'
        self.filters = {
            'base': self.base,
            'default': 'org',
            'status': 'none',
            'include': {'label': ['include']},
            'exclude': {'label': ['exclude', 'breaking']}
            }

    def parse_filters(self, args):
        ns = self.scc_parser.parse_args(self.get_main_cmd() + args)
        self.command._parse_filters(ns)

    # Default arguments
    def testDefaults(self):
        self.parse_filters([])
        assert self.command.filters == self.filters

    def testBase(self):
        self.base = 'develop'
        self.filters["base"] = "develop"  # Regenerate default
        self.parse_filters([])
        assert self.command.filters == self.filters

    # Default PR sets
    @pytest.mark.parametrize('default', ['none', 'org', 'all'])
    def testDefault(self, default):
        self.parse_filters(['-D%s' % default])
        self.filters["default"] = default
        assert self.command.filters == self.filters

    # PR inclusion
    @pytest.mark.parametrize('prefix', ['', 'label:'])
    @pytest.mark.parametrize('filter_type', ['include', 'exclude'])
    def testLabelFilter(self, filter_type, prefix):
        self.parse_filters(['--%s' % filter_type, '%stest' % prefix])
        self.filters[filter_type] = {"label": ['test']}
        assert self.command.filters == self.filters

    @pytest.mark.parametrize('prefix', ['#', 'pr:'])
    @pytest.mark.parametrize('filter_type', ['include', 'exclude'])
    def testPRFilter(self, filter_type, prefix):
        self.parse_filters(['--%s' % filter_type, '%s1' % prefix])
        self.filters[filter_type] = {"pr": ['1']}
        assert self.command.filters == self.filters

    @pytest.mark.parametrize('filter_type', ['include', 'exclude'])
    def testSubmodulePRFilter(self, filter_type):
        self.parse_filters(['--%s' % filter_type, 'org/repo#1'])
        self.filters[filter_type] = {"pr": ['org/repo1']}
        assert self.command.filters == self.filters

    @pytest.mark.parametrize('filter_type', ['include', 'exclude'])
    def testUserFilter(self, filter_type):
        self.parse_filters(['--%s' % filter_type, 'user:user'])
        self.filters[filter_type] = {"user": ["user"]}
        assert self.command.filters == self.filters

    @pytest.mark.parametrize('filter_type', ['include', 'exclude'])
    def testMixedFilters(self, filter_type):
        self.parse_filters(
            ['--%s' % filter_type, 'test',
             '--%s' % filter_type, 'label:test2',
             '--%s' % filter_type, '#1',
             '--%s' % filter_type, 'pr:2',
             '--%s' % filter_type, 'org/repo#1',
             '--%s' % filter_type, 'user:user'])
        self.filters[filter_type] = {
            "label": ['test', 'test2'],
            "pr": ["1", '2', 'org/repo1'],
            "user": ["user"]}
        assert self.command.filters == self.filters

    @pytest.mark.parametrize('status', ['none', 'no-error', 'success-only'])
    def testCheckCommitStatus(self, status):
        self.parse_filters(["-S", "%s" % status])
        self.filters["status"] = status
        assert self.command.filters == self.filters


class TestMerge(FilteredPullRequestsCommandTest):

    def setup_method(self, method):
        super(TestMerge, self).setup_method(method)
        self.command = Merge(self.sub_parser)

    def get_main_cmd(self):
        return [self.command.NAME, self.base]


class TestSetCommitStatus(FilteredPullRequestsCommandTest):

    def setup_method(self, method):
        super(TestSetCommitStatus, self).setup_method(method)
        self.command = SetCommitStatus(self.sub_parser)
        self.status = 'success'
        self.message = 'test'

    def get_main_cmd(self):
        return [self.command.NAME, self.base, '-s', self.status, '-m',
                self.message]

    # Status tests
    @pytest.mark.parametrize(
        'status', ['success', 'failure', 'error', 'pending'])
    def testStatus(self, status):
        self.status = status
        self.parse_filters([])
        assert self.command.filters == self.filters


class TestTravisMerge(MoxTestBase):

    def setup_method(self, method):
        super(TestTravisMerge, self).setup_method(method)
        self.scc_parser, self.sub_parser = parsers()
        self.command = TravisMerge(self.sub_parser)
        self.base = 'master'
        self.filters = {
            'base': self.base,
            'default': 'none',
            'include': {},
            'exclude': {}
            }

    def parse_dependencies(self, comments):
        self.command._parse_dependencies(self.base, comments)

    # Default arguments
    def testDefaults(self):
        self.parse_dependencies([])
        assert self.command.filters == self.filters

    def testBase(self):
        self.base = 'develop'
        self.filters['base'] = 'develop'  # Regenerate default
        self.parse_dependencies([])
        assert self.command.filters == self.filters

    def testIncludePRNoHash(self):
        # --depends-on 21 does not change filters
        self.parse_dependencies(['21'])
        assert self.command.filters == self.filters

    def testIncludeSinglePR(self):
        # --depends-on #21 changes filters
        self.parse_dependencies(['#21'])
        self.filters["include"]["pr"] = ['21']
        assert self.command.filters == self.filters

    def testIncludeSubmodulePR(self):
        # --depends-on ome/scripts#21 changes filters
        self.parse_dependencies(['ome/scripts#21'])
        self.filters["include"]["pr"] = ['ome/scripts21']
        assert self.command.filters == self.filters

    def testIncludeMultiplePRs(self):
        # --depends-on #21 changes filters
        self.parse_dependencies(['#21', '#22', 'ome/scripts#21'])
        self.filters["include"]["pr"] = ['21', '22', 'ome/scripts21']
        assert self.command.filters == self.filters
