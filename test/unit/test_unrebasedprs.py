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

from scc.git import UnrebasedPRs


class UnitTestCheck(unittest.TestCase):

    def setUp(self):
        self.d1 = {}
        self.d2 = {}
        self.m1 = {}
        self.m2 = {}

    def runCheck(self):
        self.assertEqual(UnrebasedPRs.check_directed_links(self.d1, self.d2),
                         self.m2)
        self.assertEqual(UnrebasedPRs.check_directed_links(self.d2, self.d1),
                         self.m1)

    def testEmptyDictionaries(self):
        self.runCheck()

    def testMatchingDictionaries(self):
        self.d1 = {1: ['-to #2']}
        self.d2 = {2: ['-from #1']}
        self.runCheck()

    def testMissingSourceComment(self):
        self.d1 = {1: ['-to #2']}
        self.d2 = {2: None}
        self.m2 = {2: ['-from #1']}
        self.runCheck()

    def testMissingTargetComment(self):
        self.d1 = {1: ['-from #2']}
        self.d2 = {2: None}
        self.m2 = {2: ['-to #1']}
        self.runCheck()

    def testMultipleSources(self):
        self.d1 = {1: ['-to #3'], 2: ['-to #3']}
        self.d2 = {3: ['-from #1', '-from #2']}
        self.runCheck()

    def testPartialMissingMultipleSources(self):
        self.d1 = {1: ['-to #3'], 2: ['-to #3']}
        self.d2 = {3: ['-from #1']}
        self.m2 = {3: ['-from #2']}
        self.runCheck()

    def testFullMissingMultipleSources(self):
        self.d1 = {1: ['-to #3'], 2: ['-to #3']}
        self.d2 = {3: None}
        self.m2 = {3: ['-from #1', '-from #2']}
        self.runCheck()

    def testMultipleTargets(self):
        self.d1 = {1: ['-from #3'], 2: ['-from #3']}
        self.d2 = {3: ['-to #1', '-to #2']}
        self.runCheck()

    def testPartialMissingMultipleTargets(self):
        self.d1 = {1: ['-from #3'], 2: ['-from #3']}
        self.d2 = {3: ['-to #1']}
        self.m2 = {3: ['-to #2']}
        self.runCheck()

    def testFullMissingMultipleTargets(self):
        self.d1 = {1: ['-from #3'], 2: ['-from #3']}
        self.d2 = {3: None}
        self.m2 = {3: ['-to #1', '-to #2']}
        self.runCheck()

    def testTrailingWhitespace(self):
        self.d1 = {1: ['-to #2']}
        self.d2 = {2: ['-from #1 ']}
        self.runCheck()

    def testTrailingComment(self):
        self.d1 = {1: ['-to #2 comment on the source']}
        self.d2 = {2: ['-from #1 comment on the target']}
        self.runCheck()

    def testTrailingPeriod(self):
        self.d1 = {1: ['-to #2.']}
        self.d2 = {2: ['-from #1.']}
        self.runCheck()


if __name__ == '__main__':
    import logging
    logging.basicConfig()
    unittest.main()
