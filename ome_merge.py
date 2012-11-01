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
import github  # PyGithub
import subprocess
import logging
import threading
import argparse

fmt="""%(asctime)s %(levelname)-5.5s %(message)s"""
logging.basicConfig(level=10, format=fmt)

log = logging.getLogger("ome_merge")
dbg = log.debug
logging.getLogger('github').setLevel(logging.INFO)
log.setLevel(logging.DEBUG)

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
        self.repo = repo
        self.pr = pr
        self.sha = pr.head.sha
        self.base = pr.base.ref
        self.user = pr.user
        self.login = pr.user.login
        self.title = pr.title
        self.num = int(pr.issue_url.split("/")[-1])
        self.issue = repo.get_issue(self.num)
        self.label_objs = self.issue.labels
        self.labels = [x.name for x in self.label_objs]
        dbg("login = %s", self.login)
        dbg("labels = %s", self.labels)
        dbg("base = %s", self.base)
        self.comments = []
        if self.issue.comments:
            for x in self.issue.get_comments():
                self.comments.append(x.body)
        dbg("len(comments) = %s", len(self.comments))

    def __contains__(self, key):
        return key in self.labels

    def __repr__(self):
        return "  # PR %s %s '%s'" % (self.num, self.login, self.title)

    def test_directories(self):
        directories = []
        for comment in self.comments:
            lines = comment.splitlines()
            for line in lines:
                if line.startswith("--test"):
                    directories.append(line.replace("--test", ""))
        return directories

class OME(object):

    def __init__(self, base, reset, exclude, include):

        log.info("")
        [org, name] = self.getRepositoryInfo()
        if reset:
            dbg("Resetting...")
            self.call("git", "reset", "--hard", "HEAD")

        dbg("Check current status")
        self.call("git", "log", "--oneline", "-n", "1", "HEAD")
        self.call("git", "submodule", "status")
        self.name = name
        self.reset = reset
        self.base = base

        # Create commit message using base, exclude & include
        self.commit_msg = "merge"+"_into_"+base
        self.include = include
        if include:
            self.commit_msg += "+" + "+".join(include)
        self.exclude = exclude
        if exclude:
            print exclude
            self.commit_msg += "-" + "-".join(exclude)

        self.remotes = {}

        # Creating Github instance
        try:
            self.token, e = self.call("git","config","--get","github.token", stdout = subprocess.PIPE).communicate()
        except Exception:
            self.token = None

        if self.token:
            self.gh = GHWrapper(github.Github(self.token))
            dbg("Creating Github instance identified as %s", self.gh.get_user().login)
        else:
            self.gh = GHWrapper(github.Github())
            dbg("Creating anonymous Github instance")
        requests = self.gh.rate_limiting
        dbg("Remaining requests: %s out of %s", requests[0], requests[1] )

        self.org = self.gh.get_organization(org)
        try:
            self.repo = self.org.get_repo(name)
        except:
            log.error("Failed to find %s", name, exc_info=1)
        self.pulls = self.repo.get_pulls()
        self.storage = []
        self.modifications = 0
        self.unique_logins = set()
        dbg("## PRs found:")

        directories_log = None

        for pr in self.pulls:
            data = Data(self.repo, pr)
            found = False

            # Check the base ref of the PR
            if data.base == base:
                if self.org.has_in_public_members(data.user):
                    found = True
                else:
                    if include:
                        for filter in include:
                            if filter.lower() in [x.lower() for x in data.labels]:
                                dbg("# ... Include %s", filter)
                                found = True

            # Exclude PRs if exclude labels are input
            if found and exclude:
                for filter in exclude:
                    if filter.lower() in [x.lower() for x in data.labels]:
                        dbg("# ... Exclude %s", filter)
                        found = False
                        break

            if found:
                self.unique_logins.add(data.login)
                dbg(data)
                self.storage.append(data)
                directories = data.test_directories()
                if directories:
                    if directories_log == None:
                        directories_log = open('directories.txt', 'w')
                    for directory in directories:
                        directories_log.write(directory)
                        directories_log.write("\n")
        self.storage.sort(lambda a, b: cmp(a.num, b.num))

        # Cleanup
        if directories_log:
            directories_log.close()

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

    def info(self):
        for data in ome.storage:
            print "# %s" % " ".join(data.labels)
            print "%s %s by %s for \t\t[???]" % \
                (data.pr.issue_url, data.title, data.login)
            print

    def merge(self, comment=False):
        dbg("## Unique users: %s", self.unique_logins)
        for user in self.unique_logins:
            key = "merge_%s" % user
            if self.repo.private:
                url = "git@github.com:%s/%s.git"  % (user, self.name)
            else:
                url = "git://github.com/%s/%s.git" % (user, self.name)
            self.call("git", "remote", "add", key, url)
            self.remotes[key] = url
            self.call("git", "fetch", key)

        conflictingPRs = []
        mergedPRs = []

        for data in self.storage:
            premerge_sha, e = self.call("git", "rev-parse", "HEAD", stdout = subprocess.PIPE).communicate()

            try:
                self.call("git", "merge", "--no-ff", "-m", \
                        "%s: PR %s (%s)" % (self.commit_msg, data.num, data.title), data.sha)
                self.modifications += 1
                mergedPRs.append(data)
            except:
                self.call("git", "reset", "--hard", "%s" % premerge_sha[0:6])
                conflictingPRs.append(data)

                msg = "Conflicting PR #%g." % data.num
                if os.environ.has_key("JOB_NAME") and  os.environ.has_key("BUILD_NUMBER"):
                    msg += "Removed from build %s #%s." % (os.environ.get("JOB_NAME"), \
                        os.environ.get("BUILD_NUMBER"))
                else:
                    msg += "."
                dbg(msg)

                if comment and self.token:
                    dbg("Adding comment to issue #%g." % data.num)
                    data.issue.create_comment(msg)

        if mergedPRs:
            log.info("Merged PRs:")
            for mergedPR in mergedPRs:
                log.info(mergedPR)

        if conflictingPRs:
            log.info("Conflicting PRs (not included):")
            for conflictingPR in conflictingPRs:
                log.info(conflictingPR)

        self.call("git", "submodule", "update")

    def submodules(self, info=False, comment=False):

        o, e = self.call("git", "submodule", "--quiet", "foreach", \
                "echo $path", \
                stdout=subprocess.PIPE).communicate()

        cwd = os.path.abspath(os.getcwd())
        lines = o.split("\n")
        while "".join(lines):
            dir = lines.pop(0).strip()
            try:
                ome = None
                self.cd(dir)
                ome = OME(self.base, self.reset, self.exclude, self.include)
                if info:
                    ome.info()
                else:
                    ome.merge(comment)
                ome.submodules(info)
                self.modifications += ome.modifications
            finally:
                try:
                    if ome:
                        ome.cleanup()
                finally:
                    self.cd(cwd)

        if self.modifications:
            self.call("git", "commit", "--allow-empty", "-a", "-n", "-m", \
                    "%s: Update all modules w/o hooks" % self.commit_msg)

    def getRepositoryInfo(self):
        originurl, e = self.call("git", "config", "--get", \
            "remote.origin.url", stdout = subprocess.PIPE, \
            stderr = subprocess.PIPE).communicate()

        # Read organization from origin URL
        dirname = os.path.dirname(originurl)
        assert "github" in dirname, 'Origin URL %s is not on GitHub' % dirname
        org = os.path.basename(dirname)
        if ":" in dirname:
            org = org.split(":")[-1]

        # Read repository from origin URL
        basename = os.path.basename(originurl)
        repo = os.path.splitext(basename)[0]
        log.info("Repository: %s/%s", org, repo)
        return [org , repo]

    def cleanup(self):
        for k, v in self.remotes.items():
            try:
                self.call("git", "remote", "rm", k)
            except Exception, e:
                log.error("Failed to remove", k, exc_info=1)



def pushTeam(base, build_number):
    newbranch = "HEAD:%s/%g" % (base, build_number)
    command = ["git", "push", "team", newbranch]
    dbg("Calling '%s'" % " ".join(command))
    p = subprocess.Popen(command, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

    rc = p.wait()
    if rc:
        raise Exception("rc=%s" % rc)
    return p

if __name__ == "__main__":

    # Create argument parser
    parser = argparse.ArgumentParser(description='Merge Pull Requests opened against a specific base branch.')
    parser.add_argument('--reset', action='store_true',
        help='Reset the current branch to its HEAD')
    parser.add_argument('--info', action='store_true',
        help='Display merge candidates but do not merge them')
    parser.add_argument('--comment', action='store_true',
        help='Add comment to conflicting PR')
    parser.add_argument('base', type=str)
    parser.add_argument('--include', nargs="*",
        help='PR labels to include in the merge')
    parser.add_argument('--exclude', nargs="*",
        help='PR labels to exclude from the merge')
    parser.add_argument('--buildnumber', type=int, default=None,
        help='The build number to use to push to team.git')
    args = parser.parse_args()

    log.info("Merging PR based on: %s", args.base)
    log.info("Excluding PR labelled as: %s", args.exclude)
    log.info("Including PR labelled as: %s", args.include)

    ome = OME(args.base, args.reset, args.exclude, args.include)
    try:
        if not args.info:
            ome.merge(args.comment)
        ome.submodules(args.info, args.comment)  # Recursive

        if args.buildnumber:
            pushTeam(args.base, args.buildnumber)
    finally:
        ome.cleanup()
