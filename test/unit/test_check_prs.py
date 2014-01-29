#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2013-2014 University of Dundee & Open Microscopy Environment
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

from scc.git import CheckPRs
import pytest

no_link_types = [None, -1]
prefixes = [("to", "from"), ("from", "to")]


class TestCheckDirectedLinks(object):

    def setup_method(self, method):
        self.links = {}
        self.mismatch = {}

    def check_directed_links(self):
        assert CheckPRs.check_directed_links(self.links) == self.mismatch

    def testEmptyDictionaries(self):
        self.check_directed_links()

    @pytest.mark.parametrize("source_prefix,target_prefix", prefixes)
    def testSingleLink(self, source_prefix, target_prefix):
        self.links = {
            1: ['-%s #2' % source_prefix],
            2: ['-%s #1' % target_prefix]}
        self.check_directed_links()

    @pytest.mark.parametrize("source_prefix,target_prefix", prefixes)
    @pytest.mark.parametrize("no_link_type", no_link_types)
    def testBrokenSingleLink(self, source_prefix, target_prefix,
                             no_link_type):
        self.links = {1: ['-%s #2' % source_prefix], 2: no_link_type}
        self.mismatch = {2: ['-%s #1' % target_prefix]}
        self.check_directed_links()

    @pytest.mark.parametrize("source_prefix,target_prefix", prefixes)
    def testMultiLink(self, source_prefix, target_prefix):
        self.links = {
            1: ['-%s #3' % source_prefix],
            2: ['-%s #3' % source_prefix],
            3: ['-%s #1' % target_prefix, '-%s #2' % target_prefix]}
        self.check_directed_links()

    @pytest.mark.parametrize("source_prefix,target_prefix", prefixes)
    def testPartialMultiLink(self, source_prefix, target_prefix):
        self.links = {
            1: ['-%s #3' % source_prefix],
            2: ['-%s #3' % source_prefix],
            3: ['-%s #1' % target_prefix]}
        self.mismatch = {3: ['-%s #2' % target_prefix]}
        self.check_directed_links()

    @pytest.mark.parametrize("source_prefix,target_prefix", prefixes)
    @pytest.mark.parametrize("no_link_type", no_link_types)
    def testBrokenMultiLink(self, source_prefix, target_prefix, no_link_type):
        self.links = {
            1: ['-%s #3' % source_prefix],
            2: ['-%s #3' % source_prefix],
            3: no_link_type}
        self.mismatch = {
            3: ['-%s #1' % target_prefix, '-%s #2' % target_prefix]}
        self.check_directed_links()

    @pytest.mark.parametrize("source_prefix,target_prefix", prefixes)
    @pytest.mark.parametrize("comment", ["  ", ".", " comment"])
    def testTrailingComment(self, source_prefix, target_prefix, comment):
        self.links = {
            1: ['-%s #2' % source_prefix],
            2: ['-%s #1%s' % (target_prefix, comment)]}
        self.check_directed_links()
