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
import uuid
import shutil
import logging
import tempfile

from scc.git import get_github, get_token_or_user
from subprocess import Popen

sandbox_url = "https://github.com/openmicroscopy/snoopys-sandbox.git"


class SandboxTest(object):

    def setup_method(self, method):
        # Basic logging configuration so if a test fails we can see
        # the statements at WARN or ERROR at least.
        logging.basicConfig()
        self.method = method.__name__
        self.cwd = os.getcwd()
        self.token = get_token_or_user(local=False)
        self.gh = get_github(self.token, dont_ask=True)
        self.user = self.gh.get_login()
        self.path = tempfile.mkdtemp("", "sandbox-", ".")
        self.path = os.path.abspath(self.path)
        try:
            with open(os.devnull, 'w') as dev_null:
                p = Popen(["git", "clone", "-q", sandbox_url, self.path],
                          stdout=dev_null, stderr=dev_null)
                assert p.wait() == 0
            self.sandbox = self.gh.git_repo(self.path)
            self.origin_remote = "origin"
        except:
            try:
                shutil.rmtree(self.path)
            finally:
                # Return to cwd regardless.
                os.chdir(self.cwd)
            raise
        # If we succeed, then we change to this dir.
        os.chdir(self.path)

    def shortDescription(self):
        return None

    def init_submodules(self):
        """
        Fetch submodules after cloning the repository
        """

        try:
            with open(os.devnull, 'w') as dev_null:
                p = Popen(["git", "submodule", "update", "--init"],
                          stdout=dev_null, stderr=dev_null)
                assert p.wait() == 0
        except:
            os.chdir(self.path)
            raise

    def uuid(self):
        """
        Return a string representing a uuid.uuid4
        """
        return str(uuid.uuid4())

    def fake_branch(self, head="master", commits=None):
        """
        Return a local branch with a list of commits, defaults to a single
        commit adding a unique file
        """

        name = self.uuid()
        if commits is None:
            commits = [(name, "hi")]

        self.sandbox.new_branch(name, head=head)

        for n in xrange(len(commits)):
            fname, txt = commits[n]
            fname = os.path.join(self.path, fname)
            with open(fname, 'w') as f:
                f.write(txt)
            self.sandbox.add(fname)
            self.sandbox.commit("%d: Writing %s" % (n, fname))
            self.sandbox.get_status()

        return name

    def add_remote(self):
        """
        Add the remote of the authenticated Github user
        """
        if self.user not in self.sandbox.list_remotes():
            remote_url = "https://%s:x-oauth-basic@github.com/%s/%s.git" \
                % (self.token, self.user, self.sandbox.origin.name)
            self.sandbox.add_remote(self.user, remote_url)

    def rename_origin_remote(self, new_name):
        """
        Rename the remote used for the upstream repository
        """
        self.sandbox.call("git", "remote", "rename", self.origin_remote,
                          new_name)
        self.origin_remote = new_name

    def push_branch(self, branch):
        """
        Push a local branch to GitHub
        """
        self.add_remote()
        self.sandbox.push_branch(branch, remote=self.user)

    def open_pr(self, branch, base):
        """
        Push a local branch and open a PR against the selected base
        """
        self.push_branch(branch)
        new_pr = self.sandbox.origin.open_pr(
            title="test %s" % branch,
            description="This is a call to Sandbox.open_pr by %s"
            % self.method,
            base=base,
            head="%s:%s" % (self.user, branch))

        return new_pr

    def teardown_method(self, method):
        try:
            self.sandbox.cleanup()
        finally:
            try:
                shutil.rmtree(self.path)
            finally:
                # Return to cwd regardless.
                os.chdir(self.cwd)
