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
import subprocess

from scc.framework import Stop, main
from scc.git import TagRelease
from Sandbox import SandboxTest


class TestTagRelease(SandboxTest):

    def setup_method(self, method):

        super(TestTagRelease, self).setup_method(method)
        self.new_version = '5.0.0-beta1'
        self.tag_prefix = None

    def has_new_prefixed_tag(self, repo):

        if self.tag_prefix:
            full_tag = self.tag_prefix + self.new_version
        else:
            full_tag = repo.get_tag_prefix() + self.new_version
        return repo.has_local_tag(full_tag)

    def tag_release(self, *args):
        args = ["tag-release", "--no-ask"] + list(args)
        main(args=args, items=[("tag-release", TagRelease)])

    @pytest.mark.parametrize('submodules', [True, False])
    @pytest.mark.parametrize('shallow_option', [None, '--shallow'])
    def testSubmodules(self, shallow_option, submodules):
        """Test tagging on repository with/or without submodules"""

        if submodules:
            self.init_submodules()
        if shallow_option:
            self.tag_release(self.new_version, shallow_option)
        else:
            self.tag_release(self.new_version)
        assert self.has_new_prefixed_tag(self.sandbox)
        if submodules and not shallow_option:
            for submodule in self.sandbox.submodules:
                assert self.has_new_prefixed_tag(submodule)

    @pytest.mark.parametrize('version', ['v5.0.0-beta1', '0.0.0beta1'])
    def testInvalidVersionNumber(self, version):
        """Test invalid version number"""

        with pytest.raises(Stop):
            self.tag_release(version)

    def testExitingTag(self):
        """Test existing tag"""

        # Create local tag and check local existence
        subprocess.Popen(
            ["git", "tag", 'v.' + self.new_version],
            stdout=subprocess.PIPE).communicate()
        assert self.sandbox.has_local_tag('v.' + self.new_version)

        # Test Stop is thrown by tag-release command
        with pytest.raises(Stop):
            self.tag_release(self.new_version)

    def testInvalidTag(self):
        """Test invalid tag reference name"""

        # Test Stop is thrown by tag-release command
        with pytest.raises(Stop):
            self.tag_release(self.new_version + "..")

    @pytest.mark.parametrize('tag_prefix', ['v', 'demo/'])
    def testPrefix(self, tag_prefix):
        """Test prefix argument"""

        self.tag_prefix = tag_prefix
        self.tag_release(self.new_version, '--prefix', tag_prefix)
        assert self.has_new_prefixed_tag(self.sandbox)
