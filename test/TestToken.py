#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2012 University of Dundee & Open Microscopy Environment
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

import os
import unittest

from scc import *
from Mock import MockTest


class UnitTestToken(MockTest):

    def setUp(self):
        MockTest.setUp(self)

        self.scc_parser, self.sub_parser = parsers()
        self.token = Token(self.sub_parser)
        self.default_scopes = ['public_repo']

    # Default arguments
    def testDefaultScopes(self):
        ns = self.scc_parser.parse_args(["token", "--create"])
        self.assertEqual(ns.scopes, self.default_scopes)

    def testNonDefaultScopes(self):
        ns = self.scc_parser.parse_args(["token", "--create", "-srepo", "-spublic_repo"])
        self.assertEqual(ns.scopes, ["repo", "public_repo"])

if __name__ == '__main__':
    import logging
    logging.basicConfig()
    unittest.main()
