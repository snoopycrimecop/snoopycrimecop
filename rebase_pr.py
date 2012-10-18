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
import difflib
import getpass

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

def getRepository(*command, **kwargs):
    command = ["git", "config", "--get", "remote.origin.url"]
    dbg("Calling '%s'" % " ".join(command))
    p = subprocess.Popen(command, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    originname = p.communicate()

    retcode = p.poll()
    if retcode:
        raise subprocess.CalledProcessError(retcode, command, output=originname[0])

    dir = os.path.dirname(originname[0])
    assert "github" in dir, 'Origin URL %s is not on GitHub' % dir

    base = os.path.basename(originname[0])
    repository_name = os.path.splitext(base)[0]
    return repository_name

def getUser(*command, **kwargs):
    command = ["git", "config", "--get", "github.user"]
    dbg("Calling '%s'" % " ".join(command))
    p = subprocess.Popen(command, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    user = p.stdout.read()[0:-1]

    retcode = p.poll()
    if retcode:
        raise subprocess.CalledProcessError(retcode, command, output=user)

    return user

revlist_cmd = lambda x: ["git","rev-list","--first-parent","%s" % x]

def getRevList(commit):

    p = subprocess.Popen(revlist_cmd(commit), stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    dbg("Calling '%s'" % " ".join(revlist_cmd(commit)))
    (revlist, stderr) = p.communicate('')

    if stderr or p.returncode:
        print "Error output was:\n%s" % stderr
        print "Output was:\n%s" % stdout
        return False

    return revlist.splitlines()

def findBranchingPoint(topic_branch, main_branch):
    # See http://stackoverflow.com/questions/1527234/finding-a-branch-point-with-git

    topic_revlist = getRevList(topic_branch)
    main_revlist = getRevList(main_branch)

    # Compare sequences
    s = difflib.SequenceMatcher(None, topic_revlist, main_revlist)
    matching_block = s.get_matching_blocks()
    if matching_block[0].size == 0:
        raise Exception("No matching block found")

    sha1 = main_revlist[matching_block[0].b]
    log.info("Branching SHA1: %s" % sha1[0:6])
    return sha1

def rebase(newbase, upstream, sha1):   
    command = ["git", "rebase", "--onto", "origin/%s" % newbase, "%s" % upstream, "%s" % sha1]
    dbg("Calling '%s'" % " ".join(command))
    p = subprocess.Popen(command)
    rc = p.wait()
    if rc:
        raise Exception("rc=%s" % rc)

if __name__ == "__main__":

    # Create argument parser
    parser = argparse.ArgumentParser(description='Rebase Pull Requests opened against a specific base branch.')
    parser.add_argument('PR', type=int, help="The number of the pull request to rebase")
    parser.add_argument('newbase', type=str, help="The branch of origin onto which the PR should be rebased")
    args = parser.parse_args()

    # Create Github instance
    if os.environ.has_key("GITHUB_TOKEN"):
        token = os.environ["GITHUB_TOKEN"]
        gh = GHWrapper(github.Github(token))
        dbg("Creating Github instance identified as %s", gh.get_user().login)
    else:
        gh = GHWrapper(github.Github())
        dbg("Creating anonymous Github instance")

    rate_limiting = gh.rate_limiting
    dbg("Remaining requests: %s out of %s", rate_limiting[0], rate_limiting[1] )

    org = "openmicroscopy"
    log.info("Organization: %s", org)
    org = gh.get_organization(org)

    try:
        repo = getRepository()
        log.info("Repository: %s", repo)
        repo = org.get_repo(repo)
    except:
        log.error("Failed to find %s", name, exc_info=1)

    try:
        pr = repo.get_pull(args.PR)
        log.info("PR %g: %s opened by %s against %s", args.PR, pr.title, pr.head.user.name, pr.base.ref)
        pr_head = pr.head.sha
        log.info("Head: %s", pr_head[0:6])
        log.info("Merged: %s", pr.is_merged())
    except:
        log.error("Failed to find PR %g", args.PR, exc_info=1)

    branching_sha1 = findBranchingPoint(pr_head, "origin/"+pr.base.ref)
    rebase(args.newbase, branching_sha1[0:6], pr_head)
