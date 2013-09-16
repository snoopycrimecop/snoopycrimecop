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

import sys
import unittest
from StringIO import StringIO

from scc import main
from Sandbox import SandboxTest


class TestLabel(SandboxTest):

    def setUp(self):
        super(TestLabel, self).setUp()
        self.output = StringIO()
        self.saved_stdout = sys.stdout
        sys.stdout = self.output

    def tearDown(self):
        self.output.close()
        sys.stdout = self.saved_stdout
        super(TestLabel, self).tearDown()

    def get_repo_labels(self):
        labels = self.sandbox.origin.get_labels()
        return "\n".join([x.name for x in labels])

    def get_issue_labels(self, issue):
        labels = self.sandbox.origin.get_issue(issue).get_labels()
        return "\n".join([x.name for x in labels])

    def testAvailable(self):
        main(["label", "--no-ask", "--available"])
        self.assertEquals(self.output.getvalue().rstrip(),
                          self.get_repo_labels())

    def testListLabels(self):
        main(["label", "--no-ask", "--list", "1"])
        self.assertEquals(self.output.getvalue().rstrip(),
                          self.get_issue_labels(1))

    def testListNoLabel(self):
        main(["label", "--no-ask", "--list", "2"])
        self.assertEquals(self.output.getvalue(),
                          self.get_issue_labels(2))

if __name__ == '__main__':
    unittest.main()
