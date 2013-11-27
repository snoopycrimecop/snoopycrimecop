#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2012-2013 Glencoe Software, Inc. All Rights Reserved.
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
import pytest

from scc.framework import main, Stop
from scc.deploy import Deploy


class TestDeployCommand(object):

    def setup_method(self, method):
        self.folder = os.path.abspath("deploy_test")
        self.live_folder = self.folder + ".live"
        self.tmp_folder = self.folder + ".tmp"

        # Initialize old folder with file and directory
        os.mkdir(self.folder)
        oldfile = os.path.join(self.folder, "a")
        open(oldfile, "w")
        self.oldtargetfile = os.path.join(self.live_folder, "a")
        olddir = os.path.join(self.folder, "d")
        os.mkdir(olddir)
        self.oldtargetdir = os.path.join(self.live_folder, "d")

    def deploy(self, *args):
        args = ["deploy"] + list(args)
        main(args=args, items=[("deploy", Deploy)])

    def createBrokenSymlink(self, folder):

        # Create broken symboic link
        brokenlink = os.path.join(folder, "brokensymlink")
        badsource = os.path.join(folder, "nonexistingsource")
        os.symlink(badsource, brokenlink)
        assert os.path.lexists(brokenlink) is True
        assert os.path.exists(brokenlink) is False

        return os.path.join(self.folder, "brokensymlink")

    def teardown_method(self, method):
        for path in [self.folder, self.live_folder, self.tmp_folder]:
            if os.path.exists(path):
                if os.path.islink(path) or os.path.isfile(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)


class TestDeployInit(TestDeployCommand):

    def testInvalidFolder(self):
        with pytest.raises(Stop):
            self.deploy("--init", "invalid_folder")

    def testExistingLiveFolder(self):
        os.mkdir(self.live_folder)
        with pytest.raises(Stop):
            self.deploy("--init", self.folder)

    def testPasses(self):
        self.deploy("--init", self.folder)
        assert os.path.isdir(self.live_folder) is True
        assert os.path.islink(self.folder) is True
        assert os.path.isfile(self.oldtargetfile) is True
        assert os.path.isdir(self.oldtargetdir) is True

    def testBrokenSymlink(self):
        targetlink = self.createBrokenSymlink(self.folder)
        self.deploy("--init", self.folder)
        assert os.path.lexists(targetlink) is False
        assert os.path.exists(targetlink) is False


class TestDeploy(TestDeployCommand):

    def setup_method(self, method):

        super(TestDeploy, self).setup_method(method)
        # Create tmp folder for content replacement
        os.mkdir(self.tmp_folder)
        newfile = os.path.join(self.tmp_folder, "b")
        open(newfile, "w")
        self.newtargetfile = os.path.join(self.live_folder, "b")

    def testNoInit(self):
        with pytest.raises(Stop):
            self.deploy(self.folder)

    def testWrongInit(self):
        os.mkdir(self.live_folder)
        with pytest.raises(Stop):
            self.deploy(self.folder)

    def testInvalidFolder(self):
        self.deploy("--init", self.folder)
        with pytest.raises(Stop):
            self.deploy("invalid_folder")

    def testMissingTmpFolder(self):
        self.deploy("--init", self.folder)
        shutil.rmtree(self.tmp_folder)
        with pytest.raises(Stop):
            self.deploy(self.folder)

    def testPasses(self):
        self.deploy("--init", self.folder)
        self.deploy(self.folder)
        assert os.path.exists(self.tmp_folder) is False
        assert os.path.exists(self.oldtargetfile) is False
        assert os.path.exists(self.oldtargetdir) is False
        assert os.path.isfile(self.newtargetfile) is True

    def testBrokenSymlink(self):
        targetlink = self.createBrokenSymlink(self.tmp_folder)
        self.deploy("--init", self.folder)
        self.deploy(self.folder)
        assert os.path.lexists(targetlink) is False
        assert os.path.exists(targetlink) is False

if __name__ == '__main__':
    unittest.main()
