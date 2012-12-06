#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2012 Glencoe Software, Inc. All Rights Reserved.
# Use is subject to license terms supplied in LICENSE.txt
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
from scc import *

class MockGHRepo(GitHubRepository):
    USERS = ["openmicroscopy", "snoopycrimecop"]
    REPO = "openmicroscopy"

    def __init__(self, user, repo):
        if user in self.USERS and repo is self.REPO:
            self.owner = user
            self.name = repo
        else:
            raise Exception("Invalid repository")
    
    def get_owner(self):
        return self.owner

class MockGHRepoManager(GHRepoManager):

    def create_instance(self, key):
        repo = MockGHRepo(key[0], key[1])
        return repo

class TestGHManager(unittest.TestCase):
    valid_users = MockGHRepo.USERS
    valid_repo = MockGHRepo.REPO

    def setUp(self):
        self.gm = MockGHRepoManager()

    def testNoRepoConnection(self):
        self.assertEqual(self.gm.get_current(), None)

    def testGoodRepoConnection(self):
        repo = self.gm.get_instance((self.valid_users[0], self.valid_repo))
        self.assertTrue(repo.owner==self.valid_users[0])
        self.assertTrue(repo.name==self.valid_repo)
        self.assertEqual(self.gm.dictionary[(self.valid_users[0], self.valid_repo)], repo)

    def testMultipeRepoConnection(self):
        repo1 = self.gm.get_instance((self.valid_users[0], self.valid_repo))
        repo2 = self.gm.get_instance((self.valid_users[1], self.valid_repo))
        self.assertTrue(repo2.owner==self.valid_users[1])
        self.assertTrue(repo2.name==repo1.name)
        self.assertEqual(self.gm.dictionary[(self.valid_users[0], self.valid_repo)], repo1)
        self.assertEqual(self.gm.dictionary[(self.valid_users[1], self.valid_repo)], repo2)
    
    def testGoodRepoReConnection(self):
        repo1 = MockGHRepo(self.valid_users[0], self.valid_repo)
        repo2 = MockGHRepo(self.valid_users[1], self.valid_repo)
        self.gm.dictionary[(self.valid_users[0], self.valid_repo)] = repo1
        self.gm.dictionary[(self.valid_users[1], self.valid_repo)] = repo2
        new_repo2 = self.gm.get_instance((self.valid_users[1], self.valid_repo))
        self.assertTrue(new_repo2.owner==self.valid_users[1])
        self.assertTrue(new_repo2.name==self.valid_repo)
        self.assertEqual(repo2, new_repo2)
        self.assertEqual(self.gm.get_current(), repo2)
        new_repo1 = self.gm.get_instance((self.valid_users[0], self.valid_repo))
        self.assertTrue(new_repo1.owner==self.valid_users[0])
        self.assertTrue(new_repo1.name==self.valid_repo)
        self.assertEqual(repo1, new_repo1)
        self.assertEqual(self.gm.get_current(), repo1)

if __name__ == '__main__':
    unittest.main()