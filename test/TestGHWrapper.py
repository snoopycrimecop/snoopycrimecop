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
from ome_merge import *

class MockGHWrapper(GHWrapper):
    def __init__(self, token = None):
        self.delegate = {}

class TestGHManager(unittest.TestCase):

    def setUp(self):
        self.gm = GHManager()

    def testAnonymousGithub(self):
        gh = get_github(None)
        self.assertFalse(gh.get_user==None)

    def testGHDictionary(self):
        gh = self.gm.get_github(None)
        self.assertEqual(self.gm.gh_dictionary[None], gh)
    
    def testGHReconnection(self):
        mock_gh = MockGHWrapper()
        self.gm.gh_dictionary[None] = mock_gh
        gh = self.gm.get_github(None)
        self.assertEqual(self.gm.gh_dictionary[None], mock_gh)
    
    def testGHSwitch(self):
        mock_gh = MockGHWrapper()
        mock_gh_2 = MockGHWrapper()
        token = 100
        self.gm.gh_dictionary[None] = mock_gh
        self.gm.gh_dictionary[token] = mock_gh_2
        gh = self.gm.get_github(None)
        self.assertEqual(gh, mock_gh)
        gh2 = self.gm.get_github(token)
        self.assertEqual(gh2, mock_gh_2)

if __name__ == '__main__':
    unittest.main()