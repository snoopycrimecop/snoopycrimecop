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

class MockGitRepo(GitHubRepository):
    PATH = os.path.abspath(".")

    def __init__(self, path, reset=False):
        if path is self.PATH:
            self.path =  os.path.abspath(path)
            self.reset = reset
            dbg("Register Git repository %s", path)
        else:
            raise Exception("Invalid Git repository")

class MockGitRepoManager(GitRepoManager):

    def create_instance(self, path, *args):
        repo = MockGitRepo(path, *args)
        return repo

class TestGHManager(unittest.TestCase):
    valid_path = MockGitRepo.PATH

    def setUp(self):
        self.gm = MockGitRepoManager()

    def testNoGitRepo(self):
        self.assertEqual(self.gm.get_current(), None)

    def testValidGitRepo(self):
        repo = self.gm.get_instance(self.valid_path)
        self.assertTrue(repo.path==self.valid_path)
        self.assertEqual(self.gm.dictionary[self.valid_path], repo)

    def testGitRepoReConnection(self):
        repo = MockGitRepo(self.valid_path)
        self.gm.dictionary[self.valid_path] = repo
        new_repo = self.gm.get_instance(self.valid_path)
        self.assertEqual(repo, new_repo)
    
    def testReset(self):
        repo = self.gm.get_instance(self.valid_path, True)
        self.assertTrue(repo.reset)

if __name__ == '__main__':
    unittest.main()