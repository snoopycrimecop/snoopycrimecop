#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2013-2014 University of Dundee & Open Microscopy Environment
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

from github.AuthenticatedUser import AuthenticatedUser
from github.NamedUser import NamedUser
from github.Organization import Organization
from github.Repository import Repository
from github.Issue import Issue
from github.Milestone import Milestone
from github.PullRequest import PullRequest
from github.PullRequestPart import PullRequestPart
from github.PaginatedList import PaginatedList

from scc.git import GHManager
from scc.git import GitHubRepository
import pytest
from Mock import MoxTestBase


class TestGithubRepository(MoxTestBase):

    def setup_method(self, method):
        super(TestGithubRepository, self).setup_method(method)
        # Mocks
        self.gh = self.mox.CreateMock(GHManager)
        self.user = self.mox.CreateMock(AuthenticatedUser)
        self.user.login = "mock_user"
        self.org = self.mox.CreateMock(Organization)
        self.org.login = "mock_org"
        self.repo = self.mox.CreateMock(Repository)
        self.repo.name = "mock_repo"
        self.repo.owner = self.user
        self.repo.organization = None

        self.pulls = []
        self.milestones = []
        self.gh.get_repo(
            "%s/%s" % (self.user.login, self.repo.name)).AndReturn(self.repo)

    def create_pulls(self, baserefs=["master"]):

        for baseref in baserefs:
            base = self.mox.CreateMock(PullRequestPart)
            base.ref = baseref
            pullrequest = self.mox.CreateMock(PullRequest)
            pullrequest.base = base
            self.pulls.append(pullrequest)

    def create_milestones(self, titles):

        for title in titles:
            milestone = self.mox.CreateMock(Milestone)
            milestone.title = title
            self.milestones.append(milestone)

    def iter_pulls(self):
        for x in self.pulls:
            yield x

    def setup_org(self):
        self.repo.organization = self.org
        self.gh.get_organization(self.org.login).AndReturn(self.org)

    def setup_repo(self):
        self.mox.ReplayAll()
        self.gh_repo = GitHubRepository(
            self.gh, self.user.login, self.repo.name)

    @pytest.mark.parametrize('with_org', [True, False])
    def test_init(self, with_org):
        if with_org:
            self.setup_org()
        self.setup_repo()
        assert self.gh_repo.gh == self.gh
        assert self.gh_repo.repo == self.repo
        assert self.gh_repo.user_name == self.user.login
        assert self.gh_repo.repo_name == self.repo.name
        if with_org:
            assert self.gh_repo.org is self.org
        else:
            assert self.gh_repo.org is None

    def test_repr(self):
        self.setup_repo()
        repo_str = "Repository: %s/%s" % (self.user.login, self.repo.name)
        assert str(self.gh_repo) == repo_str

    def test_get_issue(self):
        issue = self.mox.CreateMock(Issue)
        self.repo.get_issue(1).AndReturn(issue)
        self.setup_repo()
        assert self.gh_repo.get_issue(1) == issue

    def test_get_pull(self):
        pullrequest = self.mox.CreateMock(PullRequest)
        self.repo.get_pull(1).AndReturn(pullrequest)
        self.setup_repo()
        assert self.gh_repo.get_pull(1) == pullrequest

    def test_get_pulls(self):
        pulls = self.mox.CreateMock(PaginatedList)
        self.repo.get_pulls().AndReturn(pulls)
        self.setup_repo()
        assert self.gh_repo.get_pulls() == pulls

    def test_get_pulls_by_base(self):
        self.create_pulls(["master", "master", "develop"])
        pulls_list = self.mox.CreateMock(PaginatedList)
        pulls_list.__iter__().AndReturn(self.iter_pulls())
        self.repo.get_pulls().AndReturn(pulls_list)
        self.setup_repo()
        assert self.gh_repo.get_pulls_by_base("master") == \
            self.pulls[:-1]

    def testGetMilestoneOpen(self):
        self.create_milestones(["open-1", "open-2"])
        self.repo.get_milestones(state="open").AndReturn(self.milestones)
        self.setup_repo()
        assert self.gh_repo.get_milestone("open-2") == self.milestones[1]

    def testGetMilestoneClosed(self):
        self.create_milestones(["closed-1", "closed-2"])
        self.repo.get_milestones(state="open").AndReturn([])
        self.repo.get_milestones(state="closed").AndReturn(self.milestones)
        self.setup_repo()
        assert self.gh_repo.get_milestone("closed-2") == self.milestones[1]

    def testGetMilestoneFails(self):
        self.repo.get_milestones(state="open").AndReturn([])
        self.repo.get_milestones(state="closed").AndReturn([])
        self.setup_repo()
        assert self.gh_repo.get_milestone("closed-2") is None

    def test_get_owner(self):
        self.setup_repo()
        assert self.gh_repo.get_owner() == self.user.login

    def test_create_open_pr(self):
        pullrequest = self.mox.CreateMock(PullRequest)
        title = "mock-title"
        description = "mock-description"
        base = "mock-base"
        head = "mock-head"
        self.repo.create_pull(
            title, description, base, head).AndReturn(pullrequest)
        self.setup_repo()
        assert self.gh_repo.create_pull(title, description, base, head) == \
            pullrequest

    @pytest.mark.parametrize(
        'whitelist', [["#all"], ["test"], ["test", "test2"]])
    @pytest.mark.parametrize('with_org', [True, False])
    def test_whitelisted(self, whitelist, with_org):
        user = self.mox.CreateMock(NamedUser)
        user.login = 'test'
        if with_org:
            self.setup_org()
        if whitelist and with_org and "#org" in whitelist:
            self.org.has_in_public_members(user).AndReturn(True)
        self.setup_repo()

        assert self.gh_repo.is_whitelisted(user, whitelist)

    @pytest.mark.parametrize(
        'whitelist', [["#all", "#org"], ["#org"], ["#org", "test2"]])
    def test_org_whitelist(self, whitelist):
        user = self.mox.CreateMock(NamedUser)
        user.login = 'test'
        self.setup_org()
        if "#org" in whitelist and "#all" not in whitelist:
            self.org.has_in_public_members(user).AndReturn(True)
        self.setup_repo()

        assert self.gh_repo.is_whitelisted(user, whitelist)

    @pytest.mark.parametrize(
        'whitelist', [None, ["test2"], ["#org"], ["#org", "test2"]])
    @pytest.mark.parametrize('with_org', [True, False])
    def test_blacklisted(self, whitelist, with_org):
        user = self.mox.CreateMock(NamedUser)
        user.login = 'test'
        if with_org:
            self.setup_org()
        if whitelist and with_org and "#org" in whitelist:
            self.org.has_in_public_members(user).AndReturn(False)
        self.setup_repo()

        assert not self.gh_repo.is_whitelisted(user, whitelist)
