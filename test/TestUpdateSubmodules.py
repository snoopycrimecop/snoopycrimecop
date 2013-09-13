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

import unittest

from scc import main
from Sandbox import SandboxTest


class TestMerge(SandboxTest):

    def setUp(self):

        super(TestMerge, self).setUp()
        self.init_submodules()

    def testPush(self):

        self.sandbox.checkout_branch("dev_4_4")
        self.sandbox.reset()

        submodule_branch = "merge/dev_4_4/submodules"
        main(["update-submodules", "--no-ask", "dev_4_4", "--push",
              submodule_branch])
        remote = "git@github.com:%s/" % (self.user) + "%s.git"
        self.sandbox.rpush(":%s" % submodule_branch, remote=remote)


if __name__ == '__main__':
    import logging
    logging.basicConfig()
    unittest.main()
