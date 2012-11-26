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
import github  # PyGithub
import subprocess
import logging
import threading
import argparse

fmt = """%(asctime)s %(levelname)-5.5s %(message)s"""
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
            message_from_pipe = self.pipeReader.readline()

            # If the line read is empty the pipe has been
            # closed, do a cleanup and exit
            # WARNING: I don't know if this method is correct,
            #          further study needed
            if len(message_from_pipe) == 0:
                self.pipeReader.close()
                os.close(self.fdRead)
                return
            # end if

            # Remove the trailing newline character frm the string
            # before sending it to the logger
            if message_from_pipe[-1] == os.linesep:
                message_to_log = message_from_pipe[:-1]
            else:
                message_to_log = message_from_pipe
            # end if

            # Send the text to the logger
            self._write(message_to_log)
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


class PullRequest(object):
    def __init__(self, repo, pull):
        self.pull = pull
        self.issue = repo.get_issue(self.get_number())
        dbg("login = %s", self.get_login())
        dbg("labels = %s", self.get_labels())
        dbg("base = %s", self.get_base())
        dbg("len(comments) = %s", len(self.get_comments()))

    def __contains__(self, key):
        return key in self.get_labels()

    def __repr__(self):
        return "  # PR %s %s '%s'" % (self.get_number(), self.get_login(), self.get_title())

    def test_directories(self):
        directories = []
        for comment in self.get_comments():
            lines = comment.splitlines()
            for line in lines:
                if line.startswith("--test"):
                    directories.append(line.replace("--test", ""))
        return directories

    def get_title(self):
        """Return the title of the Pull Request."""
        return self.pull.title

    def get_user(self):
        """Return the name of the Pull Request owner."""
        return self.pull.user

    def get_login(self):
        """Return the login of the Pull Request owner."""
        return self.pull.user.login

    def get_number(self):
        """Return the number of the Pull Request."""
        return int(self.pull.issue_url.split("/")[-1])

    def get_sha(self):
        """Return the SHA1 of the head of the Pull Request."""
        return self.pull.head.sha

    def get_base(self):
        """Return the branch against which the Pull Request is opened."""
        return self.pull.base.ref

    def get_labels(self):
        """Return the labels of the Pull Request."""
        return [x.name for x in  self.issue.labels]

    def get_comments(self):
        """Return the labels of the Pull Request."""
        if self.issue.comments:
            return [comment.body for comment in self.issue.get_comments()]
        else:
            return []

class Repository(object):

    def __init__(self, filters, reset=False):

        log.info("")
        [org_name, repo_name] = get_repository_info()
        if reset:
            dbg("Resetting...")
            call("git", "reset", "--hard", "HEAD")

        dbg("Check current status")
        call("git", "log", "--oneline", "-n", "1", "HEAD")
        call("git", "submodule", "status")
        self.reset = reset
        self.filters = filters

        # Creating Github instance
        try:
            self.token = call("git", "config", "--get", 
                "github.token", stdout = subprocess.PIPE).communicate()[0]
        except Exception:
            self.token = None

        if self.token:
            gh = GHWrapper(github.Github(self.token))
            dbg("Creating Github instance identified as %s", 
                gh.get_user().login)
        else:
            gh = GHWrapper(github.Github())
            dbg("Creating anonymous Github instance")
        requests = gh.rate_limiting
        dbg("Remaining requests: %s out of %s", requests[0], requests[1])

        self.org = gh.get_organization(org_name)
        try:
            self.repo = self.org.get_repo(repo_name)
        except:
            log.error("Failed to find %s", repo_name, exc_info=1)
        self.candidate_pulls = []
        self.modifications = 0
        self.find_candidates()

    def find_candidates(self):
        """Find candidate Pull Requests for merging."""
        dbg("## PRs found:")
        directories_log = None

        # Loop over pull requests opened aainst base
        pulls = [pull for pull in self.repo.get_pulls() if (pull.base.ref == self.filters["base"])]
        for pull in pulls:
            pullrequest = PullRequest(self.repo, pull)
            found = False
            labels = [x.lower() for x in pullrequest.get_labels()]

            if self.org.has_in_public_members(pullrequest.get_user()):
                found = True
            else:
                if self.filters["include"]:
                    whitelist = [filt for filt in self.filters["include"] if filt.lower() in labels]
                    if whitelist:
                        dbg("# ... Include %s", whitelist)
                        found = True

            if not found:
                continue

            # Exclude PRs if exclude labels are input
            if self.filters["exclude"]:
                blacklist = [filt for filt in self.filters["exclude"] if filt.lower() in labels]
                if blacklist:
                    dbg("# ... Exclude %s", blacklist)
                    continue

            if found:
                dbg(pullrequest)
                self.candidate_pulls.append(pullrequest)
                directories = pullrequest.test_directories()
                if directories:
                    if directories_log == None:
                        directories_log = open('directories.txt', 'w')
                    for directory in directories:
                        directories_log.write(directory)
                        directories_log.write("\n")
        self.candidate_pulls.sort(lambda a, b: cmp(a.get_number(), b.get_number()))

        # Cleanup
        if directories_log:
            directories_log.close()

    def info(self):
        for pullrequest in self.candidate_pulls:
            print "# %s" % " ".join(pullrequest.get_labels())
            print "%s %s by %s for \t\t[???]" % \
                (pullrequest.pr.issue_url, pullrequest.get_title(), pullrequest.get_login())
            print

    def merge(self, comment=False):
        """Merge candidate pull requests."""
        dbg("## Unique users: %s", self.unique_logins())
        for key, url in self.remotes().items():
            print key
            call("git", "remote", "add", key, url)
            call("git", "fetch", key)

        conflicting_pulls = []
        merged_pulls = []

        for pullrequest in self.candidate_pulls:
            premerge_sha, e = call("git", "rev-parse", "HEAD", stdout = subprocess.PIPE).communicate()
            premerge_sha = premerge_sha.rstrip("\n")

            try:
                call("git", "merge", "--no-ff", "-m", \
                        "%s: PR %s (%s)" % (self.commit_id(), pullrequest.get_number(), pullrequest.get_title()), pullrequest.get_sha())
                self.modifications += 1
                merged_pulls.append(pullrequest)
            except:
                call("git", "reset", "--hard", "%s" % premerge_sha)
                conflictingPRs.append(data)

                msg = "Conflicting PR #%g." % pullrequest.get_number()
                if os.environ.has_key("JOB_NAME") and  os.environ.has_key("BUILD_NUMBER"):
                    msg += "Removed from build %s #%s." % (os.environ.get("JOB_NAME"), \
                        os.environ.get("BUILD_NUMBER"))
                else:
                    msg += "."
                dbg(msg)

                if comment and self.token:
                    dbg("Adding comment to issue #%g." % pullrequest.get_number())
                    pullrequest.issue.create_comment(msg)

        if merged_pulls:
            log.info("Merged PRs:")
            for merged_pull in merged_pulls:
                log.info(merged_pull)

        if conflicting_pulls:
            log.info("Conflicting PRs (not included):")
            for conflicting_pull in conflicting_pulls:
                log.info(conflicting_pull)

        call("git", "submodule", "update")

    def submodules(self, info=False, comment=False):
        """Recursively merge PRs for each submodule."""

        submodule_paths = call("git", "submodule", "--quiet", "foreach", \
                "echo $path", \
                stdout=subprocess.PIPE).communicate()[0]

        cwd = os.path.abspath(os.getcwd())
        lines = submodule_paths.split("\n")
        while "".join(lines):
            directory = lines.pop(0).strip()
            try:
                submodule_repo = None
                cd(directory)
                submodule_repo = Repository(filters, self.reset)
                if info:
                    submodule_repo.info()
                else:
                    submodule_repo.merge(comment)
                submodule_repo.submodules(info)
                self.modifications += submodule_repo.modifications
            finally:
                try:
                    if submodule_repo:
                        submodule_repo.cleanup()
                finally:
                    cd(cwd)

        if self.modifications:
            call("git", "commit", "--allow-empty", "-a", "-n", "-m", \
                    "%s: Update all modules w/o hooks" % self.commit_id())

    def get_name(self):
        """Return name of the repository."""
        return self.repo.name

    def commit_id(self):
        """
        Return commit identifier generated from base branch, include and 
        exclude labels.
        """
        commit_id = "merge"+"_into_"+self.filters["base"]
        if self.filters["include"]:
            commit_id += "+" + "+".join(self.filters["include"])
        if self.filters["exclude"]:
            commit_id += "-" + "-".join(self.filters["exclude"])
        return commit_id

    def unique_logins(self):
        """Return a set of unique logins."""
        unique_logins = set()
        for pull in self.candidate_pulls:
            unique_logins.add(pull.get_login())
        return unique_logins

    def remotes(self):
        """Return remotes associated to unique login."""
        remotes = {}
        for user in self.unique_logins():
            key = "merge_%s" % user
            if self.repo.private:
                url = "git@github.com:%s/%s.git"  % (user, self.get_name())
            else:
                url = "git://github.com/%s/%s.git" % (user, self.get_name())
            remotes[key] = url
        return remotes

    def cleanup(self):
        """Remove remote branches created for merging."""
        for key in self.remotes().keys():
            try:
                call("git", "remote", "rm", key)
            except Exception:
                log.error("Failed to remove", key, exc_info=1)

def call(*command, **kwargs):
    for x in ("stdout", "stderr"):
        if x not in kwargs:
            kwargs[x] = logWrap
    dbg("Calling '%s'" % " ".join(command))
    p = subprocess.Popen(command, **kwargs)
    rc = p.wait()
    if rc:
        raise Exception("rc=%s" % rc)
    return p

def cd(directory):
    dbg("cd %s", directory)
    os.chdir(directory)

def get_repository_info():
    """
    Return organization and repository name of the current directory.

    Origin remote must be on Github, i.e. of type
    *github/organization/repository.git
    """

    originurl = call("git", "config", "--get", \
        "remote.origin.url", stdout = subprocess.PIPE, \
        stderr = subprocess.PIPE).communicate()[0]

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

    filters = {}
    filters["base"] = args.base
    filters["include"] = args.include
    filters["exclude"] = args.exclude
    main_repo = Repository(filters, args.reset)
    try:
        if not args.info:
            main_repo.merge(args.comment)
        main_repo.submodules(args.info, args.comment)  # Recursive

        if args.buildnumber:
            newbranch = "HEAD:%s/%g" % (args.base, args.build_number)
            call("git", "push", "team", newbranch)
    finally:
        main_repo.cleanup()
