#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2012-2013 University of Dundee & Open Microscopy Environment
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

import pytest

from scc.framework import parsers
from scc.git import Token
from Mock import MockTest

scopes = [
    'user', 'user:email', 'user:follow', 'public_repo', 'repo',
    'repo:status', 'delete_repo', 'notifications', 'gist']


class TestToken(MockTest):

    def setup_method(self, method):
        super(TestToken, self).setup_method(method)

        self.scc_parser, self.sub_parser = parsers()
        self.token = Token(self.sub_parser)
        self.default_scopes = ['public_repo']

    # Default arguments
    def testDefaults(self):
        ns = self.scc_parser.parse_args(["token", "create"])
        assert ns.scope == self.default_scopes
        assert not ns.no_set

    def testCreateNonDefaultScopes(self):
        ns = self.scc_parser.parse_args(
            ["token", "create", "-srepo", "-spublic_repo"])
        assert ns.scope == ["repo", "public_repo"]

    def testCreateNoSet(self):
        ns = self.scc_parser.parse_args(["token", "create", "--no-set"])
        assert ns.no_set

    # Authorization scopes
    @pytest.mark.parametrize('scope', scopes)
    def testAllowedScopes(self, scope):
        ns = self.scc_parser.parse_args(
            ["token", "create", "-s%s" % scope])
        assert ns.scope == [scope]

    def testNonAllowedScope(self):
        with pytest.raises(SystemExit):
            self.scc_parser.parse_args(
                ["token", "create", "-sinvalidscope"])
