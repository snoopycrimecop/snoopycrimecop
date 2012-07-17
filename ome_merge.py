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
"""

import sys
import github # PyGithub3
import subprocess


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

    def __init__(self):
        self.gh = github.Github()
        self.org = self.gh.get_organization("openmicroscopy")
        self.repo = self.org.get_repo("openmicroscopy")
        self.pulls = self.repo.get_pulls()
        self.storage = []
        self.unique_logins = set()
        print "## PRs found:"
        for pr in self.pulls:
            data = Data(self.repo, pr)
            self.unique_logins.add(data.login)
            print data
            self.storage.append(data)
        self.remotes = {}

    def call(self, *command):
        p = subprocess.Popen(command)
        rc = p.wait()
        if rc:
            raise Exception("rc=%s" % rc)

    def merge(self, labels):
        print "## Unique users:", self.unique_logins
        for user in self.unique_logins:
            key = "merge_%s" % user
            url = "git://github.com/%s/openmicroscopy.git" % user
            self.call("git", "remote", "add", key, url)
            self.remotes[key] = url
            print "# Added", key, url
            self.call("git", "fetch", key)

        for data in self.storage:
            print "# Merging", data.num
            found = False
            for label in labels:
                if label in data.labels:
                    print "# ... Found", label
                    found = True
            if found:
                self.call("git", "merge", "--no-ff", "-m", \
                        "Merge gh-%s (%s)" % (data.num, data.title), data.sha)

    def cleanup(self):
        for k, v in self.remotes.items():
            try:
                self.call("git", "remote", "rm", k)
            except Exception, e:
                print e
                print "Failed to remove", k


if __name__ == "__main__":
    labels = sys.argv[1:]
    if not labels:
        print "Usage: ome_merge.py label1 [label2 label3 ...]"
        sys.exit(2)

    ome = OME()
    try:
        ome.merge(labels)
    finally:
        ome.cleanup()
