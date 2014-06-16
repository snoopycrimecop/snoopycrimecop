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

import pytest

from yaclifw.framework import main, Stop
from scc.git import CheckMilestone
from Sandbox import SandboxTest


class TestCheckMilestone(SandboxTest):

    def check_milestone(self, *args):
        args = ["check-milestone", "--no-ask"] + list(args)
        main(args=args, items=[(CheckMilestone.NAME, CheckMilestone)])

    def testNonExistingStartTag(self):
        with pytest.raises(Stop):
            self.check_milestone("0.0.0", "1.0.0")

    def testNonExistingEndTag(self):
        with pytest.raises(Stop):
            self.check_milestone("1.0.0", "0.0.0")

    def testNonExistingMilestone(self):
        with pytest.raises(Stop):
            self.check_milestone("1.0.0", "HEAD", "--set", "0.0.0")

    def testCheckMilestone(self):
        self.check_milestone("1.0.0", "1.1.1-TEST")
