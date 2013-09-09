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

import unittest

from scc import UnrebasedPRs
from Mock import MockTest


class UnitTestCheck(MockTest):

    def setUp(self):
        MockTest.setUp(self)

    def testEmptyDictionaries(self):
        self.assertEqual(UnrebasedPRs.check({}, {}), {})

    def testMatchingDictionaries(self):
        d1 = {1: ['-to #2']}
        d2 = {2: ['-from #1']}
        self.assertEqual(UnrebasedPRs.check(d1, d2), {})
        self.assertEqual(UnrebasedPRs.check(d2, d1), {})

    def testMissingSourceComment(self):
        d1 = {1: ['-to #2']}
        d2 = {2: None}
        self.assertEqual(UnrebasedPRs.check(d1, d2), {2: '-from #1'})
        self.assertEqual(UnrebasedPRs.check(d2, d1), {2: '-from #1'})

    def testMissingTargetComment(self):
        d1 = {1: ['-from #2']}
        d2 = {2: None}
        self.assertEqual(UnrebasedPRs.check(d1, d2), {2: '-to #1'})
        self.assertEqual(UnrebasedPRs.check(d2, d1), {2: '-to #1'})

if __name__ == '__main__':
    import logging
    logging.basicConfig()
    unittest.main()
