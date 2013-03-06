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

import unittest

from github.AuthenticatedUser import AuthenticatedUser
from github.Repository import Repository

from scc import GHManager
from scc import GitHubRepository

from mox import Mox


class MockTest(unittest.TestCase):

    def setUp(self):

        # Mocks
        self.mox = Mox()
        self.gh = self.mox.CreateMock(GHManager)
        self.user = self.mox.CreateMock(AuthenticatedUser)
        self.org = self.mox.CreateMock(AuthenticatedUser)
        self.repo = self.mox.CreateMock(Repository)
        self.repo.organization = None

        self.gh.get_user("mock").AndReturn(self.user)
        self.user.get_repo("mock").AndReturn(self.repo)
        self.mox.ReplayAll()

        self.gh_repo = GitHubRepository(self.gh, "mock", "mock")

    def tearDown(self):
        try:
            self.mox.VerifyAll()
        finally:
            self.mox.UnsetStubs()
