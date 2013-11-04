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

from scc.git import GHManager

import socket
from ssl import SSLError

from mox import MoxTestBase


class MockGHManager(GHManager):

    def create_instance(self):
        pass


class TestGHManager(MoxTestBase):

    def setUp(self):

        super(TestGHManager, self).setUp()
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

    def generate_errors(self, error, nerrors):

        for i in range(nerrors):
            self.gh.get_user("mock").AndRaise(error)

    def testNoError(self):
        self.gh.get_user("mock").AndReturn(self.user)
        self.mox.ReplayAll()

        self.assertEqual(self.gh_manager.get_user("mock"), self.user)

    def testNoRetryError(self):
        self.generate_errors(self.no_retry_exception, 1)
        self.mox.ReplayAll()

        self.assertRaises(GithubException, self.gh_manager.get_user, "mock")

    def testOneServerError(self):
        self.generate_errors(self.server_error, 1)
        self.gh.get_user("mock").AndReturn(self.user)
        self.mox.ReplayAll()

        self.assertEqual(self.gh_manager.get_user("mock"), self.user)

    def testTwoServerErrors(self):
        self.generate_errors(self.server_error, 2)
        self.gh.get_user("mock").AndReturn(self.user)
        self.mox.ReplayAll()

        self.assertEqual(self.gh_manager.get_user("mock"), self.user)

    def testThreeServerErrors(self):
        self.generate_errors(self.server_error, 3)
        self.gh.get_user("mock").AndReturn(self.user)
        self.mox.ReplayAll()

        self.assertEqual(self.gh_manager.get_user("mock"), self.user)

    def testFourServerErrors(self):
        self.generate_errors(self.server_error, 4)
        self.mox.ReplayAll()

        self.assertRaises(GithubException, self.gh_manager.get_user, "mock")

    def testOneSocketTimeout(self):
        self.generate_errors(self.socket_timeout, 1)
        self.gh.get_user("mock").AndReturn(self.user)
        self.mox.ReplayAll()

        self.assertEqual(self.gh_manager.get_user("mock"), self.user)

    def testTwoSocketTimeouts(self):
        self.generate_errors(self.socket_timeout, 2)
        self.gh.get_user("mock").AndReturn(self.user)
        self.mox.ReplayAll()

        self.assertEqual(self.gh_manager.get_user("mock"), self.user)

    def testThreeSocketTimeouts(self):
        self.generate_errors(self.socket_timeout, 3)
        self.gh.get_user("mock").AndReturn(self.user)
        self.mox.ReplayAll()

        self.assertEqual(self.gh_manager.get_user("mock"), self.user)

    def testFourSocketTimeouts(self):
        self.generate_errors(self.socket_timeout, 4)
        self.mox.ReplayAll()

        self.assertRaises(socket.timeout, self.gh_manager.get_user, "mock")

    def testOneSSLError(self):
        self.generate_errors(self.ssl_error, 1)
        self.gh.get_user("mock").AndReturn(self.user)
        self.mox.ReplayAll()

        self.assertEqual(self.gh_manager.get_user("mock"), self.user)

    def testTwoSSLErrors(self):
        self.generate_errors(self.ssl_error, 2)
        self.gh.get_user("mock").AndReturn(self.user)
        self.mox.ReplayAll()

        self.assertEqual(self.gh_manager.get_user("mock"), self.user)

    def testThreeSSLErrors(self):
        self.generate_errors(self.ssl_error, 3)
        self.gh.get_user("mock").AndReturn(self.user)
        self.mox.ReplayAll()

        self.assertEqual(self.gh_manager.get_user("mock"), self.user)

    def testFourSSLErrors(self):
        self.generate_errors(self.ssl_error, 4)
        self.mox.ReplayAll()

        self.assertRaises(SSLError, self.gh_manager.get_user, "mock")
