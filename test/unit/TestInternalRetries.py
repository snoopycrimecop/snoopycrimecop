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
from github import Github

from scc.git import GHManager, GitHubRepository

import socket
from ssl import SSLError

from mox import MoxTestBase


class InternalRetriesHelper(object):

    def mock_calls(self):
        pass

    def run_function(self):
        pass

    def get_output(self):
        pass

    def passes(self):
        self.assertEqual(self.run_function(), self.get_output())

    def fails_with(self, error):
        self.assertRaises(error, self.run_function)

    def testNoError(self):
        self.mock_calls()
        self.mox.ReplayAll()
        self.passes()

    def testNoRetryError(self):
        self.generate_errors(self.no_retry_exception, 1)
        self.mox.ReplayAll()
        self.fails_with(GithubException)

    def testOneServerError(self):
        self.generate_errors(self.server_error, 1)
        self.mock_calls()
        self.mox.ReplayAll()
        self.passes()

    def testTwoServerErrors(self):
        self.generate_errors(self.server_error, 2)
        self.mock_calls()
        self.mox.ReplayAll()

        self.passes()

    def testThreeServerErrors(self):
        self.generate_errors(self.server_error, 3)
        self.mock_calls()
        self.mox.ReplayAll()
        self.passes()

    def testFourServerErrors(self):
        self.generate_errors(self.server_error, 4)
        self.mox.ReplayAll()
        self.fails_with(GithubException)

    def testOneSocketTimeout(self):
        self.generate_errors(self.socket_timeout, 1)
        self.mock_calls()
        self.mox.ReplayAll()
        self.passes()

    def testTwoSocketTimeouts(self):
        self.generate_errors(self.socket_timeout, 2)
        self.mock_calls()
        self.mox.ReplayAll()
        self.passes()

    def testThreeSocketTimeouts(self):
        self.generate_errors(self.socket_timeout, 3)
        self.mock_calls()
        self.mox.ReplayAll()
        self.passes()

    def testFourSocketTimeouts(self):
        self.generate_errors(self.socket_timeout, 4)
        self.mox.ReplayAll()
        self.fails_with(socket.timeout)

    def testOneSSLError(self):
        self.generate_errors(self.ssl_error, 1)
        self.mock_calls()
        self.mox.ReplayAll()
        self.passes()

    def testTwoSSLErrors(self):
        self.generate_errors(self.ssl_error, 2)
        self.mock_calls()
        self.mox.ReplayAll()
        self.passes()

    def testThreeSSLErrors(self):
        self.generate_errors(self.ssl_error, 3)
        self.mock_calls()
        self.mox.ReplayAll()
        self.passes()

    def testFourSSLErrors(self):
        self.generate_errors(self.ssl_error, 4)
        self.mox.ReplayAll()
        self.fails_with(SSLError)


class TestInternalRetries(MoxTestBase):

    def setUp(self):

        class MockGHManager(GHManager):

            def create_instance(self):
                pass

        super(TestInternalRetries, self).setUp()
        # Define mock objects
        self.gh = self.mox.CreateMock(Github)
        self.user = self.mox.CreateMock(AuthenticatedUser)
        self.user.login = "mock"
        self.org = self.mox.CreateMock(AuthenticatedUser)
        self.repo = self.mox.CreateMock(Repository)
        self.repo.organization = None

        # Define mock maanager
        self.gh_manager = MockGHManager()
        self.gh_manager.github = self.gh
        self.gh_manager.login_or_token = "mock"

        # Define errors to test
        self.server_error = GithubException(502, 'Server Error')
        self.no_retry_exception = GithubException(-1, 'No retry')
        self.socket_timeout = socket.timeout()
        self.ssl_error = SSLError()


class TestGHManager(TestInternalRetries, InternalRetriesHelper):

    def generate_errors(self, error, nerrors):
        for i in range(nerrors):
            self.gh.get_user("mock").AndRaise(error)

    def mock_calls(self):
        self.gh.get_user("mock").AndReturn(self.user)

    def run_function(self):
        return self.gh_manager.get_user("mock")

    def get_output(self):
        return self.user


class TestGitHubRepository(TestInternalRetries, InternalRetriesHelper):

    def generate_errors(self, error, nerrors):
        for i in range(nerrors):
            self.gh.get_user("mock").AndRaise(error)

    def mock_calls(self):
        self.gh.get_user("mock").AndReturn(self.user)
        self.user.get_repo("mock").AndReturn(self.repo)

    def run_function(self):
        gh_repo = GitHubRepository(self.gh_manager, "mock", "mock")
        return gh_repo.repo

    def get_output(self):
        return self.repo
