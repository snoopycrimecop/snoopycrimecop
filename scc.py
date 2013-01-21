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

Git management script for the Open Microscopy Environment (OME)
This script is used to simplify various branching workflows
by wrapping both local git and Github access.

See the documentation on each Command subclass for specifics.

Environment variables:
    SCC_DEBUG_LEVEL     default: logging.INFO

"""

import re
import os
import sys
import time
import subprocess
import logging
import threading
import difflib

argparse_loaded = True
try:
    import argparse
except ImportError:
    print >> sys.stderr, \
        "Module argparse missing. Install via 'pip install argparse'"
    argparse_loaded = False

github_loaded = True
try:
    import github  # PyGithub
    try:
        github.GithubException(0, "test")
    except AttributeError:
        print >> sys.stderr, \
            "Conflicting github module. Uninstall PyGithub3"
        github_loaded = False
except ImportError, ie:
    print >> sys.stderr, \
        "Module github missing. Install via 'pip install PyGithub'"
    github_loaded = False

SCC_DEBUG_LEVEL = logging.INFO
if "SCC_DEBUG_LEVEL" in os.environ:
    try:
        SCC_DEBUG_LEVEL = int(os.environ.get("SCC_DEBUG_LEVEL"))
    except:
        SCC_DEBUG_LEVEL = 10 # Assume poorly formatted means "debug"

# Read Jenkins environment variables
jenkins_envvar = ["JOB_NAME", "BUILD_NUMBER", "BUILD_URL"]
IS_JENKINS_JOB = all([key in os.environ for key in jenkins_envvar])
if IS_JENKINS_JOB:
    JOB_NAME = os.environ.get("JOB_NAME")
    BUILD_NUMBER = os.environ.get("BUILD_NUMBER")
    BUILD_URL = os.environ.get("BUILD_URL")

#
# Public global functions
#

def hash_object(filename):
    """
    Returns the sha1 for this file using the
    same method as `git hash-object`
    """
    try:
        from hashlib import sha1 as sha_new
    except ImportError:
        from sha import new as sha_new
    digest = sha_new()
    size = os.path.getsize(filename)
    digest.update("blob %u\0" % size)
    file = open(filename, 'rb')
    length = 1024*1024
    try:
        while True:
            block = file.read(length)
            if not block:
                break
            digest.update(block)
    finally:
        file.close()
    return digest.hexdigest()


def git_config(name, user=False, local=False, value=None):
    dbg = logging.getLogger("scc.config").debug
    try:
        pre_cmd = ["git", "config"]
        if value is None:
            post_cmd = ["--get", name]
        else:
            post_cmd = [name, value]

        if user:
            pre_cmd.append("--global")
        elif local:
            pre_cmd.append("--local")
        p = subprocess.Popen(pre_cmd + post_cmd, \
                stdout=subprocess.PIPE).communicate()[0]
        value = p.split("\n")[0].strip()
        if value:
            dbg("Found %s", name)
            return value
        else:
            return None
    except Exception:
        dbg("Error retrieving %s", name, exc_info=1)
        value = None
    return value


def get_token(local=False):
    """
    Get the Github API token.
    """
    return git_config("github.token", local=local)


def get_token_or_user(local=False):
    """
    Get the Github API token or the Github user if undefined.
    """
    token = get_token()
    if not token:
        token = git_config("github.user", local=local)
    return token


def get_github(login_or_token=None, password=None, **kwargs):
    """
    Create a Github instance. Can be constructed using an OAuth2 token,
    a Github login and password or anonymously.
    """
    return GHManager(login_or_token, password, **kwargs)

#
# Management classes. These allow for proper mocking in tests.
#


class GHManager(object):
    """
    By setting dont_ask to true, it's possible to prevent the call
    to getpass.getpass. This is useful during unit tests.
    """

    def __init__(self, login_or_token=None, password=None, dont_ask=False):
        self.log = logging.getLogger("scc.gh")
        self.dbg = self.log.debug
        self.login_or_token = login_or_token
        self.dont_ask = dont_ask
        try:
            self.authorize(password)
            self.get_login()
        except github.GithubException, ge:
            if self.exc_is_bad_credentials(ge):
                print "Bad credentials"
                sys.exit(ge.status)

    def exc_check_code_and_message(self, ge, status, message):
        if ge.status == status:
            msg = ge.data.get("message", "")
            if message == msg:
                return True
        return False

    def exc_is_bad_credentials(self, ge):
        return self.exc_check_code_and_message(ge, 401, "Bad credentials")

    def exc_is_not_found(self, ge):
        return self.exc_check_code_and_message(ge, 404, "Not Found")

    def authorize(self, password):
        if password is not None:
            self.create_instance(self.login_or_token, password)
        elif self.login_or_token is not None:
            try:
                self.create_instance(self.login_or_token)
                self.get_login() # Trigger
            except github.GithubException:
                if self.dont_ask:
                    raise
                import getpass
                msg = "Enter password for http://github.com/%s:" % self.login_or_token
                password = getpass.getpass(msg)
                if password is not None:
                    self.create_instance(self.login_or_token, password)
        else:
            self.create_instance()

    def get_login(self):
        return self.github.get_user().login

    def get_user(self, *args):
        return self.github.get_user(*args)

    def get_organization(self, *args):
        return self.github.get_organization(*args)

    def create_instance(self, *args, **kwargs):
        """
        Subclasses can override this method in order
        to prevent use of the pygithub2 library.
        """
        self.github = github.Github(*args, **kwargs)

    def __getattr__(self, key):
        self.dbg("github.%s", key)
        return getattr(self.github, key)

    def get_rate_limiting(self):
        requests = self.github.rate_limiting
        self.dbg("Remaining requests: %s out of %s", requests[0], requests[1])

    def gh_repo(self, reponame, username=None):
        """
        Github repository are constructed by passing the user and the
        repository name as in https://github.com/username/reponame.git
        """
        if username is None:
            username = self.get_login()
        return GitHubRepository(self, username, reponame)


    def git_repo(self, path, *args, **kwargs):
        """
        Git repository instances are constructed by passing the path
        of the directory containing the repository.
        """
        return GitRepository(self, os.path.abspath(path), *args, **kwargs)



#
# Utility classes
#

class LoggerWrapper(threading.Thread):
    """
    Read text message from a pipe and redirect them
    to a logger (see python's logger module),
    the object itself is able to supply a file
    descriptor to be used for writing

    fdWrite ==> fdRead ==> pipeReader

    See: http://codereview.stackexchange.com/questions/6567/how-to-redirect-a-subprocesses-output-stdout-and-stderr-to-logging-module
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


class PullRequest(object):
    def __init__(self, repo, pull):
        """Register the Pull Request and its corresponding Issue"""
        self.log = logging.getLogger("scc.pr")
        self.dbg = self.log.debug

        self.pull = pull
        self.issue = repo.get_issue(self.get_number())
        self.dbg("login = %s", self.get_login())
        self.dbg("labels = %s", self.get_labels())
        self.dbg("base = %s", self.get_base())
        self.dbg("len(comments) = %s", len(self.get_comments()))

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

    def get_head_login(self):
        """Return the login of the branch where the changes are implemented."""
        if self.pull.head.user:
            return self.pull.head.user.login
        # Likely an organization. E.g. head.user was missing for
        # https://github.com/openmicroscopy/ome-documentation/pull/204
        return self.pull.head.repo.owner.login

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

class GitHubRepository(object):

    def __init__(self, gh, user_name, repo_name):
        self.log = logging.getLogger("scc.repo")
        self.dbg = self.log.debug
        self.gh = gh
        self.user_name = user_name
        self.repo_name = repo_name
        self.candidate_pulls = []

        try:
            self.repo = gh.get_user(user_name).get_repo(repo_name)
            if self.repo.organization:
                self.org = gh.get_organization(self.repo.organization.login)
            else:
                self.org = None
        except:
            self.log.error("Failed to find %s/%s", user_name, repo_name)
            raise

    def __repr__(self):
        return "Repository: %s/%s" % (self.user_name, self.repo_name)

    def __getattr__(self, key):
        return getattr(self.repo, key)

    def get_owner(self):
        return self.owner.login

    def is_whitelisted(self, user, default="org"):
        if default == "org":
            if self.org:
                status = self.org.has_in_public_members(user)
            else:
                status = False
        elif default == "mine":
            status = user.login == self.gh.get_login()
        elif default == "all":
            status = True
        elif default == "none":
            status = False
        else:
            raise Exception("Unknown whitelisting mode: %s", default)

        return status

    def push(self, name):
        # TODO: We need to make it possible
        # to create a GitRepository object
        # with only a remote connection for
        # just those actions which don't
        # require a clone.
        repo = "git@github.com:%s/%s.git" % (self.get_owner(), self.repo_name)
        p = subprocess.Popen(["git", "push", repo, name])
        rc = p.wait()
        if rc != 0:
            raise Exception("'git push %s %s' failed", repo, name)

    def open_pr(self, title, description, base, head):
        return self.repo.create_pull(title, description, base, head)

    def merge_info(self):
        """List the candidate Pull Request to be merged"""

        msg = "Candidate PRs:\n"
        for pullrequest in self.candidate_pulls:
            msg += str(pullrequest) + "\n"

        return msg

    def intersect(self, a, b):
        if not a or not b:
            return None

        intersection = set(a) & set(b)
        if any(intersection):
            return list(intersection)
        else:
            return None

    def run_filter(self, filters, labels, user, pr, action="Include"):

        labels = self.intersect(filters["label"], labels)
        if labels:
            self.dbg("# ... %s labels: %s", action, " ".join(labels))
            return True

        user = self.intersect(filters["user"], [user])
        if user:
            self.dbg("# ... %s user: %s", action, " ".join(user))
            return True

        pr = self.intersect(filters["pr"], [pr])
        if pr:
            self.dbg("# ... %s PR: %s", action, " ".join(pr))
            return True

        return False

    def find_candidates(self, filters):
        """Find candidate Pull Requests for merging."""
        self.dbg("## PRs found:")

        # Loop over pull requests opened aainst base
        pulls = [pull for pull in self.get_pulls() if (pull.base.ref == filters["base"])]

        for pull in pulls:
            pullrequest = PullRequest(self, pull)
            labels = [x.lower() for x in pullrequest.get_labels()]

            user = pullrequest.get_user().login
            number = str(pullrequest.get_number())
            if not self.is_whitelisted(pullrequest.get_user(), filters["default"]):
                # Allow filter PR inclusion using include filter
                if not self.run_filter(filters["include"], labels, user, number, action="Include"):
                    continue

            # Exclude PRs specified by filters
            if self.run_filter(filters["exclude"], labels, user, number,  action="Exclude"):
                continue

            self.dbg(pullrequest)
            self.candidate_pulls.append(pullrequest)

        self.candidate_pulls.sort(lambda a, b: cmp(a.get_number(), b.get_number()))

class GitRepository(object):

    def __init__(self, gh, path, reset=False):
        """
        Register the git repository path, return the current status and
        register the Github origin remote.
        """

        self.log = logging.getLogger("scc.git")
        self.dbg = self.log.debug
        self.info = self.log.info
        self.debugWrap = LoggerWrapper(self.log, logging.DEBUG)
        self.infoWrap = LoggerWrapper(self.log, logging.INFO)

        self.gh = gh
        self.path =  os.path.abspath(path)

        if reset:
            self.reset()
        self.get_status()


        # Register the origin remote
        [user_name, repo_name] = self.get_remote_info("origin")
        self.origin = gh.gh_repo(repo_name, user_name)
        self.submodules = []

    def register_submodules(self, reset=False):
        if len(self.submodules) == 0:
            submodule_paths = self.call("git", "submodule", "--quiet", "foreach",\
                    "echo $path", stdout=subprocess.PIPE).communicate()[0]

            lines = submodule_paths.split("\n")
            while "".join(lines):
                directory = lines.pop(0).strip()
                try:
                    submodule_repo = self.gh.git_repo(directory, reset)
                    self.submodules.append(submodule_repo)
                    submodule_repo.register_submodules(reset)
                finally:
                    self.cd(self.path)

    def cd(self, directory):
        if not os.path.abspath(os.getcwd()) == os.path.abspath(directory):
            self.dbg("cd %s", directory)
            os.chdir(directory)

    def communicate(self, *command):
        self.dbg("Calling '%s' for stdout/err" % " ".join(command))
        p = subprocess.Popen(command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        o, e = p.communicate()
        if p.returncode:
            msg = """Failed to run '%s'
    rc:     %s
    stdout: %s
    stderr: %s""" % (" ".join(command), p.returncode, o, e)
            raise Exception(msg)
        return o, e

    def call_info(self, *command, **kwargs):
        """
        Call wrap_call with a info LoggerWrapper
        """
        return self.wrap_call(self.infoWrap, *command, **kwargs)

    def call(self, *command, **kwargs):
        """
        Call wrap_call with a debug LoggerWrapper
        """
        return self.wrap_call(self.debugWrap, *command, **kwargs)

    def wrap_call(self, logWrap, *command, **kwargs):
        for x in ("stdout", "stderr"):
            if x not in kwargs:
                kwargs[x] = logWrap
        self.dbg("Calling '%s'" % " ".join(command))
        p = subprocess.Popen(command, **kwargs)
        rc = p.wait()
        if rc:
            raise Exception("rc=%s" % rc)
        return p

    def write_directories(self):
        """Write directories in candidate PRs comments to a txt file"""

        self.cd(self.path)
        directories_log = None

        for pr in self.origin.candidate_pulls:
            directories = pr.test_directories()
            if directories:
                if directories_log == None:
                    directories_log = open('directories.txt', 'w')
                for directory in directories:
                    directories_log.write(directory)
                    directories_log.write("\n")
        # Cleanup
        if directories_log:
            directories_log.close()

    #
    # General git commands
    #

    def get_current_head(self):
        """Return the symbolic name for the current branch"""
        self.cd(self.path)
        self.dbg("Get current head")
        o, e = self.communicate("git", "symbolic-ref", "HEAD")
        o = o.strip()
        refsheads = "refs/heads/"
        if o.startswith(refsheads):
            o = o[len(refsheads):]
        return o

    def get_current_sha1(self):
        """Return the sha1 for the current commit"""
        self.cd(self.path)
        self.dbg("Get current sha1")
        o, e = self.communicate("git", "rev-parse", "HEAD")
        return o.strip()

    def get_status(self):
        """Return the status of the git repository including its submodules"""
        self.cd(self.path)
        self.dbg("Check current status")
        self.call("git", "log", "--oneline", "-n", "1", "HEAD")
        self.call("git", "submodule", "status")

    def add(self, file):
        """
        Add a file to the repository. The path should
        be relative to the top of the repository.
        """
        self.cd(self.path)
        self.dbg("Adding %s...", file)
        self.call("git", "add", file)

    def commit(self, msg):
        self.cd(self.path)
        self.dbg("Committing %s...", msg)
        self.call("git", "commit", "-m", msg)

    def new_branch(self, name, head="HEAD"):
        self.cd(self.path)
        self.dbg("New branch %s from %s...", name, head)
        self.call("git", "checkout", "-b", name, head)

    def checkout_branch(self, name):
        self.cd(self.path)
        self.dbg("Checkout branch %s...", name)
        self.call("git", "checkout", name)

    def add_remote(self, name, url=None):
        self.cd(self.path)
        if url is None:
            repo_name = self.origin.repo.name
            url = "git@github.com:%s/%s.git" % (name, repo_name)
        self.dbg("Adding remote %s for %s...", name, url)
        self.call("git", "remote", "add", name, url)

    def push_branch(self, name, remote="origin", force=False):
        self.cd(self.path)
        self.dbg("Pushing branch %s to %s..." % (name, remote))
        if force:
            self.call("git", "push", "-f", remote, name)
        else:
            self.call("git", "push", remote, name)

    def delete_local_branch(self, name, force=False):
        self.cd(self.path)
        self.dbg("Deleting branch %s locally..." % name)
        d_switch = force and "-D" or "-d"
        self.call("git", "branch", d_switch, name)

    def delete_branch(self, name, remote="origin"):
        self.cd(self.path)
        self.dbg("Deleting branch %s from %s..." % (name, remote))
        self.call("git", "push", remote, ":%s" % name)

    def reset(self):
        """Reset the git repository to its HEAD"""
        self.cd(self.path)
        self.dbg("Resetting...")
        self.call("git", "reset", "--hard", "HEAD")

    def fast_forward(self, base, remote = "origin"):
        """Execute merge --ff-only against the current base"""
        self.dbg("## Merging base to ensure closed PRs are included.")
        p = subprocess.Popen(["git", "merge", "--ff-only", "%s/%s" % (remote, base)], stdout = subprocess.PIPE).communicate()[0]
        self.dbg(p.rstrip("/n"))
        return  p.rstrip("/n").split("\n")[0]

    def rebase(self, newbase, upstream, sha1):
        self.call_info("git", "rebase", "--onto", \
                "%s" % newbase, "%s" % upstream, "%s" % sha1)

    def get_rev_list(self, commit):
        revlist_cmd = lambda x: ["git","rev-list","--first-parent","%s" % x]
        p = subprocess.Popen(revlist_cmd(commit), stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        self.dbg("Calling '%s'" % " ".join(revlist_cmd(commit)))
        (revlist, stderr) = p.communicate('')

        if stderr or p.returncode:
            msg = "Error output was:\n%s" % stderr
            if revlist.strip():
                msg += "Output was:\n%s" % revlist
            raise Exception(msg)

        return revlist.splitlines()

    #
    # Higher level git commands
    #

    def get_remote_info(self, remote_name):
        """
        Return user and repository name of the specified remote.

        Origin remote must be on Github, i.e. of type
        *github/user/repository.git
        """
        self.cd(self.path)
        try:
            originurl = self.call("git", "config", "--get", \
                "remote." + remote_name + ".url", stdout = subprocess.PIPE, \
                stderr = subprocess.PIPE).communicate()[0]
        except:
            self.dbg("git config --get remote failure", exc_info=1)
            remotes = self.call("git", "remote", stdout = subprocess.PIPE,
                stderr = subprocess.PIPE).communicate()[0]
            raise Stop(1, "Failed to find remote: %s.\nAvailable remotes: %s can be passed with the --remote argument." % (remote_name, ", ".join(remotes.split("\n")[:-1])))

        # Read user from origin URL
        dirname = os.path.dirname(originurl)
        assert "github" in dirname, 'Origin URL %s is not on GitHub' % dirname
        user = os.path.basename(dirname)
        if ":" in dirname:
            user = user.split(":")[-1]

        # Read repository from origin URL
        basename = os.path.basename(originurl)
        if ".git" in basename:
            repo = basename.rsplit(".git")[0]
        else:
            repo = basename.rsplit()[0]
        return [user , repo]

    def merge(self, comment=False, commit_id = "merge"):
        """Merge candidate pull requests."""
        self.dbg("## Unique users: %s", self.unique_logins())
        for key, url in self.remotes().items():
            self.call("git", "remote", "add", key, url)
            self.call("git", "fetch", key)

        conflicting_pulls = []
        merged_pulls = []

        for pullrequest in self.origin.candidate_pulls:
            premerge_sha, e = self.call("git", "rev-parse", "HEAD", stdout = subprocess.PIPE).communicate()
            premerge_sha = premerge_sha.rstrip("\n")

            try:
                self.call("git", "merge", "--no-ff", "-m", \
                        "%s: PR %s (%s)" % (commit_id, pullrequest.get_number(), pullrequest.get_title()), pullrequest.get_sha())
                merged_pulls.append(pullrequest)
            except:
                self.call("git", "reset", "--hard", "%s" % premerge_sha)
                conflicting_pulls.append(pullrequest)

                msg = "Conflicting PR."
                job_dict = ["JOB_NAME", "BUILD_NUMBER", "BUILD_URL"]
                if IS_JENKINS_JOB:
                    job_values = [os.environ.get(key) for key in job_dict]
                    msg += " Removed from build [%s#%s](%s). See the [console output](%s) for more details." % \
                        (JOB_NAME, BUILD_NUMBER, BUILD_URL, BUILD_URL + "/consoleText")
                self.dbg(msg)

                if comment and get_token():
                    self.dbg("Adding comment to issue #%g." % pullrequest.get_number())
                    pullrequest.issue.create_comment(msg)

        merge_msg = ""
        if merged_pulls:
            merge_msg += "Merged PRs:\n"
            for merged_pull in merged_pulls:
                merge_msg += str(merged_pull) + "\n"

        if conflicting_pulls:
            merge_msg += "Conflicting PRs (not included):\n"
            for conflicting_pull in conflicting_pulls:
                merge_msg += str(conflicting_pull) + "\n"

        self.call("git", "submodule", "update")
        return merge_msg

    def find_branching_point(self, topic_branch, main_branch):
        # See http://stackoverflow.com/questions/1527234/finding-a-branch-point-with-git
        topic_revlist = self.get_rev_list(topic_branch)
        main_revlist = self.get_rev_list(main_branch)

        # Compare sequences
        s = difflib.SequenceMatcher(None, topic_revlist, main_revlist)
        matching_block = s.get_matching_blocks()
        if matching_block[0].size == 0:
            raise Exception("No matching block found")

        sha1 = main_revlist[matching_block[0].b]
        self.info("Branching SHA1: %s" % sha1[0:6])
        return sha1

    def rmerge(self, filters, info=False, comment=False, commit_id = "merge"):
        """Recursively merge PRs for each submodule."""

        merge_msg = ""
        merge_msg += str(self.origin) + "\n"
        self.origin.find_candidates(filters)
        if info:
            merge_msg += self.origin.merge_info()
        else:
            self.cd(self.path)
            self.write_directories()
            merge_msg += self.fast_forward(filters["base"])  + "\n"
            merge_msg += self.merge(comment, commit_id = commit_id)

        for filt in ["include", "exclude"]:
            filters[filt]["pr"] = None

        for submodule_repo in self.submodules:
            try:
                submodule_msg = submodule_repo.rmerge(filters, info, comment, commit_id = commit_id)
                merge_msg += "\n" + submodule_msg
            finally:
                self.cd(self.path)

        if IS_JENKINS_JOB:
            merge_msg_footer = "\nGenerated by %s#%s (%s)" % (JOB_NAME, BUILD_NUMBER, BUILD_URL)
        else:
            merge_msg_footer = ""

        if not info:
            self.call("git", "commit", "--allow-empty", "-a", "-n", "-m", \
                "%s\n\n%s" % (commit_id, merge_msg + merge_msg_footer))
        return merge_msg

    def unique_logins(self):
        """Return a set of unique logins."""
        unique_logins = set()
        for pull in self.origin.candidate_pulls:
            unique_logins.add(pull.get_head_login())
        return unique_logins

    def remotes(self):
        """Return remotes associated to unique login."""
        remotes = {}
        for user in self.unique_logins():
            key = "merge_%s" % user
            if self.origin.private:
                url = "git@github.com:%s/%s.git"  % (user, self.origin.name)
            else:
                url = "git://github.com/%s/%s.git" % (user, self.origin.name)
            remotes[key] = url
        return remotes

    def rcleanup(self):
        """Recursively remove remote branches created for merging."""

        self.cleanup()
        for submodule_repo in self.submodules:
            try:
                submodule_repo.rcleanup()
            except:
                self.dbg("Failed to clean repository %s" % self.path)
            self.cd(self.path)

    def cleanup(self):
        """Remove remote branches created for merging."""
        self.cd(self.path)
        for key in self.remotes().keys():
            try:
                self.call("git", "remote", "rm", key)
            except Exception:
                self.log.error("Failed to remove", key, exc_info=1)

    def rpush(self, branch_name, remote, force=False):
        """Recursively push a branch to remotes across submodules"""

        full_remote = remote % (self.origin.repo_name)
        self.push_branch(branch_name, remote=full_remote, force=force)
        self.dbg("Pushed %s to %s" % (branch_name, full_remote))

        for submodule_repo in self.submodules:
            try:
                submodule_repo.rpush(branch_name, remote, force=force)
            finally:
                self.cd(self.path)

#
# What follows are the commands which are available from the command-line.
# Alphabetically listed please.
#

class Stop(Exception):
    """
    Exception which specifies that the current execution has finished.
    This is useful when an appropriate user error message has been
    printed and it's not necessary to print a full stacktrace.
    """

    def __init__(self, rc, *args, **kwargs):
        self.rc = rc
        super(Stop, self).__init__(*args, **kwargs)

class Command(object):
    """
    Base type. At the moment just a marker class which
    signifies that a subclass is a CLI command. Subclasses
    should register themselves with the parser during
    instantiation. Note: Command.__call__ implementations
    are responsible for calling cleanup()
    """

    NAME = "abstract"

    def __init__(self, sub_parsers):
        self.log = logging.getLogger("scc.%s"%self.NAME)
        self.log_level = SCC_DEBUG_LEVEL

        help = self.__doc__.lstrip()
        self.parser = sub_parsers.add_parser(self.NAME,
            help=help, description=help)
        self.parser.set_defaults(func=self.__call__)

        self.parser.add_argument("-v", "--verbose", action="count", default=0,
            help="Increase the logging level by multiples of 10")
        self.parser.add_argument("-q", "--quiet", action="count", default=0,
            help="Decrease the logging level by multiples of 10")

    def add_token_args(self):
        self.parser.add_argument("--token",
            help="Token to use rather than from config files")
        self.parser.add_argument("--no-ask", action='store_true',
            help="Don't ask for a password if token usage fails")

    def __call__(self, args):
        self.configure_logging(args)
        self.cwd = os.path.abspath(os.getcwd())

    def login(self, args):
        if args.token:
            token = args.token
        else:
            token = get_token_or_user()
        if token is None and not args.no_ask:
            print "# github.token and github.user not found."
            print "# See `%s token` for simpifying use." % sys.argv[0]
            token = raw_input("Username or token: ").strip()
        self.gh = get_github(token, dont_ask=args.no_ask)

    def configure_logging(self, args):
        self.log_level += args.quiet * 10
        self.log_level -= args.verbose * 10

        log_format = """%(asctime)s [%(name)12.12s] %(levelname)-5.5s %(message)s"""
        logging.basicConfig(level=self.log_level, format=log_format)
        logging.getLogger('github').setLevel(logging.INFO)

        self.log = logging.getLogger('scc.%s'%self.NAME)
        self.dbg = self.log.debug


class CheckMilestone(Command):
    """Check all merged PRs for a set milestone

Find all GitHub-merged PRs between head and tag, i.e.
git log --first-parent TAG...HEAD

Usage:
    check-milestone 0.2.0 0.2.1 --set=0.2.1
    """

    NAME = "check-milestone"

    def __init__(self, sub_parsers):
        super(CheckMilestone, self).__init__(sub_parsers)
        self.add_token_args()
        self.parser.add_argument('tag', help="Start tag for searching")
        self.parser.add_argument('head', help="Branch to use check")
        self.parser.add_argument('--set', help="Milestone to use if unset",
                                 dest="milestone_name")

        # 5c5a373 Merge pull request #31 from joshmoore/sha-blob
        self.pattern = re.compile("^\w+\sMerge\spull\srequest\s.(\d+)\s.*$")

    def __call__(self, args):
        super(CheckMilestone, self).__call__(args)
        self.login(args)
        main_repo = self.gh.git_repo(self.cwd, False)
        try:

            if args.milestone_name:
                milestone = None
                milestones = main_repo.origin.get_milestones()
                for m in milestones:
                    if m.title == args.milestone_name:
                        milestone = m
                        break


                if not milestone:
                    raise Stop(3, "Unknown milestone: %s" % args.milestone_name)

            p = main_repo.call("git", "log", "--oneline", "--first-parent",
                               "%s...%s" % (args.tag, args.head),
                               stdout=subprocess.PIPE)
            o, e = p.communicate()
            for line in o.split("\n"):
                if line:
                    m = self.pattern.match(line)
                    if not m:
                        self.log.info("Unknown merge: %s", line)
                        continue
                    pr = int(m.group(1))
                    pr = main_repo.origin.get_issue(pr)
                    if pr.milestone:
                        self.log.debug("PR %s in milestone %s", pr.number, pr.milestone.title)
                    else:
                        if args.milestone_name:
                            try:
                                pr.edit(milestone=milestone)
                                print "Set milestone for PR %s to %s" % (pr.number, milestone.title)
                            except github.GithubException, ge:
                                if self.gh.exc_is_not_found(ge):
                                    raise Stop(10, "Can't edit milestone")
                                raise
                        else:
                            print "No milestone for PR %s ('%s')" % (pr.number, line)
        finally:
            main_repo.cleanup()


class AlreadyMerged(Command):
    """Detect branches local & remote which are already merged"""

    NAME = "already-merged"

    def __init__(self, sub_parsers):
        super(AlreadyMerged, self).__init__(sub_parsers)
        self.add_token_args()

        self.parser.add_argument("target",
                help="Head to check against. E.g. master or origin/master")
        self.parser.add_argument("ref", nargs="*",
                default=["refs/heads", "refs/remotes"],
                help="List of ref patterns to be checked. E.g. refs/remotes/origin")

    def __call__(self, args):
        super(AlreadyMerged, self).__call__(args)
        self.login(args)

        main_repo = self.gh.git_repo(self.cwd, False)
        try:
            self.already_merged(args, main_repo)
        finally:
            main_repo.cleanup()

    def already_merged(self, args, main_repo):
        fmt = "%(committerdate:iso8601) %(refname:short)   --- %(subject)"
        cmd = ["git", "for-each-ref", "--sort=committerdate"]
        cmd.append("--format=%s" % fmt)
        cmd += args.ref
        proc = main_repo.call(*cmd, stdout=subprocess.PIPE)
        out, err = proc.communicate()
        for line in out.split("\n"):
            if line:
                self.go(main_repo, line.rstrip(), args.target)

    def go(self, main_repo, input, target):
        parts = input.split(" ")
        branch = parts[3]
        tip, err = main_repo.call("git", "rev-parse", branch,
            stdout=subprocess.PIPE).communicate()
        mrg, err = main_repo.call("git", "merge-base", branch, target,
            stdout=subprocess.PIPE).communicate()
        if tip == mrg:
            print input


class CleanSandbox(Command):
    """Cleans snoopys-sandbox repo after testing

Removes all branches from your fork of snoopys-sandbox
    """

    NAME = "clean-sandbox"

    def __init__(self, sub_parsers):
        super(CleanSandbox, self).__init__(sub_parsers)
        self.add_token_args()

        group = self.parser.add_mutually_exclusive_group(required=True)
        group.add_argument('-f', '--force', action="store_true",
                help="Perform a clean of all non-master branches")
        group.add_argument('-n', '--dry-run', action="store_true",
                help="Perform a dry-run without removing any branches")

        self.parser.add_argument("--skip", action="append", default=["master"])

    def __call__(self, args):
        super(CleanSandbox, self).__call__(args)
        self.login(args)

        gh_repo = self.gh.gh_repo("snoopys-sandbox")
        branches = gh_repo.repo.get_branches()
        for b in branches:
            if b.name in args.skip:
                if args.dry_run:
                    print "Would not delete", b.name
            elif args.dry_run:
                print "Would delete", b.name
            elif args.force:
                gh_repo.push(":%s" % b.name)
            else:
                raise Exception("Not possible!")


class Label(Command):
    """
    Query/add/remove labels from Github issues.
    """

    NAME = "label"

    def __init__(self, sub_parsers):
        super(Label, self).__init__(sub_parsers)
        self.add_token_args()

        self.parser.add_argument('issue', nargs="*", type=int,
                help="The number of the issue to check")

        # Actions
        group = self.parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--add', action='append',
            help='List labels attached to the issue')
        group.add_argument('--available', action='store_true',
            help='List all available labels for this repo')
        group.add_argument('--list', action='store_true',
            help='List labels attached to the issue')

    def __call__(self, args):
        super(Label, self).__call__(args)
        self.login(args)

        main_repo = self.gh.git_repo(self.cwd, False)
        try:
            self.labels(args, main_repo)
        finally:
            main_repo.cleanup()

    def labels(self, args, main_repo):
        if args.add:
            self.add(args, main_repo)
        elif args.available:
            self.available(args, main_repo)
        elif args.list:
            self.list(args, main_repo)

    def get_issue(self, args, main_repo, issue):
        # Copied from Rebase command.
        # TODO: this could be refactored
        if args.issue and len(args.issue) > 1:
            if print_issue_num:
                print "# %s" % issue
        return main_repo.origin.get_issue(issue)

    def add(self, args, main_repo):
        for label in args.add:

            try:
                label = main_repo.origin.get_label(label)
            except github.GithubException, ge:
                if self.gh.exc_is_not_found(ge):
                    try:
                        main_repo.origin.create_label(label, "663399")
                        label = main_repo.origin.get_label(label)
                    except github.GithubException, ge:
                        if self.gh.exc_is_not_found(ge):
                            raise Stop(10, "Can't create label: %s" % label)
                        raise
                else:
                    raise

            for issue in args.issue:
                issue = self.get_issue(args, main_repo, issue)
                try:
                    issue.add_to_labels(label)
                except github.GithubException, ge:
                    if self.gh.exc_is_not_found(ge):
                        raise Stop(10, "Can't add label: %s" % label.name)
                    raise

    def available(self, args, main_repo):
        if args.issue:
            print >>sys.stderr, "# Ignoring issues: %s" % args.issue
        for label in main_repo.origin.get_labels():
            print label.name

    def list(self, args, main_repo):
        for issue in args.issue:
            issue = self.get_issue(args, main_repo, issue)
            labels = issue.get_labels()
            for label in labels:
                print label.name


class Merge(Command):
    """
    Merge Pull Requests opened against a specific base branch.

    Automatically merge all pull requests with any of the given labels.
    It assumes that you have checked out the target branch locally and
    have updated any submodules. The SHA1s from the PRs will be merged
    into the current branch. AFTER the PRs are merged, any open PRs for
    each submodule with the same tags will also be merged into the
    CURRENT submodule sha1. A final commit will then update the submodules.
    """

    NAME = "merge"

    def __init__(self, sub_parsers):
        super(Merge, self).__init__(sub_parsers)
        self.add_token_args()

        filter_desc = " Filter keys can be specified using label:my_label, \
            pr:24 or  user:username. If no key is specified, the filter is \
            considered as a label filter."

        self.parser.add_argument('--reset', action='store_true',
            help='Reset the current branch to its HEAD')
        self.parser.add_argument('--info', action='store_true',
            help='Display merge candidates but do not merge them')
        self.parser.add_argument('--comment', action='store_true',
            help='Add comment to conflicting PR')
        self.parser.add_argument('base', type=str)
        self.parser.add_argument('--default', '-D', type=str,
            choices=["none", "mine", "org" , "all"], default="org",
            help='Mode specifying the default PRs to include. None includes no PR. All includes all open PRs. Mine only includes the PRs opened by the authenticated user. If the repository belongs to an organization, org includes any PR opened by a public member of the organization. Default: org.')
        self.parser.add_argument('--include', '-I', type=str, action='append',
            help='Filters to include PRs in the merge.' + filter_desc)
        self.parser.add_argument('--exclude', '-E', type=str, action='append',
            help='Filters to exclude PRs from the merge.' + filter_desc)
        self.parser.add_argument('--push', type=str,
            help='Name of the branch to use to recursively push the merged branch to Github')

    def __call__(self, args):
        super(Merge, self).__call__(args)
        self.login(args)

        main_repo = self.gh.git_repo(self.cwd, args.reset)
        main_repo.register_submodules(args.reset)

        try:
            self.merge(args, main_repo)
        finally:
            if not args.info:
                self.log.debug("Cleaning remote branches created for merging")
                main_repo.rcleanup()

        if args.push is not None:
            branch_name = "HEAD:refs/heads/%s" % (args.push)

            user = self.gh.get_login()
            remote = "git@github.com:%s/" % (user) + "%s.git"

            main_repo.rpush(branch_name, remote, force=True)
            gh_branch = "https://github.com/%s/%s/tree/%s" % (user, main_repo.origin.repo_name, args.push)
            self.log.info("Merged branch pushed to %s" % gh_branch)

    def merge(self, args, main_repo):

        self._parse_filters(args)

        # Create commit message using command arguments
        commit_args = ["merge"]
        commit_args.append(args.base)
        commit_args.append("-D")
        commit_args.append(args.default)
        if args.include:
            for filt in args.include:
                commit_args.append("-I")
                commit_args.append(filt)
        if args.exclude:
            for filt in args.exclude:
                commit_args.append("-E")
                commit_args.append(filt)

        merge_msg = main_repo.rmerge(self.filters, args.info, args.comment,
            commit_id = " ".join(commit_args))

        for line in merge_msg.split("\n"):
            self.log.info(line)

    def _parse_filters(self, args):
        """ Read filters from arguments and fill filters dictionary"""

        self.filters = {}
        self.filters["base"] = args.base
        self.filters["default"] = args.default
        if args.default == "org":
            default_user = "any public member of the organization"
        elif args.default == "mine":
            default_user = "%s" % self.gh.get_login()
        elif args.default == "all":
            default_user = "any user"
        elif args.default == "none":
            default_user = "no user"
        else:
            raise Exception("Unknown default mode: %s", args.default)

        if args.info:
            action = "Finding"
        else:
            action = "Merging"
        self.log.info("%s PR based on %s opened by %s", action, args.base, default_user)

        descr = {"label": " labelled as", "pr": "", "user": " opened by"}
        keys = descr.keys()
        default_key = "label"

        for ftype in ["include" , "exclude"]:
            self.filters[ftype] = dict.fromkeys(keys)

            if not getattr(args, ftype):
                continue

            for filt in getattr(args, ftype):
                found = False
                for key in keys:
                    if filt.find(key + ":") == 0:
                        value = filt.replace(key + ":",'',1)
                        if self.filters[ftype][key]:
                            self.filters[ftype][key].append(value)
                        else:
                            self.filters[ftype][key] = [value]
                        found = True
                        continue

                if not found:
                    if self.filters[ftype][key]:
                        self.filters[ftype][default_key].append(filt)
                    else:
                        self.filters[ftype][default_key] = [filt]

            action = ftype[0].upper() + ftype[1:-1] + "ing"
            for key in keys:
                if self.filters[ftype][key]:
                    self.log.info("%s PR%s: %s", action, descr[key], " ".join(self.filters[ftype][key]))

class Rebase(Command):
    """Rebase Pull Requests opened against a specific base branch.

        The workflow currently is:

        1) Find the branch point for the original PR.
        2) Rebase all commits from the branch point to the tip.
        3) Create a branch named "rebase/develop/ORIG_NAME".
        4) If push is set, also push to GH, and switch branches.
        5) If pr is set, push to GH, open a PR, and switch branches.
        6) If keep is set, omit the deleting of the newbranch.

        If --remote is not set, 'origin' will be used.
    """

    NAME = "rebase"

    def __init__(self, sub_parsers):
        super(Rebase, self).__init__(sub_parsers)
        self.add_token_args()

        for name, help in (
                ('pr', 'Skip creating a PR.'),
                ('push', 'Skip pushing github'),
                ('delete', 'Skip deleting local branch')):

            self.parser.add_argument('--no-%s'%name, action='store_false',
                dest=name, default=True, help=help)

        self.parser.add_argument('--remote', default="origin",
            help='Name of the remote to use as the origin')

        self.parser.add_argument('PR', type=int, help="The number of the pull request to rebase")
        self.parser.add_argument('newbase', type=str, help="The branch of origin onto which the PR should be rebased")

    def __call__(self, args):
        super(Rebase, self).__call__(args)
        self.login(args)

        main_repo = self.gh.git_repo(self.cwd, False)
        try:
            self.rebase(args, main_repo)
        finally:
            main_repo.cleanup()

    def rebase(self, args, main_repo):

        # Local information
        [origin_name, origin_repo] = main_repo.get_remote_info(args.remote)
        # If we are pushing the branch somewhere, we likely will
        # be deleting the new one, and so should remember what
        # commit we are on now in order to go back to it.
        try:
            old_branch = main_repo.get_current_head()
        except:
            old_branch = main_repo.get_current_sha1()

        # Remote information
        pr = main_repo.origin.get_pull(args.PR)
        self.log.info("PR %g: %s opened by %s against %s", \
            args.PR, pr.title, pr.head.user.name, pr.base.ref)
        pr_head = pr.head.sha
        self.log.info("Head: %s", pr_head[0:6])
        self.log.info("Merged: %s", pr.is_merged())

        branching_sha1 = main_repo.find_branching_point(pr_head,
                "%s/%s" % (args.remote, pr.base.ref))
        main_repo.rebase("%s/%s" % (args.remote, args.newbase),
                branching_sha1[0:6], pr_head)

        new_branch = "rebased/%s/%s" % (args.newbase, pr.head.ref)
        main_repo.new_branch(new_branch)
        print >> sys.stderr, "# Created local branch %s" % new_branch

        if args.push or args.pr:
            try:
                user = self.gh.get_login()
                remote = "git@github.com:%s/%s.git" % (user, origin_repo)

                main_repo.push_branch(new_branch, remote=remote)
                print >> sys.stderr, "# Pushed %s to %s" % (new_branch, remote)

                if args.pr:
                    template_args = {"id":pr.number, "base":args.newbase,
                            "title": pr.title, "body": pr.body}
                    title = "%(title)s (rebased onto %(base)s)" % template_args
                    body= """

This is the same as gh-%(id)s but rebased onto %(base)s.

----

%(body)s

                    """ % template_args

                    gh_repo = self.gh.gh_repo(origin_repo, origin_name)
                    pr = gh_repo.open_pr(title, body,
                            base=args.newbase, head="%s:%s" % (user, new_branch))
                    print pr.html_url
                    # Reload in order to prevent mergeable being null.
                    time.sleep(0.5)
                    pr = main_repo.origin.get_pull(pr.number)
                    if not pr.mergeable:
                        print >> sys.stderr, "#"
                        print >> sys.stderr, "# WARNING: PR is NOT mergeable!"
                        print >> sys.stderr, "#"

            finally:
                main_repo.checkout_branch(old_branch)

            if args.delete:
                main_repo.delete_local_branch(new_branch, force=True)


class Token(Command):
    """Get, set, and create tokens for use by scc"""

    NAME = "token"

    def __init__(self, sub_parsers):
        super(Token, self).__init__(sub_parsers)
        # No token args

        self.parser.add_argument("--local", action="store_true",
            help="Access token only in local repository")
        self.parser.add_argument("--user", action="store_true",
            help="Access token only in user configuration")
        self.parser.add_argument("--all", action="store_true",
            help="""Print all known tokens with key""")
        self.parser.add_argument("--set",
            help="Set token to specified value")
        self.parser.add_argument("--create", action="store_true",
            help="""Create token by authorizing with github.""")

    def __call__(self, args):
        super(Token, self).__call__(args)
        # No login

        if args.all:
            for key in ("github.token", "github.user"):

                for user, local, msg in \
                    ((False, True, "local"), (True, False, "user")):

                    rv = git_config(key, user=user, local=local)
                    if rv is not None:
                        print "[%s] %s=%s" % (msg, key, rv)

        elif (args.set or args.create):
            if args.create:
                user = git_config("github.user")
                if not user:
                    raise Exception("No github.user configured")
                gh = get_github(user)
                user = gh.github.get_user()
                auth = user.create_authorization(["public_repo"], "scc token")
                git_config("github.token", user=args.user,
                    local=args.local, value=auth.token)
            else:
                git_config("github.token", user=args.user,
                    local=args.local, value=args.set)
        else:
            token = git_config("github.token",
                user=args.user, local=args.local)
            if token:
                print token


class Version(Command):
    """Find which version of scc is being used"""

    NAME = "version"

    def __init__(self, sub_parsers):
        super(Version, self).__init__(sub_parsers)
        # No token args

    def __call__(self, args):
        super(Version, self).__call__(args)
        # No login
        self.configure_logging(args)

        self.blob = hash_object(__file__)
        self.dbg("hash_object: %s", self.blob)

        gh = get_github(get_token(), dont_ask=True)
        self.repo = gh.gh_repo("snoopycrimecop", "openmicroscopy")

        found = self.search_heads()
        if not found:
            found = self.search_prs()

        if not found:
            print "unknown"
        else:
            print found

    def sort(self, a, b):
        a = a.split(".")
        b = b.split(".")
        return cmp(b, a)

    def matches(self, head, msg=None):
        if msg is None:
            self.dbg("Checking %s", head)
        else:
            self.dbg("Checking %s (%s)", msg, head)

        tree = self.repo.get_git_tree(head)
        for elt in tree.tree:
            if self.blob == elt.sha:
                self.dbg("Found blob: %s" % elt.path)
                return head

    def search_heads(self):

        heads = [tag.name for tag in self.repo.get_tags()]

        # Remove versions known not to support Version
        for x in ("0.1.0", "0.2.0"):
            heads.remove(x)

        heads.sort(self.sort)
        heads.append("master")

        self.dbg("Searching: %s" % heads)
        for head in heads:
            if self.matches(head):
                return head

    def search_prs(self):
        for pr in self.repo.get_pulls():
            msg = "%s %s" % (pr.number, pr.title)
            if self.matches(pr.head.sha, msg):
                return pr.head.sha

def parsers():

    class HelpFormatter(argparse.RawTextHelpFormatter):
        """
        argparse.HelpFormatter subclass which cleans up our usage, preventing very long
        lines in subcommands.

        Borrowed from omero/cli.py
        Defined inside of parsers() in case argparse is not installed.
        """

        def __init__(self, prog, indent_increment=2, max_help_position=40, width=None):
            argparse.RawTextHelpFormatter.__init__(self, prog, indent_increment, max_help_position, width)
            self._action_max_length = 20

        def _split_lines(self, text, width):
            return [text.splitlines()[0]]

        class _Section(argparse.RawTextHelpFormatter._Section):

            def __init__(self, formatter, parent, heading=None):
                #if heading:
                #    heading = "\n%s\n%s" % ("=" * 40, heading)
                argparse.RawTextHelpFormatter._Section.__init__(self, formatter, parent, heading)

    scc_parser = argparse.ArgumentParser(
        description='Snoopy Crime Cop Script',
        formatter_class=HelpFormatter)
    sub_parsers = scc_parser.add_subparsers(title="Subcommands")

    return scc_parser, sub_parsers

def main(args=None):
    """
    Reusable entry point. Arguments are parsed
    via the argparse-subcommands configured via
    each Command class found in globals().
    """

    if not argparse_loaded or not github_loaded:
        raise Stop(2, "Missing required module")
    if args is None: args = sys.argv[1:]

    scc_parser, sub_parsers = parsers()

    for name, MyCommand in sorted(globals().items()):
        if not isinstance(MyCommand, type): continue
        if not issubclass(MyCommand, Command): continue
        if MyCommand == Command: continue
        MyCommand(sub_parsers)

    ns = scc_parser.parse_args(args)
    ns.func(ns)


if __name__ == "__main__":
    try:
        main()
    except Stop, stop:
        print stop,
        sys.exit(stop.rc)
