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

import os

from scc.framework import main
from scc.version import call_git_describe, Version, version_file


class TestVersion(object):

    def setup_method(self, method):
        if os.path.isfile(version_file):
            os.rename(version_file, version_file + '.bak')
        assert not os.path.isfile(version_file)

    def teardown_method(self, method):
        if os.path.isfile(version_file + '.bak'):
            os.rename(version_file + '.bak', version_file)

    def read_version_file(self):
        version = None
        with open(version_file) as f:
            version = f.readlines()[0]
        return version.strip()

    def testVersionOutput(self, capsys):
        main(["version"], items=[("version", Version)])
        out, err = capsys.readouterr()
        assert out.rstrip() == call_git_describe()

    def testVersionFile(self, capsys):
        main(["version"], items=[("version", Version)])
        assert os.path.isfile(version_file)
        out, err = capsys.readouterr()
        assert out.rstrip() == self.read_version_file()

    def testVersionOverwrite(self, capsys):
        with open(version_file, 'w') as f:
            f.write('test\n')
        assert self.read_version_file() == 'test'
        try:
            main(["version"], items=[("version", Version)])
            out, err = capsys.readouterr()
            assert out.rstrip() == self.read_version_file()
        finally:
            os.remove(version_file)

    def testNonGitRepository(self, capsys):
        cwd = os.getcwd()
        try:
            # Move to a non-git repository and ensure call_git_describe
            # returns None
            os.chdir('..')
            assert call_git_describe() is None
            main(["version"], items=[("version", Version)])
            out, err = capsys.readouterr()
            assert out.rstrip() == self.read_version_file()
        finally:
            os.chdir(cwd)

    def testGitRepository(self):
        cwd = os.getcwd()
        import tempfile
        import shutil
        from subprocess import Popen, PIPE
        sandbox_url = "https://github.com/openmicroscopy/snoopys-sandbox.git"
        path = tempfile.mkdtemp("", "sandbox-", "..")
        path = os.path.abspath(path)
        # Read the version for the current Git repository
        main(["version"], items=[("version", Version)])
        version = self.read_version_file()
        try:
            # Clone snoopys-sanbox
            p = Popen(["git", "clone", sandbox_url, path],
                      stdout=PIPE, stderr=PIPE)
            assert p.wait() == 0
            os.chdir(path)
            # Check git describe returns a different version number
            assert call_git_describe() != version
            # Read the version again and check the file is unmodified
            main(["version"], items=[("version", Version)])
            assert self.read_version_file() == version
        finally:
            try:
                shutil.rmtree(path)
            finally:
                os.chdir(cwd)
