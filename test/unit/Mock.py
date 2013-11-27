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

from github.AuthenticatedUser import AuthenticatedUser
from github.Repository import Repository

from scc.git import GHManager
from scc.git import GitHubRepository

from mox import Mox


class MoxTestBase(object):

    def setup_method(self, method):
        self.mox = Mox()

    def teardown_method(self, method):
        self.mox.VerifyAll()


class MockTest(MoxTestBase):

    def setup_method(self, method):

        super(MockTest, self).setup_method(method)
        # Mocks
        self.gh = self.mox.CreateMock(GHManager)
        self.user = self.mox.CreateMock(AuthenticatedUser)
        self.org = self.mox.CreateMock(AuthenticatedUser)
        self.repo = self.mox.CreateMock(Repository)
        self.repo.organization = None

        self.user.login = "test"
        self.gh.get_repo("mock/mock").AndReturn(self.repo)
        self.mox.ReplayAll()

        self.gh_repo = GitHubRepository(self.gh, "mock", "mock")
