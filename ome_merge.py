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

"""
Automatically merge all pull requests with any of the given labels.
It assumes that you have checked out the target branch locally and
have updated any submodules. The SHA1s from the PRs will be merged
into the current branch. AFTER the PRs are merged, any open PRs for
each submodule with the same tags will also be merged into the
CURRENT submodule sha1. A final commit will then update the submodules.
"""

import os
import sys
import github  # PyGithub3
import subprocess
import logging

logging.basicConfig(level=10)
log = logging.getLogger("ome_merge")
dbg = log.debug


class GHWrapper(object):

    def __init__(self, delegate):
        self.delegate = delegate

    def __getattr__(self, key):
        dbg("gh.%s", key)
        return super(GHWrapper, self).__getattr__(key)


class StreamRedirect(object):
    """
    Since all server components should exclusively using the logging module
    any output to stdout or stderr is caught and logged at "WARN". This is
    useful, especially in the case of Windows, where stdout/stderr is eaten.
    """

    def __init__(self, logger):
        self.logger = logger
        self.internal = logging.getLogger("StreamRedirect")
        self.softspace = False

    def flush(self):
        pass

    def write(self, msg):
        msg = msg.strip()
        if msg:
            self.logger.warn(msg)

    def __getattr__(self, name):
        self.internal.warn("No attribute: %s" % name)


class Data(object):
    def __init__(self, repo, pr):
        self.sha = pr.head.sha
        self.login = pr.head.user.login
        self.title = pr.title
        self.num = int(pr.issue_url.split("/")[-1])
        self.issue = repo.get_issue(self.num)
        self.label_objs = self.issue.labels
        self.labels = [x.name for x in self.label_objs]

    def __contains__(self, key):
        return key in self.labels

    def __repr__(self):
        return "# %s %s '%s' (Labels: %s)" % \
                (self.sha, self.login, self.title, ",".join(self.labels))


class OME(object):

    def __init__(self, filters, name="openmicroscopy"):
        self.name = name
        self.filters = filters
        self.remotes = {}
        self.gh = github.Github()
        self.org = self.gh.get_organization("openmicroscopy")
        try:
            self.repo = self.org.get_repo(name)
        except:
            log.error("Failed to find %s", name, exc_info=1)
        self.pulls = self.repo.get_pulls()
        self.storage = []
        self.unique_logins = set()
        dbg("## PRs found:")
        for pr in self.pulls:
            data = Data(self.repo, pr)
            print data.labels
            found = False
            for filter in filters:
                print filter
                if filter in data.labels:
                    dbg("# ... Found %s", filter)
                    found = True
            if found:
                self.unique_logins.add(data.login)
                dbg(data)
                self.storage.append(data)

    def cd(self, dir):
        dbg("cd %s", dir)

    def call(self, *command, **kwargs):
        for x in ("stdout", "stderr"):
            if x not in kwargs:
                kwargs[x] = StreamRedirect(log)
        p = subprocess.Popen(command, **kwargs)
        rc = p.wait()
        if rc:
            raise Exception("rc=%s" % rc)
        return p

    def merge(self):
        dbg("## Unique users: %s", self.unique_logins)
        for user in self.unique_logins:
            key = "merge_%s" % user
            url = "git://github.com/%s/%s.git" % (user, self.name)
            self.call("git", "remote", "add", key, url)
            self.remotes[key] = url
            dbg("# Added %s=%s", key, url)
            self.call("git", "fetch", key)

        for data in self.storage:
            dbg("# Merging %s", data.num)
            self.call("git", "merge", "--no-ff", "-m", \
                    "Merge gh-%s (%s)" % (data.num, data.title), data.sha)

    def submodules(self):

        o, e = self.call("git", "submodule", "foreach", \
                "git config --get remote.origin.url", \
                stdout=subprocess.PIPE).communicate()

        cwd = os.path.abspath(os.getcwd())
        lines = o.split("\n")
        while "".join(lines):
            dir = lines.pop(0).strip()
            dir = dir.split(" ")[1][1:-1]
            repo = lines.pop(0).strip()
            repo = repo.split("/")[-1]
            if repo.endswith(".git"):
                repo = repo[:-4]

            try:
                ome = None
                self.cd(dir)
                ome = OME(self.filters, repo)
                ome.merge()
                ome.submodules()
            finally:
                try:
                    if ome:
                        ome.cleanup()
                finally:
                    self.cd(cwd)

        self.call("git", "commit", "-a", "-m", "Update all modules")

    def cleanup(self):
        for k, v in self.remotes.items():
            try:
                self.call("git", "remote", "rm", k)
            except Exception, e:
                log.error("Failed to remove", k, exc_info=1)


if __name__ == "__main__":
    filters = sys.argv[1:]
    if not filters:
        print "Usage: ome_merge.py label1 [label2 label3 ...]"
        sys.exit(2)

    ome = OME(filters)
    try:
        ome.merge()
        ome.submodules()  # Recursive
    finally:
        ome.cleanup()
