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
import threading

fmt="""%(asctime)s %(levelname)-5.5s %(message)s"""
logging.basicConfig(level=10, format=fmt)

log = logging.getLogger("ome_merge")
dbg = log.debug


class GHWrapper(object):

    def __init__(self, delegate):
        self.delegate = delegate

    def __getattr__(self, key):
        dbg("gh.%s", key)
        return getattr(self.delegate, key)


# http://codereview.stackexchange.com/questions/6567/how-to-redirect-a-subprocesses-output-stdout-and-stderr-to-logging-module
class LoggerWrapper(threading.Thread):
    """
    Read text message from a pipe and redirect them
    to a logger (see python's logger module),
    the object itself is able to supply a file
    descriptor to be used for writing

    fdWrite ==> fdRead ==> pipeReader
    """

    def __init__(self, logger, level=logging.DEBUG):
        """
        Setup the object with a logger and a loglevel
        and start the thread
        """

        # Initialize the superclass
        threading.Thread.__init__(self)

        # Make the thread a Daemon Thread (program will exit when only daemon
        # threads are alive)
        self.daemon = True

        # Set the logger object where messages will be redirected
        self.logger = logger

        # Set the log level
        self.level = level

        # Create the pipe and store read and write file descriptors
        self.fdRead, self.fdWrite = os.pipe()

        # Create a file-like wrapper around the read file descriptor
        # of the pipe, this has been done to simplify read operations
        self.pipeReader = os.fdopen(self.fdRead)

        # Start the thread
        self.start()
    # end __init__

    def fileno(self):
        """
        Return the write file descriptor of the pipe
        """
        return self.fdWrite
    # end fileno

    def run(self):
        """
        This is the method executed by the thread, it
        simply read from the pipe (using a file-like
        wrapper) and write the text to log.
        NB the trailing newline character of the string
           read from the pipe is removed
        """

        # Endless loop, the method will exit this loop only
        # when the pipe is close that is when a call to
        # self.pipeReader.readline() returns an empty string
        while True:

            # Read a line of text from the pipe
            messageFromPipe = self.pipeReader.readline()

            # If the line read is empty the pipe has been
            # closed, do a cleanup and exit
            # WARNING: I don't know if this method is correct,
            #          further study needed
            if len(messageFromPipe) == 0:
                self.pipeReader.close()
                os.close(self.fdRead)
                return
            # end if

            # Remove the trailing newline character frm the string
            # before sending it to the logger
            if messageFromPipe[-1] == os.linesep:
                messageToLog = messageFromPipe[:-1]
            else:
                messageToLog = messageFromPipe
            # end if

            # Send the text to the logger
            self._write(messageToLog)
        # end while
    # end run

    def _write(self, message):
        """
        Utility method to send the message
        to the logger with the correct loglevel
        """
        self.logger.log(self.level, message)
    # end write


logWrap = LoggerWrapper(log)


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
        self.gh = GHWrapper(github.Github())
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
            found = False
            for filter in filters:
                if filter in data.labels:
                    dbg("# ... Found %s", filter)
                    found = True
            if found:
                self.unique_logins.add(data.login)
                dbg(data)
                self.storage.append(data)

    def cd(self, dir):
        dbg("cd %s", dir)
        os.chdir(dir)

    def call(self, *command, **kwargs):
        for x in ("stdout", "stderr"):
            if x not in kwargs:
                kwargs[x] = logWrap
        dbg("Calling '%s'" % " ".join(command))
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
            self.call("git", "fetch", key)

        for data in self.storage:
            self.call("git", "merge", "--no-ff", "-m", \
                    "Merge gh-%s (%s)" % (data.num, data.title), data.sha)

        self.call("git", "submodule", "update")

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

        self.call("git", "commit", "--allow-empty", "-a", "-n", "-m", "Update all modules w/o hooks")

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
