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

import os
import pytest
from scc.git import get_token_or_user, git_version
from Sandbox import SandboxTest

mingitversion = pytest.mark.skipif(git_version() < (1, 7, 4),
                                   reason="Git 1.7.4 required")


class TestConfig(SandboxTest):

    def writeConfigFile(self, configString):
        with open(os.path.join(self.path, '.git', 'config'), 'w') as f:
            f.write(configString)

    @mingitversion
    def testEmptyConfig(self):
        assert get_token_or_user(local=True) is None

    @mingitversion
    def testUserConfig(self):
        uuid = self.uuid()
        self.writeConfigFile("[github]\n    user = %s" % uuid)
        assert get_token_or_user(local=True) == uuid

    @mingitversion
    def testTokenConfig(self):
        uuid = self.uuid()
        self.writeConfigFile("[github]\n    token = %s" % uuid)
        assert get_token_or_user(local=True) == uuid

    @mingitversion
    def testUserAndTokenConfig(self):
        uuid = self.uuid()
        self.writeConfigFile("[github]\n    user = 2\n    token = %s" % uuid)
        assert get_token_or_user(local=True) == uuid
