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
import shutil
import unittest

from scc import *

class TestDeploy(unittest.TestCase):

    def setUp(self):
        self.folder = os.path.abspath("deploy_test")
        self.live_folder = self.folder + ".live"
        self.new_folder = self.folder + ".new"
        self.tmp_folder = self.folder + ".tmp"
        
        # Create folder
        self.oldfilename = "a"
        self.oldfile = os.path.join(self.folder, self.oldfilename)
        self.olddirname = "d"
        self.olddir = os.path.join(self.folder, self.olddirname)
        os.mkdir(self.folder)
        open(self.oldfile, "w")
        os.mkdir(self.olddir)
        
        # Create tmp folder
        self.newfilename = "b"
        self.newfile = os.path.join(self.tmp_folder, self.newfilename)
        os.mkdir(self.tmp_folder)
        open(self.newfile, "w")

    def tearDown(self):
        for path in [self.folder, self.live_folder, self.tmp_folder,
            self.new_folder]:
            if os.path.exists(path):
                if os.path.islink(path) or os.path.isfile(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)

    def testDeployInitInvalidFolder(self):
        self.assertRaises(Stop,  main, ["deploy", "--init", "invalid_folder"])

    def testDeployInitExistingLiveFolder(self):
        os.mkdir(self.live_folder)
        self.assertRaises(Stop,  main, ["deploy", "--init", self.folder])

    def testDeployInit(self):
        main(["deploy", "--init", self.folder])
        self.assertTrue(os.path.isdir(self.live_folder))
        self.assertTrue(os.path.islink(self.folder))
        self.assertTrue(os.path.isfile(self.oldfile))
        self.assertTrue(os.path.isdir(self.olddir))

    def testDeployNoInit(self):
        self.assertRaises(Stop,  main, ["deploy", self.folder])

    def testDeployWrongInit(self):
        os.mkdir(self.live_folder)
        self.assertRaises(Stop,  main, ["deploy", self.folder])

    def testDeployInvalidFolder(self):
        main(["deploy", "--init", self.folder])
        self.assertRaises(Stop,  main, ["deploy", "invalid_folder"])

    def testDeployMissingTmpFolder(self):
        main(["deploy", "--init", self.folder])
        shutil.rmtree(self.tmp_folder)
        self.assertRaises(Stop,  main, ["deploy", self.folder])

    def testDeployExistingNewFolder(self):
        main(["deploy", "--init", self.folder])
        os.mkdir(self.new_folder)
        self.assertRaises(Stop,  main, ["deploy", self.folder])

    def testDeploy(self):
        main(["deploy", "--init", self.folder])
        main(["deploy", self.folder])
        self.assertFalse(os.path.exists(self.tmp_folder))
        self.assertFalse(os.path.exists(self.new_folder))
        self.assertFalse(os.path.exists(self.oldfile))
        self.assertFalse(os.path.exists(self.olddir))
        self.assertTrue(os.path.isfile(os.path.join(self.folder, self.newfilename)))

if __name__ == '__main__':
    unittest.main()
