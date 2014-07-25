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

from yaclifw.framework import parsers
from scc.git import FilteredPullRequestsCommand
from scc.git import Merge
from scc.git import SetCommitStatus
from scc.git import TravisMerge
from scc.git import get_default_filters
from Mock import MoxTestBase, MockTest
defaults = (None, 'none', 'org', 'all')


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


class TestFilteredPullRequestsCommand(MoxTestBase):

    def setup_method(self, method):
        super(TestFilteredPullRequestsCommand, self).setup_method(method)
        self.scc_parser, self.sub_parser = parsers()
        self.command = FilteredPullRequestsCommand(self.sub_parser)
        self.filters = {'include': {}, 'exclude': {}}
        self.command.filters = {'include': {}, 'exclude': {}}

    @pytest.mark.parametrize('ftype', ['include', 'exclude'])
    @pytest.mark.parametrize('value', ['', '#12#12', 'pr:12'])
    def test_parse_hash_invalid(self, ftype, value):
        rsp = self.command._parse_hash(ftype, value)
        assert not rsp
        assert self.command.filters == self.filters

    @pytest.mark.parametrize('ftype', ['include', 'exclude'])
    @pytest.mark.parametrize(('prefix', 'key'), [
        ('', 'pr'), ('user/repo', 'user/repo'),
        ('user-1/repo-1', 'user-1/repo-1')])
    def test_parse_hash_pr(self, ftype, prefix, key):
        rsp = self.command._parse_hash(ftype, '%s#1' % prefix)
        self.filters[ftype] = {key: ['1']}
        assert rsp
        assert self.command.filters == self.filters

    @pytest.mark.parametrize('ftype', ['include', 'exclude'])
    @pytest.mark.parametrize(
        'invalid_key_value',
        ['keyvalue', '#1', ':value', 'key:', 'user#repo:value'])
    def test_parse_key_value_invalid(self, ftype, invalid_key_value):
        rsp = self.command._parse_key_value(ftype, '%s' % invalid_key_value)
        assert not rsp
        assert self.command.filters == self.filters

    @pytest.mark.parametrize('ftype', ['include', 'exclude'])
    @pytest.mark.parametrize(
        'key', ['user', 'label', 'pr', 'user/repo',
                'user-1/repo-2'])
    @pytest.mark.parametrize('value', ['1', 'value', 'value-1', 'value/1'])
    def test_parse_key_value(self, ftype, key, value):
        self.command._parse_key_value(ftype, '%s:%s' % (key, value))
        self.filters[ftype] = {key: [value]}
        assert self.command.filters == self.filters

    @pytest.mark.parametrize('ftype', ['include', 'exclude'])
    @pytest.mark.parametrize('key', ['user/repo', 'user-1/repo-2'])
    @pytest.mark.parametrize('value', ['1'])
    def test_parse_url(self, ftype, key, value):
        self.command._parse_url(
            ftype, 'https://github.com/%s/pull/%s' % (key, value))
        self.filters[ftype] = {key: [value]}
        assert self.command.filters == self.filters


class FilteredPullRequestsCommandTest(MoxTestBase):

    def setup_method(self, method):
        super(FilteredPullRequestsCommandTest, self).setup_method(method)
        self.scc_parser, self.sub_parser = parsers()
        self.base = 'master'
        self.filters = {
            'base': self.base,
            'status': 'none',
            }
        self.args = []

    def parse_filters(self):
        ns = self.scc_parser.parse_args(self.get_main_cmd() + self.args)
        self.command._parse_filters(ns)
        return self.command.filters

    def set_defaults(self, default):
        if default:
            self.args += ['-D%s' % default]
            self.filters.update(get_default_filters(default))
        else:
            self.filters.update(get_default_filters("org"))

    # Default arguments
    @pytest.mark.parametrize('default', defaults)
    def testBase(self, default):
        self.set_defaults(default)
        self.base = 'develop'
        self.filters["base"] = "develop"
        assert self.parse_filters() == self.filters

    @pytest.mark.parametrize('default', defaults)
    @pytest.mark.parametrize('ftype', ['include', 'exclude'])
    @pytest.mark.parametrize('user_prefix', [None, 'user:'])
    @pytest.mark.parametrize('pr_prefix', [None, '#', 'pr:', 'org/repo#'])
    @pytest.mark.parametrize('label_filter', [None, '', 'label:'])
    def testUserFilter(self, default, ftype, user_prefix, pr_prefix,
                       label_filter):
        self.set_defaults(default)
        if user_prefix:
            self.args += ['--%s' % ftype, '%suser' % user_prefix]
            self.filters[ftype].setdefault("user", []).append('user')
        if pr_prefix:
            self.args += ['--%s' % ftype, '%s1' % pr_prefix]
            if '/' in pr_prefix:
                key = "org/repo"
            else:
                key = "pr"
            self.filters[ftype].setdefault(key, []).append('1')
        if label_filter:
            self.args += ['--%s' % ftype, '%slabel' % label_filter]
            self.filters[ftype].setdefault("label", []).append('label')
        assert self.parse_filters() == self.filters

    @pytest.mark.parametrize('default', defaults)
    @pytest.mark.parametrize('status', ['none', 'no-error', 'success-only'])
    def testCheckCommitStatus(self, default, status):
        self.set_defaults(default)
        self.args += ["-S", "%s" % status]
        self.filters["status"] = status
        self.parse_filters()
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
    @pytest.mark.parametrize('default', defaults)
    @pytest.mark.parametrize(
        'status', ['success', 'failure', 'error', 'pending'])
    def testStatus(self, default, status):
        self.set_defaults(default)
        self.status = status
        self.parse_filters()
        assert self.command.filters == self.filters


class TestTravisMerge(MoxTestBase):

    def setup_method(self, method):
        super(TestTravisMerge, self).setup_method(method)
        self.scc_parser, self.sub_parser = parsers()
        self.command = TravisMerge(self.sub_parser)
        self.base = 'master'
        self.filters = get_default_filters("none")
        self.filters.update({'base': self.base})

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
        self.filters["include"]["ome/scripts"] = ['21']
        assert self.command.filters == self.filters

    def testIncludeMultiplePRs(self):
        # --depends-on #21 changes filters
        self.parse_dependencies(['#21', '#22', 'ome/scripts#21'])
        self.filters["include"]["pr"] = ['21', '22']
        self.filters["include"]['ome/scripts'] = ['21']
        assert self.command.filters == self.filters
