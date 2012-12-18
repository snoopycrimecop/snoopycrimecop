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

import os
import uuid
import shutil
import unittest
import tempfile

from scc import *
from Sandbox import *
from subprocess import *


class TestMerge(SandboxTest):

    def setUp(self):
        
        super(TestMerge, self).setUp()
        
        # Setup
        self.user = self.gh.get_login()
        gh_repo = self.gh.gh_repo("snoopys-sandbox", "openmicroscopy")

        try:
            p = Popen(["git", "submodule", "update", "--init"])
            self.assertEquals(0, p.wait())
        except:
            os.chdir(self.path)
            raise
            
    def test(self):

        main(["merge","dev_4_4"])

    def testPush(self):

        main(["merge","dev_4_4" ,"--push", "test"])
        # This will clean the pushed branch
        remote = "git@github.com:%s/" % (self.user) + "%s.git"
        self.sandbox.rpush(":test", remote=remote)
            

if __name__ == '__main__':
    unittest.main()
