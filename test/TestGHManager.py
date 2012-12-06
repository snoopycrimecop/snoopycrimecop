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
    TOKEN = "mytoken"
    USER = "test"
    PASSWORD = "password"

    def __init__(self, login_or_token = None, password = None):
        if login_or_token is None:
            self.user = None
        elif password is None:
            if login_or_token is self.TOKEN:
                self.user = login_or_token
            else:
                raise Exception("Invalid token")
        else:
            if login_or_token is self.USER:
                if password is self.PASSWORD:
                    self.user = login_or_token
                else:
                    raise Exception("Invalid password")
            else:
                raise Exception("Invalid user")

class MockGHWrapper(GHWrapper):

    def create_instance(self, *args):
        self.github = MockGithub(*args)

    def get_login(self):
        return self.github.user

class MockGHManager(GHManager):

    def create_instance(self, login_or_token = None, password = None):
        gh = MockGHWrapper(login_or_token, password)
        return gh

class TestGHManager(unittest.TestCase):
    valid_token = MockGithub.TOKEN
    valid_user = MockGithub.USER
    valid_password = MockGithub.PASSWORD

    def setUp(self):
        self.gm = MockGHManager()

    def testNoConnection(self):
        self.assertEqual(self.gm.get_current(), None)

    def testAnonymousConnection(self):
        gh = self.gm.get_instance()
        self.assertFalse(gh.get_login==None)
        self.assertEqual(self.gm.dictionary[None], gh)

    def testGoodTokenConnection(self):
        gh = self.gm.get_instance(self.valid_token)
        self.assertFalse(gh.get_login==self.valid_token)
        self.assertEqual(self.gm.dictionary[self.valid_token], gh)

    def testInvalidTokenConnection(self):
        invalid_token = "invalidtoken"
        self.assertRaises(Exception, self.gm.get_instance, invalid_token)
        self.assertFalse(invalid_token in self.gm.dictionary)

    def testUserConnection(self):
        gh = self.gm.get_instance(self.valid_user, self.valid_password)
        self.assertTrue(gh.get_login() is self.valid_user)
        self.assertEqual(self.gm.dictionary[self.valid_user], gh)
                    
    def testInvalidUserConnection(self):
        invaliduser = "invaliduser"
        self.assertRaises(Exception, self.gm.get_instance, (invaliduser, "password"))
        self.assertFalse(invaliduser in self.gm.dictionary)

    def testInvalidPasswordConnection(self):
        self.assertRaises(Exception, self.gm.get_instance, (self.valid_user, "invalidpassword"))
        self.assertFalse(self.valid_user in self.gm.dictionary)
        
    def testAnonymousReconnection(self):
        mock_gh = MockGHWrapper()
        self.gm.dictionary[None] = mock_gh
        gh = self.gm.get_instance(None)
        self.assertEqual(self.gm.dictionary[None], mock_gh)

    def testTokenReconnection(self):
        mock_gh = MockGHWrapper(self.valid_token)
        self.gm.dictionary[self.valid_token] = mock_gh
        gh = self.gm.get_instance(self.valid_token)
        self.assertEqual(self.gm.dictionary[self.valid_token], mock_gh)

    def testAnonymousReconnection(self):
        mock_gh = MockGHWrapper(self.valid_user, self.valid_password)
        self.gm.dictionary[self.valid_user] = mock_gh
        gh = self.gm.get_instance(self.valid_user)
        self.assertEqual(self.gm.dictionary[self.valid_user], mock_gh)
    
    def testGHSwitch(self):
        mock_gh = MockGHWrapper()
        mock_gh_2 = MockGHWrapper("test", "password")
        mock_gh_3 = MockGHWrapper(self.valid_token)
        self.gm.dictionary[None] = mock_gh
        self.gm.dictionary["test"] = mock_gh_2
        self.gm.dictionary[self.valid_token] = mock_gh_3

        gh = self.gm.get_instance(None)
        self.assertEqual(gh, mock_gh)
        self.assertEqual(self.gm.get_current(), mock_gh)
        gh2 = self.gm.get_instance("test")
        self.assertEqual(gh2, mock_gh_2)
        self.assertEqual(self.gm.get_current(), mock_gh_2)
        gh3 = self.gm.get_instance(self.valid_token)
        self.assertEqual(gh3, mock_gh_3)
        self.assertEqual(self.gm.get_current(), mock_gh_3)

if __name__ == '__main__':
    unittest.main()