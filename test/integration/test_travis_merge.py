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

from yaclifw.framework import main, Stop
from scc.git import TravisMerge
from Sandbox import SandboxTest


class TestTravisMerge(SandboxTest):

    def setup_method(self, method):

        super(TestTravisMerge, self).setup_method(method)
        self.init_submodules()
        self.base = "dev_4_4"
        self.merge_branch = "merge/dev_4_4/test"
        self.branch = []
        self.pr = []
        for i in range(2):
            self.branch.append(self.fake_branch(head=self.base))
            self.pr.append(self.open_pr(self.branch[i], self.base))
            self.sandbox.checkout_branch(self.base)

    def isMerged(self, ref='HEAD'):
        revlist = self.sandbox.communicate("git", "rev-list", ref)
        return [pr.head.sha in revlist.splitlines() for pr in self.pr]

    def teardown_method(self, method):
        # Clean the initial branch. This will close the inital PRs
        for branch in self.branch:
            self.sandbox.push_branch(":%s" % branch, remote=self.user)
        super(TestTravisMerge, self).teardown_method(method)

    def travis_merge(self, *args):
        self.sandbox.checkout_branch(self.branch[0])
        args = ["travis-merge", "--no-ask"] + list(args)
        main("scc", args=args, items=[(TravisMerge.NAME, TravisMerge)])

    def testMissingEnvironmentVariable(self):

        # scc merge without TRAVIS_PULL_REQUEST should fail
        with pytest.raises(Stop):
            self.travis_merge()

    def testTravisMerge(self, monkeypatch):

        monkeypatch.setenv('TRAVIS_PULL_REQUEST', self.pr[0].number)
        self.travis_merge()
        assert self.isMerged() == [True, False]

    @pytest.mark.parametrize('location', ['description', 'comment'])
    @pytest.mark.parametrize('form', ['url', 'reference'])
    def testDependency(self, location, form, monkeypatch):

        monkeypatch.setenv('TRAVIS_PULL_REQUEST', self.pr[0].number)
        if form == 'url':
            dep_line = '--depends-on %s' % self.pr[1].html_url
        else:
            dep_line = '--depends-on #%s' % self.pr[1].number
        if location == 'description':
            self.pr[0].edit(body=self.pr[0].body+'\n\n----\n%s' % dep_line)
        elif location == 'comment':
            self.pr[0].create_issue_comment(dep_line)
        self.travis_merge()
        assert self.isMerged() == [True, True]
