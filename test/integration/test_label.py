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

from yaclifw.framework import main
from scc.git import Label
from Sandbox import SandboxTest


class TestLabel(SandboxTest):

    def get_repo_labels(self):
        labels = self.sandbox.origin.get_labels()
        return "\n".join([x.name for x in labels])

    def get_issue_labels(self, issue):
        labels = self.sandbox.origin.get_issue(issue).get_labels()
        return "\n".join([x.name for x in labels])

    def label(self, *args):
        args = ["label", "--no-ask"] + list(args)
        main(args=args, items=[(Label.NAME, Label)])

    def testAvailable(self, capsys):
        self.label("--available")
        out, err = capsys.readouterr()
        assert out.rstrip() == self.get_repo_labels()

    def testListLabels(self, capsys):
        self.label("--list", "1")
        out, err = capsys.readouterr()
        assert out.rstrip() == self.get_issue_labels(1)

    def testListNoLabel(self, capsys):
        self.label("--list", "2")
        out, err = capsys.readouterr()
        assert out.rstrip() == self.get_issue_labels(2)
