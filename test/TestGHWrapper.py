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

class MockGithub(object):

    def __init__(self, login_or_token = None, password = None):
        if password is not None:
            self.user = login_or_token
        elif login_or_token is not None:
            self.user = login_or_token
        else:
            self.user = None

class MockGHWrapper(GHWrapper):
    FACTORY = MockGithub

    def get_login(self):
        return self.github.user

class MockGHManager(GHManager):
    FACTORY = MockGHWrapper

class TestGHManager(unittest.TestCase):

    def setUp(self):
        self.gm = MockGHManager()

    def testAnonymousConnection(self):
        gh = self.gm.get_github()
        self.assertFalse(gh.get_login==None)
        self.assertEqual(self.gm.gh_dictionary[None], gh)

    def testUserConnection(self):
        gh = self.gm.get_github("test", "password")
        self.assertTrue(gh.get_login() is "test")
        self.assertEqual(self.gm.gh_dictionary["test"], gh)

    def testTokenConnection(self):
        gh = self.gm.get_github("abcdef")
        self.assertFalse(gh.get_login=="abcdef")
        self.assertEqual(self.gm.gh_dictionary["abcdef"], gh)
    
    def testAnonymousReconnection(self):
        mock_gh = MockGHWrapper()
        self.gm.gh_dictionary[None] = mock_gh
        gh = self.gm.get_github(None)
        self.assertEqual(self.gm.gh_dictionary[None], mock_gh)
    
    def testGHSwitch(self):
        mock_gh = MockGHWrapper()
        mock_gh_2 = MockGHWrapper("test", "password")
        mock_gh_3 = MockGHWrapper("abcdef")
        self.gm.gh_dictionary[None] = mock_gh
        self.gm.gh_dictionary["test"] = mock_gh_2
        self.gm.gh_dictionary["abcdef"] = mock_gh_3

        gh = self.gm.get_github(None)
        self.assertEqual(gh, mock_gh)
        gh2 = self.gm.get_github("test")
        self.assertEqual(gh2, mock_gh_2)
        gh3 = self.gm.get_github("abcdef")
        self.assertEqual(gh3, mock_gh_3)

if __name__ == '__main__':
    unittest.main()