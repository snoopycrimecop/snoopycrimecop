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

from github.AuthenticatedUser import AuthenticatedUser
from github.Repository import Repository
from github.GithubException import GithubException
from github.Issue import Issue
from github.PullRequest import PullRequest
from github import Github

from scc.git import GHManager, GitHubRepository

import socket
from ssl import SSLError
import pytest
from Mock import MoxTestBase


class InternalRetriesHelper(object):

    def mock_calls(self):
        pass

    def run_function(self):
        pass

    def get_output(self):
        pass

    def testNoError(self):
        self.mock_calls()
        self.mox.ReplayAll()
        assert self.run_function() == self.get_output()

    def testNoRetryError(self):
        self.generate_errors(self.no_retry_exception, 1)
        self.mox.ReplayAll()
        with pytest.raises(GithubException):
            self.run_function()

    @pytest.mark.parametrize('error_type', ['server', 'socket', 'SSL'])
    @pytest.mark.parametrize('nerrors', [1, 2, 3, 4])
    def testRetries(self, error_type, nerrors):
        if error_type == 'server':
            self.generate_errors(self.server_error, nerrors)
        elif error_type == 'socket':
            self.generate_errors(self.socket_timeout, nerrors)
        elif error_type == 'SSL':
            self.generate_errors(self.ssl_error, nerrors)
        if nerrors < 4:
            self.mock_calls()
        self.mox.ReplayAll()
        if nerrors < 4:
            assert self.run_function() == self.get_output()
        else:
            if error_type == 'server':
                with pytest.raises(GithubException):
                    self.run_function()
            elif error_type == 'socket':
                with pytest.raises(socket.timeout):
                    self.run_function()
            elif error_type == 'SSL':
                with pytest.raises(SSLError):
                    self.run_function()


class TestInternalRetries(MoxTestBase):

    def setup_method(self, method):

        class MockGHManager(GHManager):

            def create_instance(self):
                pass

        super(TestInternalRetries, self).setup_method(method)
        # Define mock objects
        self.gh = self.mox.CreateMock(Github)
        self.user = self.mox.CreateMock(AuthenticatedUser)
        self.user.login = "mock"
        self.org = self.mox.CreateMock(AuthenticatedUser)
        self.repo = self.mox.CreateMock(Repository)
        self.repo.organization = None
        self.issue = self.mox.CreateMock(Issue)
        self.pull = self.mox.CreateMock(PullRequest)

        # Define mock manager
        self.gh_manager = MockGHManager()
        self.gh_manager.github = self.gh
        self.gh_manager.login_or_token = "mock"

        # Define errors to test
        self.server_error = GithubException(502, 'Server Error')
        self.no_retry_exception = GithubException(-1, 'No retry')
        self.socket_timeout = socket.timeout()
        self.ssl_error = SSLError()


class TestGHManagerGetUser(TestInternalRetries, InternalRetriesHelper):

    def generate_errors(self, error, nerrors):
        for i in range(nerrors):
            self.gh.get_user("mock").AndRaise(error)

    def mock_calls(self):
        self.gh.get_user("mock").AndReturn(self.user)

    def run_function(self):
        return self.gh_manager.get_user("mock")

    def get_output(self):
        return self.user


class TestGHManagerGetOrganization(TestInternalRetries,
                                   InternalRetriesHelper):

    def generate_errors(self, error, nerrors):
        for i in range(nerrors):
            self.gh.get_organization("mock").AndRaise(error)

    def mock_calls(self):
        self.gh.get_organization("mock").AndReturn(self.org)

    def run_function(self):
        return self.gh_manager.get_organization("mock")

    def get_output(self):
        return self.org


class TestGHManagerGetRepo(TestInternalRetries, InternalRetriesHelper):

    def generate_errors(self, error, nerrors):
        for i in range(nerrors):
            self.gh.get_repo("mock/mock").AndRaise(error)

    def mock_calls(self):
        self.gh.get_repo("mock/mock").AndReturn(self.repo)

    def run_function(self):
        return self.gh_manager.get_repo("mock/mock")

    def get_output(self):
        return self.repo


class TestGitHubRepositoryInit(TestInternalRetries, InternalRetriesHelper):

    def generate_errors(self, error, nerrors):
        for i in range(nerrors):
            self.gh.get_repo("mock/mock").AndRaise(error)

    def mock_calls(self):
        self.gh.get_repo("mock/mock").AndReturn(self.repo)

    def run_function(self):
        gh_repo = GitHubRepository(self.gh_manager, "mock", "mock")
        return gh_repo.repo

    def get_output(self):
        return self.repo


class TestGitHubRepositoryGetIssue(TestInternalRetries,
                                   InternalRetriesHelper):

    def setup_method(self, method):
        super(TestGitHubRepositoryGetIssue, self).setup_method(method)
        self.gh.get_repo("mock/mock").AndReturn(self.repo)

    def generate_errors(self, error, nerrors):
        for i in range(nerrors):
            self.repo.get_issue(1).AndRaise(error)

    def mock_calls(self):
        self.repo.get_issue(1).AndReturn(self.issue)

    def run_function(self):
        self.gh_repo = GitHubRepository(self.gh_manager, "mock", "mock")
        return self.gh_repo.get_issue(1)

    def get_output(self):
        return self.issue


class TestGitHubRepositoryGetPulls(TestInternalRetries,
                                   InternalRetriesHelper):

    def setup_method(self, method):
        super(TestGitHubRepositoryGetPulls, self).setup_method(method)
        self.gh.get_repo("mock/mock").AndReturn(self.repo)

    def generate_errors(self, error, nerrors):
        for i in range(nerrors):
            self.repo.get_pulls().AndRaise(error)

    def mock_calls(self):
        self.repo.get_pulls().AndReturn([self.pull])

    def run_function(self):
        self.gh_repo = GitHubRepository(self.gh_manager, "mock", "mock")
        return self.gh_repo.get_pulls()

    def get_output(self):
        return [self.pull]


class TestGitHubRepositoryGetPull(TestInternalRetries,
                                  InternalRetriesHelper):

    def setup_method(self, method):
        super(TestGitHubRepositoryGetPull, self).setup_method(method)
        self.gh.get_repo("mock/mock").AndReturn(self.repo)

    def generate_errors(self, error, nerrors):
        for i in range(nerrors):
            self.repo.get_pull(1).AndRaise(error)

    def mock_calls(self):
        self.repo.get_pull(1).AndReturn(self.pull)

    def run_function(self):
        self.gh_repo = GitHubRepository(self.gh_manager, "mock", "mock")
        return self.gh_repo.get_pull(1)

    def get_output(self):
        return self.pull
