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

from scc.git import UnrebasedPRs


class TestCheckDirectedLinks(object):

    def setup_method(self, method):
        self.links = {}
        self.mismatch = {}

    def check_directed_links(self):
        assert UnrebasedPRs.check_directed_links(self.links) == self.mismatch

    def testEmptyDictionaries(self):
        self.check_directed_links()

    def testMatchingDictionaries(self):
        self.links = {1: ['-to #2'], 2: ['-from #1']}
        self.check_directed_links()

    def testMissingSourceComment(self):
        self.links = {1: ['-to #2'], 2: None}
        self.mismatch = {2: ['-from #1']}
        self.check_directed_links()

    def testMissingTargetComment(self):
        self.links = {1: ['-from #2'], 2: None}
        self.mismatch = {2: ['-to #1']}
        self.check_directed_links()

    def testMultipleSources(self):
        self.links = {1: ['-to #3'], 2: ['-to #3']}
        self.mismatch = {3: ['-from #1', '-from #2']}
        self.check_directed_links()

    def testPartialMissingMultipleSources(self):
        self.links = {1: ['-to #3'], 2: ['-to #3'], 3: ['-from #1']}
        self.mismatch = {3: ['-from #2']}
        self.check_directed_links()

    def testFullMissingMultipleSources(self):
        self.links = {1: ['-to #3'], 2: ['-to #3'], 3: None}
        self.mismatch = {3: ['-from #1', '-from #2']}
        self.check_directed_links()

    def testMultipleTargets(self):
        self.links = {1: ['-from #3'], 2: ['-from #3']}
        self.mismatch = {3: ['-to #1', '-to #2']}
        self.check_directed_links()

    def testPartialMissingMultipleTargets(self):
        self.links = {1: ['-from #3'], 2: ['-from #3'], 3: ['-to #1']}
        self.mismatch = {3: ['-to #2']}
        self.check_directed_links()

    def testFullMissingMultipleTargets(self):
        self.links = {1: ['-from #3'], 2: ['-from #3'], 3: None}
        self.mismatch = {3: ['-to #1', '-to #2']}
        self.check_directed_links()

    def testTrailingWhitespace(self):
        self.links = {1: ['-to #2'], 2: ['-from #1 ']}
        self.check_directed_links()

    def testTrailingComment(self):
        self.links = {
            1: ['-to #2 comment on the source'],
            2: ['-from #1 comment on the target']}
        self.check_directed_links()

    def testTrailingPeriod(self):
        self.links = {1: ['-to #2.'], 2: ['-from #1.']}
        self.check_directed_links()
