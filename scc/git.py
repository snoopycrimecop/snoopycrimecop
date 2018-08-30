#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2012-2017 University of Dundee & Open Microscopy Environment
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


import argparse
import re
import copy
import os
import sys
import uuid
import subprocess
import logging
import threading
import datetime
import difflib
import socket
import yaml
import six
from ssl import SSLError
from yaclifw.framework import Command, Stop

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

# Read Jenkins environment variables
jenkins_envvar = ["JOB_NAME", "BUILD_NUMBER", "BUILD_URL"]
IS_JENKINS_JOB = all([key in os.environ for key in jenkins_envvar])
if IS_JENKINS_JOB:
    JOB_NAME = os.environ.get("JOB_NAME")
    BUILD_NUMBER = os.environ.get("BUILD_NUMBER")
    BUILD_URL = os.environ.get("BUILD_URL")

EMPTY_MSG = 'Empty PR description. Please add a short summary' \
    ' of the PR scope and some testing instructions.'

CONFLICT_COMMENT = '--conflicts'
#
# Public global functions
#

try:
    SCC_RETRIES = int(os.environ.get("SCC_RETRIES"))
except Exception:
    SCC_RETRIES = 3
GH_RETRY_CODES = [405, 502]


def check_github_code(exception):
    if exception.status not in GH_RETRY_CODES:
        raise
    return "Received %s" % exception.data


def check_exception_message(exception):
    if exception.message != "rc=128":
        raise
    return "Received rc=128"


def retry_on_error(retries=SCC_RETRIES):
    """
    Decorator for handling Github server errors

    :keyword retries:
        Number of attempts before giving up (default to 3)
    """

    def decorator(func):
        log = logging.getLogger("scc.gh")

        def wrapper(*args, **kwargs):
            for num in range(retries + 1):
                try:
                    return func(*args, **kwargs)
                except github.GithubException, e:
                    error = check_github_code(e)
                except socket.timeout:
                    error = "Socket timeout"
                except SSLError:
                    error = "SSL error"
                except Exception, e:
                    error = check_exception_message(e)
                if num >= retries:
                    raise
                log.debug("%s, retrying (try %s)", error, num + 1)

        return wrapper
    return decorator


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


def git_version(local=False):
    """
    Get the version of Git.
    """
    p = subprocess.Popen(["git", "--version"], stdout=subprocess.PIPE)
    output = p.communicate()[0].split()
    p.stdout.close()
    return tuple([int(x) for x in output[2].split(".")])


def git_config(name, user=False, local=False, value=None, config_file=None):
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

        if config_file is not None:
            pre_cmd.extend(["-f", config_file])

        p = subprocess.Popen(
            pre_cmd + post_cmd, stdout=subprocess.PIPE)
        value = p.communicate()[0]
        p.stdout.close()
        value = value.split("\n")[0].strip()
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
    Get the GitHub API token.
    """
    if os.getenv('GITHUB_TOKEN'):
        return os.getenv('GITHUB_TOKEN')
    return git_config("github.token", local=local)


def get_token_or_user(local=False):
    """
    Get the GitHub API token or the GitHub user if undefined.
    """
    token = get_token(local=local)
    if not token:
        token = git_config("github.user", local=local)
    return token


def get_github(login_or_token=None, password=None, **kwargs):
    """
    Create a GitHub instance. Can be constructed using an OAuth2 token,
    a GitHub login and password or anonymously.
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

    def __init__(self, login_or_token=None, password=None, dont_ask=False,
                 user_agent='PyGithub'):

        self.log = logging.getLogger("scc.gh")
        self.dbg = self.log.debug
        self.login_or_token = login_or_token
        self.dont_ask = dont_ask
        self.user_agent = user_agent
        try:
            self.authorize(password)
            if login_or_token or password:
                self.get_login()
        except github.GithubException, ge:
            raise Stop(ge.status, ge.data.get("message", ""))

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
                self.get_login()  # Trigger
            except github.GithubException:
                if self.dont_ask:
                    raise
                import getpass
                msg = "Enter password for http://github.com/%s:" % \
                    self.login_or_token
                try:
                    password = getpass.getpass(msg)
                    if password is not None:
                        self.create_instance(self.login_or_token, password)
                except KeyboardInterrupt:
                    raise Stop("Interrupted by the user")
        else:
            self.create_instance()

    @retry_on_error(retries=SCC_RETRIES)
    def get_login(self):
        return self.get_user().login

    @retry_on_error(retries=SCC_RETRIES)
    def get_user(self, *args):
        return self.github.get_user(*args)

    @retry_on_error(retries=SCC_RETRIES)
    def get_organization(self, *args):
        return self.github.get_organization(*args)

    @retry_on_error(retries=SCC_RETRIES)
    def get_repo(self, *args):
        return self.github.get_repo(*args)

    @retry_on_error(retries=SCC_RETRIES)
    def get_rate_limits(self):
        """
        Input Data format:
            {
                u'rate': {
                    u'reset': 1401089650,
                    u'limit': 5000,
                    u'remaining': 4992
                },
                u'resources': {
                    u'core': {
                        u'reset': 1401089650,
                        u'limit': 5000,
                        u'remaining': 4992
                    },
                    u'search': {
                        u'reset': 1401086384,
                        u'limit': 30,
                        u'remaining': 30
                    }
                }
            }

        Returns: (core, search) each of which contains the keys:
            'reset', 'limit', 'remaining', 'name', and 'time'
            which is a readable version of 'reset'.
        """
        limits = dict(self.github.get_rate_limit()._rawData)
        core = limits["resources"]["core"]
        search = limits["resources"]["search"]
        for name, data in (("Core", core), ("Search", search)):
            t = data["reset"]
            t = datetime.datetime.fromtimestamp(t)
            t = t.strftime("%H:%m")
            data["time"] = t
            data["name"] = name
        return (core, search)

    @retry_on_error(retries=SCC_RETRIES)
    def create_instance(self, *args, **kwargs):
        """
        Subclasses can override this method in order
        to prevent use of the pygithub2 library.
        """
        self.github = github.Github(*args, user_agent=self.user_agent,
                                    **kwargs)

    @retry_on_error(retries=SCC_RETRIES)
    def __getattr__(self, key):
        self.dbg("github.%s", key)
        return getattr(self.github, key)

    def get_rate_limiting(self):
        requests = self.github.rate_limiting
        self.dbg("Remaining requests: %s out of %s", requests[0], requests[1])
        return requests

    def gh_repo(self, reponame, username=None):
        """
        GitHub repository are constructed by passing the user and the
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


class DefaultList(list):
    def __copy__(self):
        return []


class LoggerWrapper(threading.Thread):
    """
    Read text message from a pipe and redirect them
    to a logger (see python's logger module),
    the object itself is able to supply a file
    descriptor to be used for writing

    fdWrite ==> fdRead ==> pipeReader

    See:
    http://codereview.stackexchange.com/questions/6567/
    how-to-redirect-a-subprocesses-output-stdout-and-stderr-to-logging-module
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

    def close(self):
        """Close the write end of the pipe."""
        os.close(self.fdWrite)


class Milestone(object):
    def __init__(self, milestone):
        """Register the Pull Request and its corresponding Issue"""
        self.log = logging.getLogger("scc.milestone")
        self.dbg = self.log.debug

        self.milestone = milestone

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        s = "  # Milestone %s " % self.title
        if self.due_on:
            s += "due on %s" % self.due_on
        if self.description:
            s += "\n    %s" % self.description
        return s

    @retry_on_error(retries=SCC_RETRIES)
    def __getattr__(self, key):
        return getattr(self.milestone, key)


class PullRequest(object):
    # Indicates the PR is marked as conflicting and there has been no
    # subsequent activity
    PR_IS_CONFLICTING = 1
    # Indicates the PR was previously marked as conflicting but there has
    # since been new activity
    PR_WAS_CONFLICTING = 2

    def __init__(self, pull):
        """Register the Pull Request and its corresponding Issue"""
        self.log = logging.getLogger("scc.pr")
        self.dbg = self.log.debug

        self.pull = pull
        self.issue = None
        self.issue_comments = []

    def __contains__(self, key):
        return key in self.get_labels()

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return "  # PR %s %s '%s'" % (self.get_number(), self.get_login(),
                                      self.get_title())

    @retry_on_error(retries=SCC_RETRIES)
    def __getattr__(self, key):
        return getattr(self.pull, key)

    def parse(self, argument, whitelist=lambda x: True):

        found_body_comments = self.parse_body(argument)
        if found_body_comments:
            return found_body_comments
        else:
            found_comments = self.parse_comments(argument,
                                                 whitelist=whitelist)
            if found_comments:
                return found_comments
            else:
                return []

    def parse_body(self, argument):
        found_comments = []
        if isinstance(argument, list):
            patterns = ["--%s" % a for a in argument]
        else:
            patterns = ["--%s" % argument]

        if self.pull.body is None:
            return found_comments

        lines = self.pull.body.splitlines()
        for line in lines:
            for pattern in patterns:
                if line.startswith(pattern):
                    found_comments.append(line.replace(pattern, ""))
        return found_comments

    def parse_comments(self, argument, whitelist=lambda x: True):
        found_comments = []
        if isinstance(argument, list):
            patterns = ["--%s" % a for a in argument]
        else:
            patterns = ["--%s" % argument]

        for comment in self.get_comments(whitelist=whitelist):
            lines = comment.splitlines()
            for line in lines:
                for pattern in patterns:
                    if line.startswith(pattern):
                        found_comments.append(line.replace(pattern, ""))
        return found_comments

    def get_last_conflicting_comment(self, sccuser):
        comment = None
        for comment in self.get_comments(
                whitelist=lambda c: c.user.login == sccuser, raw=True):
            pass

        if comment:
            lines = comment.body.splitlines()
            for line in lines:
                if line.startswith(CONFLICT_COMMENT):
                    return comment

    def get_conflict_status(self, sccuser):
        """
        A PR is considered marked PR_IS_CONFLICTING if:
        - the last comment contains CONFLICT_COMMENT
        - the last comment was created by the scc user
        - there is no subsequent activity on the PR

        A PR is considered marked PR_WAS_CONFLICTING if:
        - the last comment created by the scc user contains CONFLICT_COMMENT
        - there has been subsequent activity on the PR

        This means the default state of the PR is not conflicting.
        """
        status = 0
        comment = self.get_last_conflicting_comment(sccuser)
        if comment:
            status = self.PR_IS_CONFLICTING
            if comment.updated_at < self.pull.updated_at:
                status = self.PR_WAS_CONFLICTING
        return status

    def resolve_conflict_status(self, sccuser, merged_msg):
        """
        Edit the last conflicting comment to indicate it was resolved
        """
        comment = self.get_last_conflicting_comment(sccuser)
        if comment:
            editted = []
            lines = comment.body.splitlines()
            for line in lines:
                if line.startswith(CONFLICT_COMMENT):
                    line = '~~%s~~ %s' % (line, merged_msg)
                editted.append(line)
            comment.edit('\n'.join(editted))

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
        return self.pull.number

    @retry_on_error(retries=SCC_RETRIES)
    def has_issues(self):
        """Check if the base repository has issues enabled."""
        return self.pull.base.repo.has_issues

    @retry_on_error(retries=SCC_RETRIES)
    def get_issue(self):
        """Return the issue corresponding to the Pull Request."""
        if not self.issue:
            self.issue = self.pull.base.repo.get_issue(self.get_number())
        return self.issue

    def get_head_login(self):
        """Return the login of the branch where the changes are implemented."""
        if self.pull.head.user:
            return self.pull.head.user.login
        # Likely an organization. E.g. head.user was missing for
        # https://github.com/openmicroscopy/ome-documentation/pull/204
        return self.pull.head.repo.owner.login

    def get_head_repo(self):
        """Return the repository of the branch containing the changes."""
        return self.pull.head.repo

    def get_sha(self):
        """Return the SHA1 of the head of the Pull Request."""
        return self.pull.head.sha

    @retry_on_error(retries=SCC_RETRIES)
    def get_last_commit(self, ref="base"):
        """Return the head commit of the Pull Request.
        """
        branch = getattr(self.pull, ref)
        return branch.repo.get_commit(self.get_sha())

    def get_base(self):
        """Return the branch against which the Pull Request is opened."""
        return self.pull.base.ref

    @retry_on_error(retries=SCC_RETRIES)
    def get_labels(self):
        """Return the labels of the Pull Request."""
        if not self.has_issues():
            return []
        else:
            return [x.name for x in self.get_issue().labels]

    @retry_on_error(retries=SCC_RETRIES)
    def get_comments(self, whitelist=lambda x: True, raw=False):
        """Return the labels of the Pull Request."""
        if not self.has_issues():
            return []

        if not self.issue_comments and self.get_issue().comments:
            self.issue_comments = self.get_issue().get_comments()

        if raw:
            return [comment for comment in self.issue_comments
                    if whitelist(comment)]
        return [comment.body for comment in self.issue_comments
                if whitelist(comment)]

    @retry_on_error(retries=SCC_RETRIES)
    def create_issue_comment(self, msg):
        """Add comment to Pull Request"""

        return self.pull.create_issue_comment(msg)

    @retry_on_error(retries=SCC_RETRIES)
    def edit_body(self, body):
        """Edit body of Pull Request"""

        self.pull.edit(body=body)

    @retry_on_error(retries=SCC_RETRIES)
    def create_status(self, status, message, url, ref="base"):
        """Add a status to the head of the Pull Request."""
        self.get_last_commit(ref).create_status(
            status, url or github.GithubObject.NotSet, message,
        )

    @retry_on_error(retries=SCC_RETRIES)
    def get_last_status(self, ref="base"):
        """Return the last status of the Pull Request."""
        try:
            return self.get_last_commit(ref).get_statuses()[0]
        except IndexError:
            return None

    @retry_on_error(retries=SCC_RETRIES)
    def is_merged(self):
        return self.pull.is_merged()


class GitHubRepository(object):

    def __init__(self, gh, user_name, repo_name):
        self.log = logging.getLogger("scc.repo")
        self.dbg = self.log.debug
        self.gh = gh
        self.user_name = user_name
        self.repo_name = repo_name
        self.candidate_pulls = []
        self.candidate_branches = {}

        try:
            self.repo = gh.get_repo(user_name + '/' + repo_name)
            if self.repo.organization:
                self.org = gh.get_organization(self.repo.organization.login)
            else:
                self.org = None
        except Exception:
            self.log.error("Failed to find %s/%s", user_name, repo_name)
            raise

    def __repr__(self):
        return "Repository: %s/%s" % (self.user_name, self.repo_name)

    @retry_on_error(retries=SCC_RETRIES)
    def __getattr__(self, key):
        return getattr(self.repo, key)

    @retry_on_error(retries=SCC_RETRIES)
    def get_issue(self, *args):
        return self.repo.get_issue(*args)

    @retry_on_error(retries=SCC_RETRIES)
    def get_pulls(self, *args):
        return self.repo.get_pulls(*args)

    @retry_on_error(retries=SCC_RETRIES)
    def get_pulls_by_base(self, base):
        return [pull for pull in self.get_pulls()
                if (pull.base.ref == base)]

    @retry_on_error(retries=SCC_RETRIES)
    def get_pull(self, *args):
        pull_request_number, = args
        try:
            return self.repo.get_pull(pull_request_number)
        except Exception:
            self.log.error(
                "Failure to get pull request %s/%s#%d" %
                (self.user_name, self.repo_name, pull_request_number)
            )
            raise

    @retry_on_error(retries=SCC_RETRIES)
    def get_milestone(self, name):

        for state in ("open", "closed"):
            milestones = self.repo.get_milestones(state=state)
            for m in milestones:
                if m.title == name:
                    return m
        return None

    @retry_on_error(retries=SCC_RETRIES)
    def get_milestones(self, *args):
        return self.repo.get_milestones(*args)

    def get_owner(self):
        return self.owner.login

    @retry_on_error(retries=SCC_RETRIES)
    def is_whitelisted(self, user, whitelist):

        if not whitelist:
            return False

        if "#all" in whitelist:
            return True

        if "#org" in whitelist:
            # Whitelist all public members of the organization
            if self.org and self.org.has_in_public_members(user):
                return True
            # Whitelist the owner of a non-organization repository
            elif not self.org and user.login == self.get_owner():
                return True

        for whitelist_user in whitelist:
            if user.login == whitelist_user:
                return True

        return False

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

    @retry_on_error(retries=SCC_RETRIES)
    def open_pr(self, title, description, base, head):
        return self.repo.create_pull(title, description, base, head)

    def merge_info(self):
        """List the candidate Pull Request to be merged"""

        msg = ""
        if self.candidate_pulls:
            msg += "Candidate PRs:\n"
            for pullrequest in self.candidate_pulls:
                msg += str(pullrequest) + "\n"
        if self.candidate_branches:
            msg += "Candidate Branches:\n"
            for remote, repo_branches in self.candidate_branches.iteritems():
                for branch in repo_branches[1]:
                    msg += "  # %s:%s\n" % (remote, branch)

        return msg

    def intersect(self, a, b):
        if not a or not b:
            return None

        intersection = set(a) & set(b)
        if any(intersection):
            return list(intersection)
        else:
            return None

    def run_filter(self, filters, pr_attributes, action="Include"):

        for key, value in pr_attributes.iteritems():
            intersect_set = self.intersect(filters.get(key, None), value)
            if intersect_set:
                self.dbg("  # ... %s %s: %s", action, key,
                         " ".join(intersect_set))
                return True, "%s: %s" % (key, " ".join(intersect_set))

        return False, None

    def find_candidate_pulls(self, filters):
        """Find candidate Pull Requests for merging."""
        self.dbg("## PRs found:")
        msg = ""

        # Fail fast if default is none and no include filter is specified
        if not filters["include"]:
            return msg

        # Combine pr filter with user/repo filters
        repo_name = "%s/%s" % (self.user_name, self.repo_name)
        for ftype in ["include", "exclude"]:
            if filters[ftype].get(repo_name, None):
                filters[ftype].setdefault("pr", []).extend(
                    filters[ftype][repo_name])

        # Loop over pull requests opened against base
        pulls = self.get_pulls_by_base(filters["base"])
        excluded_pulls = {}

        for pull in pulls:
            pullrequest = PullRequest(pull)
            include, exclude_reason = self.filter_pull(pullrequest, filters)

            if not include:
                excluded_pulls[pullrequest] = exclude_reason
            else:
                self.dbg(pullrequest)
                self.candidate_pulls.append(pullrequest)

        if excluded_pulls:
            msg += "Excluded PRs:\n"
            msg += "\n".join(["%s (%s)" % (str(key), str(value))
                              for key, value in excluded_pulls.iteritems()])
            msg += "\n"

        self.candidate_pulls.sort(lambda a, b:
                                  cmp(a.get_number(), b.get_number()))

        return msg

    def filter_pull(self, pullrequest, filters):

        def is_whitelisted_comment(x):
            # Always include the organization filter for whitelisting comments
            user_filters = copy.deepcopy(filters["include"].setdefault(
                "user", []))
            user_filters.append('#org')
            return self.is_whitelisted(x.user, user_filters)

        if pullrequest.parse(filters["exclude"].get("label"),
                             whitelist=is_whitelisted_comment):
            return False, 'exclude comment'

        pullrequest_user = pullrequest.get_user()
        pr_attributes = {}
        pr_attributes["label"] = [x.lower() for x in
                                  pullrequest.get_labels()]
        pr_attributes["user"] = [pullrequest_user.login]
        pr_attributes["pr"] = ['#' + str(pullrequest.get_number())]

        if not self.is_whitelisted(pullrequest_user,
                                   filters["include"].get("user")):
            # Allow filter PR inclusion using include filter
            filter_included, reason = self.run_filter(
                filters["include"], pr_attributes, action="Include")
            if not filter_included and not pullrequest.parse(
                    filters["include"].get("label", None),
                    whitelist=is_whitelisted_comment):
                return False, "user: %s" % pullrequest_user.login

        # Exclude PRs specified by filters
        filter_excluded, reason = self.run_filter(
            filters["exclude"], pr_attributes, action="Exclude")
        if filter_excluded:
            return False, reason

        # Filter PRs by status if the status filter is on
        status_included, reason = self.run_status_filter(pullrequest, filters)
        if not status_included:
            return False, reason

        return True, None

    def run_status_filter(self, pullrequest, filters):

        if "status" not in filters or filters["status"] == "none":
            return True, None

        status = pullrequest.get_last_status("base")
        if status is None:
            # If no status on the base repo, fallback on the head repo
            status = pullrequest.get_last_status("head")

        if status is None:
            state = ""
        else:
            state = status.state

        exclude_1 = (filters["status"] == "success-only") and \
            (state != "success")
        exclude_2 = (filters["status"] == "no-error") and \
            (state in ["error", "failure"])
        if exclude_1 or exclude_2:
            return False, "status: %s" % state

        return True, None

    def find_candidate_branches(self, filters,
                                fork_filter=lambda x: '/' in x):
        """Find candidate branches for merging."""
        self.dbg("## Branches found:")

        # Fail fast if default is none and no include filter is specified
        if not filters["include"]:
            return

        # Check for repositories in include
        forks = [f for f in filters["include"] if fork_filter(f)]

        for fork in forks:
            remote = fork.split('/')[0]
            self.candidate_branches[remote] = (
                self.gh.get_repo(fork), [b for b in filters["include"][fork]
                                         if not re.match('#\d+$', b)])


class GitRepository(object):

    def __init__(self, gh, path, remote="origin", push_branch=None,
                 repository_config=None):
        """
        Register the git repository path, return the current status and
        register the GitHub origin remote.
        """

        self.log = logging.getLogger("scc.git")
        self.dbg = self.log.debug
        self.info = self.log.info
        self.debugWrap = LoggerWrapper(self.log, logging.DEBUG)
        self.infoWrap = LoggerWrapper(self.log, logging.INFO)

        self.gh = gh
        self.path = path
        root_path = self.communicate("git", "rev-parse", "--show-toplevel")
        self.path = os.path.abspath(root_path.strip())

        self.get_status()

        # Register the remote
        [user_name, repo_name] = self.get_remote_info(remote)
        self.remote = remote
        self.push_branch_name = push_branch
        self.repository_config = repository_config
        if self.repository_config is not None and \
           isinstance(self.repository_config, six.string_types):
            self.dbg("Reading repository configuration from %s" %
                     (repository_config))
            self.repository_config = yaml.load(file(self.repository_config,
                                                    'rb').read())
        if self.repository_config is not None:
            self.dbg("Repository configuration:\n%s" %
                     (yaml.dump(self.repository_config)))
        self.submodules = []
        if gh:
            self.origin = gh.gh_repo(repo_name, user_name)

    def register_submodules(self):
        if len(self.submodules) == 0:
            for directory in self.get_submodule_paths():
                repository_config = None
                if self.repository_config is not None and \
                   "submodules" in self.repository_config and \
                   directory in self.repository_config["submodules"]:
                    repository_config = \
                        self.repository_config["submodules"][directory]
                try:
                    submodule_repo = \
                        self.gh.git_repo(directory,
                                         repository_config=repository_config)
                    self.submodules.append(submodule_repo)
                    submodule_repo.register_submodules()
                finally:
                    self.cd(self.path)

    def cd(self, directory):
        if not os.path.abspath(os.getcwd()) == os.path.abspath(directory):
            self.dbg("cd %s", directory)
            os.chdir(directory)

    def communicate(self, *command, **kwargs):
        return_stderr = kwargs.pop('return_stderr', False)
        kwargs['no_wait'] = True

        p = self.wrap_call(subprocess.PIPE, *command, **kwargs)
        o, e = p.communicate()
        p.stdout.close()
        p.stderr.close()
        if p.returncode:
            msg = """Failed to run '%s'
    rc:     %s
    stdout: %s
    stderr: %s""" % (" ".join(command), p.returncode, o, e)
            raise Exception(msg)

        if return_stderr:
            return o, e
        if e:
            self.log.error('stderr (%s): %s', " ".join(command), e)
        return o

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

    def call_no_wait(self, *command, **kwargs):
        """
        Call wrap_call with a debug LoggerWrapper
        """
        kwargs["no_wait"] = True
        return self.wrap_call(self.debugWrap, *command, **kwargs)

    def wrap_call(self, logWrap, *command, **kwargs):
        for x in ("stdout", "stderr"):
            if x not in kwargs:
                kwargs[x] = logWrap

        try:
            no_wait = kwargs.pop("no_wait")
        except Exception:
            no_wait = False

        self.cd(self.path)
        self.dbg("Calling '%s'" % " ".join(command))
        p = subprocess.Popen(command, **kwargs)
        if not no_wait:
            rc = p.wait()
            if rc:
                raise Exception("rc=%s" % rc)
        return p

    def write_directories(self):
        """Write directories in candidate PRs comments to a txt file"""

        self.cd(self.path)
        directories_log = None

        for pr in self.origin.candidate_pulls:
            directories = pr.parse_comments("test")
            if directories:
                if directories_log is None:
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
        o = self.communicate("git", "symbolic-ref", "HEAD")
        o = o.strip()
        refsheads = "refs/heads/"
        if o.startswith(refsheads):
            o = o[len(refsheads):]
        return o

    def get_sha1(self, branch):
        """Return the sha1 for the specified branch"""

        self.dbg("Get sha1 of %s")
        o = self.communicate("git", "rev-parse", branch)
        return o.strip()

    def get_current_sha1(self):
        """Return the sha1 for the current commit"""

        return self.get_sha1('HEAD')

    def get_status(self):
        """Return the status of the git repository including its submodules"""
        self.dbg("Check current status")
        self.call("git", "log", "--oneline", "-n", "1", "HEAD")
        self.call("git", "submodule", "status")

    def add(self, file):
        """
        Add a file to the repository. The path should
        be relative to the top of the repository.
        """
        self.dbg("Adding %s...", file)
        self.call("git", "add", file)

    def commit(self, msg):
        self.dbg("Committing %s...", msg)
        self.call("git", "commit", "-m", msg)

    def tag(self, tag, message=None, force=False, sign=False):
        """Tag the HEAD of the git repository"""
        if message is None:
            message = "Tag with version %s" % tag

        if self.has_local_tag(tag):
            raise Stop(21, "Tag %s already exists in %s." % (tag, self.path))

        if not self.is_valid_tag(tag):
            raise Stop(22, "%s is not a valid tag name." % tag)

        tag_command = ["git", "tag", tag, "-m", message]
        if force:
            tag_command.append("-f")
        if sign:
            tag_command.append("-s")
            self.dbg("Creating signed tag %s...", tag)
        else:
            self.dbg("Creating tag %s...", tag)

        self.call(*tag_command)

    def new_branch(self, name, head="HEAD"):
        self.dbg("New branch %s from %s...", name, head)
        self.call("git", "checkout", "-b", name, head)

    def checkout_branch(self, name):
        self.dbg("Checkout branch %s...", name)
        self.call("git", "checkout", name)

    def add_remote(self, name, url=None):
        if url is None:
            repo_name = self.origin.repo.name
            url = "git@github.com:%s/%s.git" % (name, repo_name)
        self.dbg("Adding remote %s for %s...", name, url)
        self.call("git", "remote", "add", name, url)

    def fetch(self, remote="origin"):
        self.dbg("Fetching remote %s...", remote)
        self.call("git", "fetch", remote)

    @retry_on_error(retries=SCC_RETRIES)
    def push_branch(self, name, remote="origin", force=False):
        self.dbg("Pushing branch %s to %s..." % (name, remote))
        if force:
            self.call("git", "push", "-f", remote, name)
        else:
            self.call("git", "push", remote, name)

    def delete_local_branch(self, name, force=False):
        self.dbg("Deleting branch %s locally..." % name)
        d_switch = force and "-D" or "-d"
        self.call("git", "branch", d_switch, name)

    def delete_branch(self, name, remote="origin"):
        self.dbg("Deleting branch %s from %s..." % (name, remote))
        self.call("git", "push", remote, ":%s" % name)

    def reset(self):
        """Reset the git repository to its HEAD"""
        self.dbg("Resetting...")
        self.call("git", "reset", "--hard", "HEAD")
        self.call("git", "submodule", "update", "--recursive")

    def fast_forward(self, base, remote="origin"):
        """Execute merge --ff-only against the current base"""
        self.dbg("## Merging base to ensure closed PRs are included.")
        args = [
            "git", "log", "--oneline", "--first-parent",
            "HEAD..%s/%s" % (remote, base)
        ]
        merge_log = self.communicate(*args)
        merge_log = merge_log.rstrip("\n")

        args = ["git", "merge", "--ff-only", "%s/%s" % (remote, base)]
        msg = self.communicate(*args)
        msg = msg.rstrip("\n").split("\n")[0] + "\n"
        self.dbg(msg)
        return msg, merge_log

    def rebase(self, newbase, upstream, sha1):
        self.call_info("git", "rebase", "--onto",
                       "%s" % newbase, "%s" % upstream, "%s" % sha1)

    def get_rev_list(self, commit):
        """Return first parent revision list for a given commit"""
        args = ["git", "rev-list", "--first-parent", "%s" % commit]
        o = self.communicate(*args)
        return o.splitlines()

    def has_local_changes(self):
        """Check for local changes in the Git repository"""
        out = self.communicate("git", "status", "--porcelain").strip()
        if out:
            self.dbg("%s has local changes", self)
            return True
        else:
            self.dbg("%s has no local changes", self)
            return False

    def has_ref(self, ref):
        """Check for reference existence in the local Git repository"""

        try:
            self.call("git", "show-ref", "--verify", "--quiet", ref)
            return True
        except Exception:
            return False

    def has_local_tag(self, tag):
        """Check for tag existence in the local Git repository"""

        return self.has_ref("refs/tags/%s" % tag)

    def has_local_branch(self, branch):
        """Check for branch existence in the local Git repository"""

        return self.has_ref("refs/heads/%s" % branch)

    def has_remote_branch(self, branch, remote="origin"):
        """Check for branch existence in the local Git repository"""

        return self.has_ref("refs/remotes/%s/%s" % (remote, branch))

    def has_local_object(self, commit):
        """Check for object existence in the local Git repository"""

        try:
            self.call("git", "cat-file", "-e", commit)
            return True
        except Exception:
            return False

    def has_remote_tag(self, name, remote="origin"):
        self.dbg("Check tag exists %s...", name)
        p = self.call_no_wait(
            "git", "ls-remote", "--tags", "--exit-code",
            remote, name)
        rcode = p.wait()
        return 0 == rcode

    def is_valid_tag(self, tag):
        """Check the validity of a reference name for a tag"""

        try:
            self.call("git", "check-ref-format", "refs/tags/%s" % tag)
            return True
        except Exception:
            return False

    def get_submodule_paths(self):
        """Return path of repository submodules"""

        submodule_paths = self.communicate(
            "git", "submodule", "--quiet", "foreach", "echo $path")
        submodule_paths = submodule_paths.split("\n")[:-1]

        return submodule_paths

    def merge_base(self, a, b):
        """Return the first ancestor between two branches"""

        try:
            mrg = self.communicate("git", "merge-base", a, b)
        except Exception as e:
            self.log.error(e)
            raise Exception(
                'Failed to find common ancestor of %s and %s' % (a, b))
        return mrg.strip()

    def list_remotes(self):
        """Return a list of existing remotes"""

        remotes = self.communicate("git", "remote")
        remotes = remotes.split("\n")[:-1]

        return remotes

    def get_remote_url(self, remote_name="origin"):
        """Return the URL of the remote"""

        self.cd(self.path)
        return git_config("remote.%s.url" % remote_name)

    #
    # Higher level git commands
    #

    def get_remote_info(self, remote_name):
        """
        Return user and repository name of the specified remote.

        Remote must be on GitHub, i.e. of type
        *github/user/repository.git
        """
        remoteurl = self.get_remote_url(remote_name)
        if remoteurl is None:
            raise Stop(1, "Failed to find remote: %s.\nAvailable remotes: %s"
                       " can be passed with the --remote argument."
                       % (remote_name, ", ".join(self.list_remotes())))
        if remoteurl[-1] == "/":
            remoteurl = remoteurl[:-1]

        # Read user from remote URL
        dirname = os.path.dirname(remoteurl)
        assert "github" in dirname, 'URL of remote %s: %s is not on GitHub' \
            % (remote_name, dirname)
        user = os.path.basename(dirname)
        if ":" in dirname:
            user = user.split(":")[-1]

        # Read repository from remote URL
        basename = os.path.basename(remoteurl)
        if ".git" in basename:
            repo = basename.rsplit(".git")[0]
        else:
            repo = basename.rsplit()[0]
        return [user, repo]

    def list_merged_files(self, sha, upstream="HEAD"):
        """
        Return a list of files modified by this PR
        """
        files = self.communicate(
            "git", "diff", "--name-only", "%s...%s" % (upstream, sha))
        files = set(files.split("\n")[:-1])
        return files

    def list_upstream_changes(self, sha, upstream="HEAD"):
        """
        Return a list of files modified in parent since this PR was branched,
        suggesting a rebase may be necessary.
        """
        mrg = self.merge_base(upstream, sha)
        common_base = mrg.split("\n")[0]

        files = self.communicate(
            "git", "diff", "--name-only", "%s..%s" % (common_base, upstream))
        files = set(files.split("\n")[:-1])
        return files

    def get_possible_conflicts(
            self, pull, conflict_files, changed_files, upstream):
        """
        Find possible conflicting pull requests by finding other pull requests
        which modify the same file.

        conflict_files: A list of conflicting files
        changed_files: A dictionary of (PullRequest, [changed-filenames])
        upstream: The SHA1 of the upstream branch before any other PRs were
          merged, required to detect if a rebase might be needed
        """
        conflicts = {}
        upstream_conflicts = set()
        if not changed_files:
            return conflicts, upstream_conflicts

        pull_changed = set()
        for cf in conflict_files:
            if cf in changed_files[pull]:
                pull_changed.add(cf)
            else:
                # Uncommitted changes in working directory
                try:
                    conflicts[None].append(cf)
                except KeyError:
                    conflicts[None] = [cf]

        if upstream:
            upstream_changes = self.list_upstream_changes(
                pull.get_sha(), upstream=upstream)
            upstream_conflicts = pull_changed.intersection(upstream_changes)

        for (pr, changed) in changed_files.iteritems():
            if pr != pull:
                both_changed = pull_changed.intersection(changed)
                if both_changed:
                    conflicts[pr] = both_changed
        return conflicts, upstream_conflicts

    def safe_merge(self, sha, message):
        """Merge a branch and revert to current HEAD in case of conflict.
        Returns: [] if the merge succeeded
                 list of conflicting paths if it failed
                 [None] if it failed and conflict detection also failed
        """
        premerge_sha = self.communicate("git", "rev-parse", "HEAD")
        premerge_sha = premerge_sha.rstrip("\n")

        try:
            self.call("git", "merge", "--no-ff", "-m", message, sha)
            return []
        except Exception:
            try:
                conflicts = self.communicate(
                    "git", "diff", "--name-only", "--diff-filter=U")
                conflicts = [c for c in conflicts.split('\n') if c]
                if not conflicts:
                    self.info('Conflict detection failed')
                    conflicts = [None]
                return conflicts
            finally:
                self.call("git", "reset", "--hard", "%s" % premerge_sha)

    def merge(self, comment=False, commit_id="merge",
              set_commit_status=False):
        """Merge candidate pull requests and pull requests."""
        self.dbg("## Unique users: %s", self.unique_logins())
        for key, url in self.get_merge_remotes().items():
            self.call("git", "remote", "add", key, url)
            self.fetch(key)

        upstream_sha = self.get_current_sha1()
        changed_files = {}

        conflicting_pulls = []
        merged_pulls = []
        conflicting_branches = []
        merged_branches = []

        for pullrequest in self.origin.candidate_pulls:
            # Compare current PR against the list of PRs merged so far
            # (An alternative would be to compare against pre-merge by
            # passing upstream_sha as the second of list_merged_files)
            files = self.list_merged_files(pullrequest.get_sha())
            changed_files[pullrequest] = files

            merge_status = self.merge_pull(
                pullrequest, comment=comment, commit_id=commit_id,
                all_changed_files=changed_files, upstream=upstream_sha)
            if merge_status:
                merged_pulls.append(pullrequest)
            else:
                conflicting_pulls.append(pullrequest)

        for remote, repo_branches in \
                self.origin.candidate_branches.iteritems():
            # repo = repo_branches[0]
            for branch_name in repo_branches[1]:
                merge_status = self.merge_branch(
                    remote, branch_name, commit_id=commit_id)
                if merge_status:
                    merged_branches.append('%s:%s' % (remote, branch_name))
                else:
                    conflicting_branches.append(
                        '%s:%s' % (remote, branch_name))

        merge_msg = self.log_merge(merged_pulls, merged_branches,
                                   conflicting_pulls, conflicting_branches)

        if set_commit_status and get_token():
            conflict = len(conflicting_branches) or len(conflicting_pulls)
            status = 'failure' if conflict else 'success'
            success_msg = 'Not all current branches/PRs can be merged.'
            conflict_msg = 'All current PRs/branches can be merged.'
            message = conflict_msg if conflict else success_msg
            url = BUILD_URL if IS_JENKINS_JOB else github.GithubObject.NotSet
            merge_msg += self.set_commit_status(status, message, url)

        self.call("git", "submodule", "update")
        return merge_msg

    def log_merge(self, merged_pulls, merged_branches, conflicting_pulls,
                  conflicting_branches):

        merge_msgs = []

        if merged_pulls:
            merge_msg = "Merged PRs:\n"
            merge_msg += "\n".join([str(x) for x in merged_pulls])
            merge_msg += "\n"
            merge_msgs.append(merge_msg)

        if merged_branches:
            merge_msg = "Merged branches:\n"
            merge_msg += "\n".join(["  # %s\n" % x for x in merged_branches])
            merge_msg += "\n"
            merge_msgs.append(merge_msg)

        if conflicting_pulls:
            merge_msg = "Conflicting PRs (not included):\n"
            merge_msg += "\n".join([str(x) for x in conflicting_pulls])
            merge_msg += "\n"
            merge_msgs.append(merge_msg)

        if conflicting_branches:
            merge_msg = "Conflicting branches (not included):\n"
            merge_msg += "\n".join(["  # %s\n" % x for x in
                                    conflicting_branches])
            merge_msg += "\n"
            merge_msgs.append(merge_msg)

        return "\n".join(merge_msgs)

    def get_conflicts_message(self, conflicts, upstream_conflicts):
        conflict_msg = ''
        if conflicts or upstream_conflicts:
            conflict_msg += '\nPossible conflicts:'
        else:
            conflict_msg += '\nFailed to autodetect conflicts'

        if conflicts:
            for pr in sorted(conflicts.keys(),
                             key=lambda c: c.get_number() if c else None):
                if pr:
                    conflict_msg += "\n  - PR #%d %s '%s'\n%s" % (
                        pr.get_number(), pr.get_login(), pr.get_title(),
                        '\n'.join('    - %s' % f for f in conflicts[pr]))
                else:
                    conflict_msg += "\n  - Conflict detection failed\n%s" % (
                        '\n'.join('    - %s' % f for f in conflicts[pr]))
        if upstream_conflicts:
            conflict_msg += '\n  - Upstream changes\n' + \
                '\n'.join('    - %s' % f for f in upstream_conflicts)
        return conflict_msg

    def merge_pull(self, pullrequest, comment=False, commit_id="merge",
                   all_changed_files=None, upstream=None):
        """Merge pull request."""

        commit_msg = "%s: PR %s (%s)" % (
            commit_id, pullrequest.get_number(), pullrequest.get_title())
        conflict_files = self.safe_merge(pullrequest.get_sha(), commit_msg)
        previous_conflict_status = pullrequest.get_conflict_status(
            self.gh.get_login())

        if IS_JENKINS_JOB:
            build_msg = (
                "build [%s#%s](%s). "
                "See the [console output](%s) for more details."
                % (JOB_NAME, BUILD_NUMBER, BUILD_URL,
                   BUILD_URL + "consoleText"))

        if not conflict_files:
            if not pullrequest.body and comment and get_token():
                self.dbg("Adding comment to Pull Request #%g."
                         % pullrequest.get_number())
                pullrequest.create_issue_comment(EMPTY_MSG)
            if previous_conflict_status:
                # Resolve both PR_IS_CONFLICTING and PR_WAS_CONFLICTING
                self.dbg("Resolving previous conflict on Pull Request #%g."
                         % pullrequest.get_number())
                merged_msg = "Conflict resolved"
                if IS_JENKINS_JOB:
                    merged_msg += " in %s" % build_msg
                pullrequest.resolve_conflict_status(
                    self.gh.get_login(), merged_msg)
            return True

        conflict_msg = "Conflicting PR."
        if IS_JENKINS_JOB:
            conflict_msg += " Removed from %s" % build_msg

        conflicts, upstream_conflicts = self.get_possible_conflicts(
            pullrequest, conflict_files, all_changed_files, upstream)
        conflict_msg += self.get_conflicts_message(
            conflicts, upstream_conflicts)

        conflict_msg += '\n\n%s\n' % CONFLICT_COMMENT

        self.info('%s\n%s', pullrequest, conflict_msg)

        if comment and get_token():
            if previous_conflict_status == PullRequest.PR_IS_CONFLICTING:
                self.dbg("Not adding comment to issue #%g, already %s.",
                         pullrequest.get_number(), CONFLICT_COMMENT)
            else:
                self.dbg("Adding comment to issue #%g.",
                         pullrequest.get_number())
                pullrequest.create_issue_comment(conflict_msg)
        return False

    def merge_branch(self, remote, branch_name, commit_id="merge"):
        """Merge branch."""
        ref = 'merge_%s/%s' % (remote, branch_name)
        if not self.has_remote_branch(branch_name, 'merge_%s' % remote):
            raise Exception('Remote branch not found: %s' % ref)
        try:
            self.merge_base('HEAD', ref)
        except Exception:
            self.info(
                'No common ancester found for %s:%s', remote, branch_name)
            return False

        commit_msg = "%s: branch %s:%s" % (commit_id, remote, branch_name)
        conflict_files = self.safe_merge(ref, commit_msg)

        if not conflict_files:
            return True

        conflict_msg = "Conflicting branch."
        conflict_msg += self.get_conflicts_message(None, conflict_files)

        self.info('%s:%s\n%s', remote, branch_name, conflict_msg)
        return False

    def set_commit_status(self, status, message, url):
        msg = ""
        for pullrequest in self.origin.candidate_pulls:
            msg += "Setting commit status %s on PR %s (%s)\n" % (
                status,
                pullrequest.get_number(),
                pullrequest.get_sha(),
            )
            pullrequest.create_status(status, message, url)
        return msg

    def find_branching_point(self, topic_branch, main_branch):
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

    def rset_commit_status(self, filters, status, message, url, info=False):
        """Recursively set commit status for PRs for each submodule."""

        msg = ""
        msg += str(self.origin) + "\n"
        msg += self.origin.find_candidate_pulls(filters)
        if info:
            msg += self.origin.merge_info()
        else:
            msg += self.set_commit_status(status, message, url)

        for submodule_repo in self.submodules:
            # Create submodule filters
            sub_filters = copy.deepcopy(filters)
            for ftype in ["include", "exclude"]:
                sub_filters.pop("pr", None)  # Do not copy top-level PRs

            msg += submodule_repo.rset_commit_status(
                sub_filters, status, message, url, info)

        return msg

    def get_fork_filter(self, is_submodule=False):
        """Return filter for including tracking branches"""
        if is_submodule:
            return lambda x: (
                '/' in x and x.endswith(self.origin.repo_name))
        else:
            repo_names = tuple([s.origin.repo_name for s in self.submodules])
            return lambda x: (
                '/' in x and not x.endswith(repo_names))

    def rmerge(self, filters, info=False, comment=False, commit_id="merge",
               top_message=None, update_gitmodules=False,
               set_commit_status=False, allow_empty=True, is_submodule=False):
        """Recursively merge PRs for each submodule."""

        if self.repository_config is not None and \
           "base-branch" in self.repository_config and \
           filters["base"] != self.repository_config["base-branch"]:
            self.log.info("Overriding base-branch from %s to %s" %
                          (filters["base"],
                           self.repository_config["base-branch"]))
            filters["base"] = self.repository_config["base-branch"]

        updated = False
        merge_msg = ""
        merge_msg += str(self.origin) + "\n"
        merge_msg += self.origin.find_candidate_pulls(filters)
        self.origin.find_candidate_branches(
            filters, fork_filter=self.get_fork_filter(is_submodule))
        if info:
            merge_msg += self.origin.merge_info()
        else:
            self.cd(self.path)
            self.write_directories()
            presha1 = self.get_current_sha1()
            if self.has_remote_branch(filters["base"], self.remote):
                ff_msg, ff_log = self.fast_forward(filters["base"],
                                                   remote=self.remote)
                merge_msg += ff_msg
                # Scan the ff log to produce a digest of the merged PRs
                if ff_log:
                    merge_msg += "Previously merged:\n"
                    pattern = r'Merge pull request #(\d+)'
                    for line in ff_log.split('\n'):
                        s = re.search(pattern, line)
                        if s is not None:
                            pr = self.origin.get_pull(int(s.group(1)))
                            merge_msg += str(PullRequest(pr)) + '\n'
                merge_msg += '\n'

            merge_msg += self.merge(comment, commit_id=commit_id,
                                    set_commit_status=set_commit_status)
            postsha1 = self.get_current_sha1()
            updated = (presha1 != postsha1)

        for submodule_repo in self.submodules:
            # Create submodule filters
            sub_filters = copy.deepcopy(filters)
            # Do not copy top-level PRs
            for ftype in ["include", "exclude"]:
                sub_filters[ftype].pop("pr", None)
            try:
                submodule_updated, submodule_msg = submodule_repo.rmerge(
                    sub_filters, info, comment, commit_id=commit_id,
                    update_gitmodules=update_gitmodules,
                    set_commit_status=set_commit_status,
                    allow_empty=allow_empty, is_submodule=True)
                merge_msg += "\n" + submodule_msg
            finally:
                self.cd(self.path)

        if not info:
            summary_update = self.summary_commit(
                merge_msg, commit_id=commit_id, top_message=top_message,
                update_gitmodules=update_gitmodules, allow_empty=allow_empty)
            if summary_update:
                updated = True

        return updated, merge_msg

    def summary_commit(self, merge_msg, commit_id="merge", top_message=None,
                       update_gitmodules=False, allow_empty=True):
        """Create a top-level summary commit bumping the submodules"""

        if IS_JENKINS_JOB:
            merge_msg_footer = "\nGenerated by %s#%s (%s)" \
                               % (JOB_NAME, BUILD_NUMBER, BUILD_URL)
        else:
            merge_msg_footer = ""

        if top_message is None:
            top_message = commit_id

        commit_message = "%s\n\n%s" \
            % (top_message, merge_msg + merge_msg_footer)

        if update_gitmodules:
            submodule_paths = self.get_submodule_paths()
            for path in submodule_paths:
                # Read submodule URL registered in .gitmodules
                config_url = "submodule.%s.url" % path
                submodule_url = git_config(config_url,
                                           config_file=".gitmodules")

                # Substitute submodule URL using connection login
                user = self.gh.get_login()
                pattern = '(.*github.com[:/]).*(/.*.git)'
                new_url = re.sub(pattern, r'\1%s\2' % user, submodule_url)
                git_config(config_url, config_file=".gitmodules",
                           value=new_url)

                # Substitute submodule branch
                if self.push_branch is not None:
                    config_branch = "submodule.%s.branch" % path
                    git_config(config_branch, config_file=".gitmodules",
                               value=self.push_branch_name)

        updated = self.has_local_changes()
        if updated:
            self.call("git", "commit", "-a", "-n", "-m", commit_message)
        elif allow_empty:
            self.call("git", "commit", "--allow-empty", '-a', "-n", "-m",
                      commit_message)

        return updated

    def get_tag_prefix(self):
        "Return the tag prefix for this repository using git describe"

        try:
            version = self.communicate("git", "describe")
            prefix = re.split('\d', version)[0]
        except Exception:
            # If no tag is present on the branch, git describe fails
            prefix = ""

        return prefix

    def rtag(self, version, message=None, sign=False, prefix=None):
        """Recursively tag repositories with a version number."""

        msg = ""
        for repo in [self] + self.submodules:
            msg += str(repo.origin) + "\n"
            if prefix:
                full_tag = prefix + version
            else:
                full_tag = repo.get_tag_prefix() + version
            repo.tag(full_tag, message, sign=sign)
            msg += "Created tag %s\n" % (full_tag)

        return msg

    def tagdelete(self, version):
        tag_prefix = self.get_tag_prefix()
        tag_string = ":%s%s" % (tag_prefix, version)
        self.log.info(self.origin)
        try:
            if self.has_remote_tag(tag_string):
                self.log.info("Pushing %s to %s", tag_string, self.remote)
                self.push_branch(tag_string, remote=self.remote)
        except Exception:
            self.log.warn("Failed to push", exc_info=1)

        try:
            tag_string = tag_string[1:]
            if self.has_local_tag(tag_string):
                self.log.info("Removing local tag %s", tag_string)
                self.call("git", "tag", "-d", tag_string)
        except Exception:
            self.log.warn("Failed to remove local tag", exc_info=1)

    def rtagdelete(self, version):
        """Recursively remove tag from repositories."""
        self.tagdelete(version)
        for repo in self.submodules:
            repo.tagdelete(version)

    def unique_logins(self):
        """Return a set of unique logins."""
        unique_logins = set()
        for pull in self.origin.candidate_pulls:
            unique_logins.add((pull.get_head_login(), pull.get_head_repo()))
        for remote, repo_branches in \
                self.origin.candidate_branches.iteritems():
            unique_logins.add((remote, repo_branches[0]))
        return unique_logins

    def get_merge_remotes(self):
        """Return remotes associated to unique login."""
        remotes = {}
        for user, repo in self.unique_logins():
            key = "merge_%s" % user
            if repo.private:
                url = repo.ssh_url
            else:
                url = repo.git_url
            remotes[key] = url
        return remotes

    def rcleanup(self):
        """Recursively remove remote branches created for merging."""

        self.cleanup()
        for submodule_repo in self.submodules:
            try:
                submodule_repo.rcleanup()
            except Exception:
                self.dbg("Failed to clean repository %s" % self.path)
            self.cd(self.path)

    def cleanup(self):
        """Remove remote branches created for merging."""
        if self.gh:  # no gh implies no connection
            remotes = self.list_remotes()
            merge_remotes = [x for x in self.get_merge_remotes().keys()
                             if x in remotes]
            for merge_remote in merge_remotes:
                try:
                    self.call("git", "remote", "rm", merge_remote)
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

    def __del__(self):
        # We need to make sure our logging wrappers are closed when this
        # instance's reference count hits zero and it is garbage collected.
        # If we do to not do this the logging wrapper thread will block
        # forever because the write end of the PIPE has not been closed.
        self.infoWrap.close()
        self.debugWrap.close()

#
# Exceptions
#


class UnknownMerge(Exception):
    """
    Exception which specifies that the given commit
    doesn't qualify as a GitHub-style merge.
    """

    def __init__(self, line):
        self.line = line
        super(UnknownMerge, self).__init__()


class GitHubCommand(Command):
    """
    Abstract class for commands acting on a git repository
    """

    NAME = "abstract"

    def __init__(self, sub_parsers, **kwargs):
        super(GitHubCommand, self).__init__(sub_parsers, **kwargs)

        sha1_chars = "^([0-9a-f]+)\s"
        self.pr_pattern = re.compile(sha1_chars +
                                     "Merge\spull\srequest\s.(\d+)\s(.*)$")
        self.commit_pattern = re.compile(sha1_chars + "(.*)$")
        self.add_token_args()
        self.parser.add_argument(
            '--callbacks', default=self.show_rate, help=argparse.SUPPRESS)

    def configure_logging(self, args):
        super(GitHubCommand, self).configure_logging(args)
        logging.getLogger('github').setLevel(logging.INFO)

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
        self.show_rate()

    def show_rate(self):
        core, search = self.gh.get_rate_limits()
        logging.getLogger('scc.gh').debug((
            "%(remaining)s remaining from "
            "%(limit)s (Reset at %(time)s)") % core)

    def parse_pr(self, line):
        m = self.pr_pattern.match(line)
        if not m:
            raise UnknownMerge(line=line)
        sha1 = m.group(1)
        num = int(m.group(2))
        rest = m.group(3)
        return sha1, num, rest

    def parse_commit(self, line):
        m = self.commit_pattern.match(line)
        if not m:
            raise UnknownMerge(line=line)
        sha1 = m.group(1)
        rest = m.group(2)
        return sha1, rest

    def add_remote_arg(self):
        self.parser.add_argument(
            '--remote', default="origin",
            help='Name of the remote to use as the origin')

    def add_token_args(self):
        self.parser.add_argument(
            "--token",
            help="Token to use rather than from config files")
        self.parser.add_argument(
            "--no-ask", action='store_true',
            help="Do not ask for a password if token usage fails")


class GitRepoCommand(GitHubCommand):
    """
    Abstract class for commands acting on a git repository
    """

    NAME = "abstract"

    def __init__(self, sub_parsers, **kwargs):
        super(GitRepoCommand, self).__init__(sub_parsers, **kwargs)
        self.parser.add_argument(
            '--shallow', action='store_true',
            help='Do not recurse into submodules')
        self.parser.add_argument(
            '--reset', action='store_true',
            help='Reset the current branch to its HEAD')
        self.add_remote_arg()

    def init_main_repo(self, args):
        repository_config = None
        if hasattr(args, "repository_config"):
            repository_config = args.repository_config
        push_branch = None
        if hasattr(args, "push"):
            push_branch = args.push
        self.main_repo = self.gh.git_repo(
            self.cwd, remote=args.remote, push_branch=push_branch,
            repository_config=repository_config)
        if not args.shallow:
            self.main_repo.register_submodules()
        if args.reset:
            self.main_repo.reset()
            self.main_repo.get_status()
        return [self.main_repo] + self.main_repo.submodules

    def add_new_commit_args(self):
        self.parser.add_argument(
            '--message', '-m',
            help='Message to use for the commit. '
            'Overwrites auto-generated value')
        self.parser.add_argument(
            '--push', type=str,
            help='Name of the branch to use to recursively push'
            ' the merged branch to GitHub')
        self.parser.add_argument(
            '--update-gitmodules', action='store_true',
            help='Update submodule URLs to point at the forks'
            ' of the GitHub user')
        self.parser.add_argument('base', type=str)

    def push(self, args, main_repo):
        branch_name = "HEAD:refs/heads/%s" % (args.push)

        user = self.gh.get_login()
        remote = "git@github.com:%s/" % (user) + "%s.git"

        main_repo.rpush(branch_name, remote, force=True)
        gh_branch = "https://github.com/%s/%s/tree/%s" \
            % (user, main_repo.origin.repo_name, args.push)
        self.log.info("Merged branch pushed to %s" % gh_branch)

    def get_open_pr(self, args):
        user = self.gh.get_login()
        branch_name = args.push

        for pull in self.main_repo.origin.get_pulls():
            if pull.head.user.login == user and pull.head.ref == branch_name:
                self.log.info("PR %s already opened", pull.number)
                return PullRequest(pull)

        return None


def get_default_filters(default):
    filters = {}
    if default == "org":
        filters["include"] = {
            "user": ["#org"], "label": ["include"]}
        filters["exclude"] = {"label": ["exclude", "breaking"]}
    elif default == "none":
        filters["include"] = {}
        filters["exclude"] = {}
    elif default == "all":
        filters["include"] = {"user": ["#all"]}
        filters["exclude"] = {}
    else:
        raise "Default %s non-defined"
    return filters


class FilteredPullRequestsCommand(GitRepoCommand):
    """
    Abstract base class for repo commands that take filters to find
    and work with open pull requests
    """

    def __init__(self, sub_parsers):
        super(FilteredPullRequestsCommand, self).__init__(sub_parsers)
        self.parser.add_argument(
            '--info', action='store_true',
            help='Display pull requests but do not perform actions on them')

    def _configure_filters(self):
        filter_desc = """Filters can be specified as key value pairs, e.g. \
KEY:VALUE or using a hash symbol, e.g. prefix#NUMBER. Recognized key/values \
are label:LABEL, pr:NUMBER, user:USERNAME. For user keys, user:#org means \
any public member of the repository organization and user:#all means any \
user.  Filter values with a hash symbol allow to filter Pull Requests by \
number, e.g. #NUMBER or ORG/REPO#NUMBER for the ORG/REPO submodule. If \
neither  a key/value nor a hash symbol is found, the filter is considered a \
label filter."""
        self.parser.add_argument(
            '--default', '-D', type=str,
            choices=["none", "org", "all"], default="org",
            help="""Specify the default set of filters to use. NONE means no \
filter is preset. ORG sets user:#org, label:include as the default include \
filters and label:exclude and label:breaking as the default exclude filets. \
ALL sets user:#all as the default include filter. Default: ORG.""")
        self.parser.add_argument(
            '--include', '-I', type=str, action='append',
            help='Filters to include Pull Requests. ' + filter_desc)
        self.parser.add_argument(
            '--exclude', '-E', type=str, action='append',
            help='Filters to exclude Pull Requests. ' + filter_desc)
        self.parser.add_argument(
            '--check-commit-status', '-S', type=str,
            choices=["none", "no-error", "success-only"], default="none",
            help='Check success/failure status on latest commits to include '
            ' Pull Requests in the merge.')

    def get_action(self):
        pass

    def _log_filters(self, info=False):
        if info:
            action = "Listing Pull Request(s)"
        else:
            action = self.get_action() + " Pull Request(s)"
        self.log.info("%s based on %s", action, self.filters["base"])

        ftype_desc = {'include': 'Including', 'exclude': 'Excluding'}
        key_value_map = {
            "label": ("%s Pull Request(s) labelled as", lambda x: x),
            "pr": ("%s Pull Request(s)", lambda x: x),
            "user": ("%s Pull Request(s) opened by", self.get_user_desc)}

        for ftype in sorted(ftype_desc.keys(), reverse=True):
            for key in sorted(self.filters[ftype].keys(), reverse=True):
                if key in key_value_map:
                    key_desc = key_value_map[key][0] % ftype_desc[ftype]
                    value_map = key_value_map[key][1]
                    values_desc = map(value_map, self.filters[ftype][key])
                else:
                    key_desc = "%s %s Branches(s)/Pull Request(s)" % (
                        ftype_desc[ftype], key)
                    values_desc = self.filters[ftype][key]
                filter_desc = key_desc + " %s" % " or ".join(values_desc)
                self.log.info("%s", filter_desc)

        status_map = {
            "success-only": "without successful status",
            "no-error": "with either error or failure status"}
        if self.filters.get('status') and self.filters['status'] != "none":
            self.log.info('Excluding Pull Request(s) %s' %
                          status_map[self.filters['status']])

    def get_user_desc(self, value):
        if value == '#org':
            if self.main_repo.origin.org:
                return 'any public member of the organization'
            else:
                return 'the repository owner'
        if value == '#all':
            return 'any user'
        return '%s' % value

    def _parse_filters(self, args):
        """ Read filters from arguments and fill filters dictionary"""

        self.filters = get_default_filters(args.default)
        self.filters["base"] = args.base

        for ftype in ["include", "exclude"]:
            if not getattr(args, ftype):
                continue

            for filt in getattr(args, ftype):
                found = self._parse_key_value(ftype, filt)
                if found:
                    continue

                found = self._parse_hash(ftype, filt)
                if found:
                    continue

                found = self._parse_branch_string(ftype, filt)
                if found:
                    continue

                found = self._parse_branch_url(ftype, filt)
                if found:
                    continue

                self.filters[ftype].setdefault("label", []).append(filt)

        self.filters["status"] = args.check_commit_status

    def _parse_key_value(self, ftype, key_value):
        """Parse a key/value pattern of type key/value"""
        keyvalue_pattern = r'(?P<key>([\w-]+)(/[\w-]+)?)' + \
            r':(?P<value>#?([/\w-]+))'
        pattern = re.compile(keyvalue_pattern + '$')
        m = pattern.match(key_value)
        if not m:
            return False

        key = m.group('key')
        value = m.group('value')
        if key == 'pr':
            value = '#' + value
        self.filters[ftype].setdefault(key, []).append(value)
        return True

    def _parse_hash(self, ftype, value):
        """Parse a hash pattern of type #n or user/repo#n"""
        hash_pattern = r'(?P<prefix>([\w-]+/[\w-]+)?)#(?P<nr>\d+)'
        hash_pattern = re.compile(hash_pattern + '$')
        m = hash_pattern.match(value)
        if not m:
            return False

        if not m.group('prefix'):
            prefix = 'pr'
        else:
            prefix = m.group('prefix')
        self.filters[ftype].setdefault(prefix, []).append('#' + m.group('nr'))
        return True

    def _parse_url(self, ftype, value):
        """
        Parse a Pull Request URL of type https://github.com/user/repo/pull/n
        """
        github_url = r'https://github.com/%s/pull/%s' % \
            (r'(?P<prefix>([\w-]+/[\w-]+))', r'(?P<nr>\d+)')
        url_pattern = re.compile(github_url + '$')
        m = url_pattern.match(value)
        if not m:
            return False

        prefix = m.group('prefix')
        self.filters[ftype].setdefault(prefix, []).append('#' + m.group('nr'))
        return True

    def _parse_branch_string(self, ftype, value):
        """Parse a branch string of type user/repo:branch"""
        branch_pattern = r'(?P<prefix>([\w-]+/[\w-]+)):(?P<branch>[\.\w-]+)'
        branch_pattern = re.compile(branch_pattern + '$')
        m = branch_pattern.match(value)
        if not m:
            return False
        prefix = m.group('prefix')
        self.filters[ftype].setdefault(prefix, []).append(m.group('branch'))
        return True

    def _parse_branch_url(self, ftype, value):
        """Parse a branch URL of type
           https://github.com/user/repo/tree/<branch>"""
        github_url = r'https://github.com/%s/tree/%s' % \
            (r'(?P<prefix>([\w-]+/[\w-]+))', r'(?P<branch>[\.\w-]+)')
        url_pattern = re.compile(github_url + '$')
        m = url_pattern.match(value)
        if not m:
            return False

        prefix = m.group('prefix')
        self.filters[ftype].setdefault(prefix, []).append(m.group('branch'))
        return True


class CheckLabels(GitRepoCommand):
    """
    Check which PRs are not labelled with a base branch label.
    For admins, allow setting a base-based label on all pull requests.
    """

    NAME = "check-labels"

    def __init__(self, sub_parsers):
        super(CheckLabels, self).__init__(sub_parsers)
        self.parser.add_argument(
            '--set',
            action='store_true',
            default=False,
            help='Whether or not to set labels (Admin-only)')

    def __call__(self, args):
        super(CheckLabels, self).__call__(args)
        self.login(args)
        all_repos = self.init_main_repo(args)
        for repo in all_repos:
            print repo.origin
            pulls = repo.origin.get_pulls()
            for pull in pulls:
                pr = PullRequest(pull)
                self.check_pr_label(pr,
                                    args.set and repo.origin.permissions.push)

    def check_pr_label(self, pr, set_label=False):
        label = pr.base.ref
        # Read existing labels
        pr_labels = [x for x in pr.get_labels()]
        if label not in pr_labels:
            if set_label:
                pr.get_issue().add_to_labels(label)
                print "Added label %s to %s" % (label, pr.number)
            else:
                print "Missing label %s on %s" % (label, pr.number)


class CheckMilestone(GitRepoCommand):
    """Check all merged PRs for a set milestone

Find all GitHub-merged PRs between tagged release and sha1, i.e.
git log --first-parent TAG...HEAD

Usage:
    check-milestone 0.2.0 0.2.1 --set=0.2.1
    """

    NAME = "check-milestone"

    def __init__(self, sub_parsers):
        super(CheckMilestone, self).__init__(sub_parsers)
        self.parser.add_argument(
            'release1',
            help="Release number to use as the search starting point")
        self.parser.add_argument(
            'release2',
            help="Release number to use as the search ending point")
        self.parser.add_argument(
            '--set', dest="milestone_name",
            help="Milestone to use if unset (requires write permissions)")

    def __call__(self, args):
        super(CheckMilestone, self).__call__(args)
        self.login(args)
        all_repos = self.init_main_repo(args)
        try:
            for repo in all_repos:
                print repo.origin
                self.check_milestone(repo, args)
        finally:
            self.main_repo.cleanup()

    def check_milestone(self, repo, args):

        milestone = None
        if args.milestone_name:
            milestone = repo.origin.get_milestone(args.milestone_name)
            if not milestone:
                raise Stop(3, "Unknown milestone: %s" % args.milestone_name)
            if not repo.origin.permissions.push:
                raise Stop(4, "Authenticated user does not have write access")

        # Construct tag 1 and check its validity
        tag1 = repo.get_tag_prefix() + args.release1
        if not repo.has_local_tag(tag1):
            raise Stop(21, "Tag %s does not exist." % tag1)

        # Construct tag 2 and check its validity
        tag2 = repo.get_tag_prefix() + args.release2
        if not repo.has_local_tag(tag2):
            if not repo.has_remote_branch(args.release2, remote=args.remote):
                raise Stop(21, "Tag %s does not exist." % tag2)
            else:
                tag2 = args.remote + '/' + args.release2

        o = repo.communicate(
            "git", "log", "--oneline", "--first-parent",
            "%s...%s" % (tag1, tag2))

        for line in o.split("\n"):
            if line.split():
                try:
                    sha1, num, rest = self.parse_pr(line)
                except Exception:
                    self.log.info("Unknown merge: %s", line)
                    continue
                pr = PullRequest(repo.origin.get_pull(num))
                self.check_pr_milestone(pr, milestone)

    def check_pr_milestone(self, pr, milestone=None):
        milestone_title = None
        has_milestone = False
        if pr.milestone:
            milestone_title = pr.milestone.title
            self.log.debug("PR %s in milestone %s",
                           pr.number, pr.milestone.title)
            has_milestone = True
        else:
            print "No milestone for PR %s: %s" % (pr.number, pr.title)

        set_milestone = False
        if milestone and (milestone_title != milestone.title):
            try:
                pr.get_issue().edit(milestone=milestone)
                print "Set milestone for PR %s to %s" \
                    % (pr.number, milestone.title)
            except github.GithubException, ge:
                if self.gh.exc_is_not_found(ge):
                    raise Stop(10, "Can't edit milestone")
                raise
            set_milestone = True

        return has_milestone, set_milestone


class CheckPRs(GitRepoCommand):
    """Check that PRs in one branch have been merged to another.

This makes use of git notes to detect links between PRs on two
different branches. These have likely be migrated via the rebase
command.

    """

    NAME = "check-prs"

    def __init__(self, sub_parsers):
        super(CheckPRs, self).__init__(sub_parsers)
        group = self.parser.add_mutually_exclusive_group()
        group.add_argument(
            '--parse', action='store_true',
            help="Parse generated files into git commands")
        group.add_argument(
            '--write', action='store_true',
            help="Write PRs to files.")
        group.add_argument(
            '--no-check', action='store_true',
            help="Do not check mismatching rebased PR comments.")
        group.add_argument(
            '--cache-dir',
            help="Directory to use to cache the rebased links.")

        self.parser.add_argument('a', help="First branch to compare")
        self.parser.add_argument('b', help="Second branch to compare")

    def fname(self, branch):
        return "%s_prs.txt" % branch

    def __call__(self, args):
        super(CheckPRs, self).__call__(args)
        self.login(args)

        if args.parse:
            self.parse(args.a, args.b)
            return

        self.init_main_repo(args)

        try:
            unrebased_count = 0
            mismatch_count = 0
            repos = [self.main_repo]
            repos.extend(self.main_repo.submodules)
            for repo in repos:
                print repo.origin
                self.prs = {}
                self.links = {}
                self.rebasedprs = set()
                s_unrebased, s_mismatch = self.notes(repo, args)
                unrebased_count += s_unrebased
                mismatch_count += s_mismatch

            if unrebased_count + mismatch_count > 0:
                raise Stop(unrebased_count + mismatch_count,
                           'Found %s unrebased PR(s) and %s mismatching PR(s)'
                           % (unrebased_count, mismatch_count))
        finally:
            self.main_repo.cleanup()

    def notes(self, repo, args):

        # Load cached links
        self.load_links(cache_dir=args.cache_dir,
                        cache_name=repo.origin.repo_name + '.rebased')
        self.rebasedprs.update(self.links.keys())

        # List unrebased PRs
        count1 = self.list_unrebased_prs(
            repo, args.a, args.b, remote=args.remote, write=args.write)
        count2 = self.list_unrebased_prs(
            repo, args.b, args.a, remote=args.remote, write=args.write)
        unrebased_count = count1 + count2

        if not args.no_check:
            # Check mismatching rebased PRs links
            m = self.check_links(repo.origin)
            if not m:
                mismatch_count = 0
            else:
                print "*"*100
                print "Mismatching rebased PR comments"
                print "*"*100

                for key in m.keys():
                    comments = ", ".join(['--rebased'+x for x in m[key]])
                    if key in self.rebasedprs:
                        self.rebasedprs.remove(key)
                    print "  # PR %s: expected '%s' comment(s)" %  \
                        (key, comments)
                mismatch_count = len(m.keys())
        else:
            mismatch_count = 0

        # Cache the rebased links
        rebased_links = dict((k, self.links[k]) for k in self.links
                             if k in self.rebasedprs)
        self.dump_links(rebased_links, cache_dir=args.cache_dir,
                        cache_name=repo.origin.repo_name + '.rebased')

        return unrebased_count, mismatch_count

    def list_prs(self, repo, source_branch, target_branch, remote="origin"):

        git_notes_ref = "refs/notes/see_also/" + target_branch
        merge_base = repo.find_branching_point(
            "%s/%s" % (remote, source_branch),
            "%s/%s" % (remote, target_branch))
        merge_range = "%s...%s/%s" % (merge_base, remote, source_branch)
        middle_marker = str(uuid.uuid4()).replace("-", "")
        end_marker = str(uuid.uuid4()).replace("-", "")

        cmd = [
            "git", "log",
            "--pretty=%%h %%s %%ar %s %%N %s" % (middle_marker, end_marker),
            "--first-parent", merge_range]
        if git_version() > (2, 7, 6):
                cmd += ["--notes=%s" % git_notes_ref]
        out = repo.communicate(*cmd)

        # List PRs without seealso notes
        pr_list = []
        for line in out.split(end_marker):
            line = line.strip()
            if not line:
                continue
            try:
                line, rest = line.split(middle_marker)
            except Exception:
                raise Exception("can't split on ##: " + line)
            if "See gh-" in rest or "n/a" in rest:
                continue

            try:
                sha1, num, rest = self.parse_pr(line)
                pr_list.append(num)
            except Exception:
                self.log.info("Unknown merge: %s", line)
        return pr_list

    def list_unrebased_prs(self, repo, source_branch, target_branch,
                           remote="origin", write=False):
        """
        Method for listing unrebased PRs while filtering out those which
        """

        pr_list = self.list_prs(repo, source_branch, target_branch, remote)
        self.log.debug(
            "Found %s first-parent PRs merged on %s without a see_also note"
            " for %s" % (len(pr_list), source_branch, target_branch))

        # Look into PR body/comment for rebase notes and fill match dictionary
        unrebased_prs = []
        for pr_number in [x for x in pr_list if x not in self.rebasedprs]:
            pr = self.visit_pr(repo.origin, pr_number)

            # No rebase comment found on the PR
            if not self.links[pr_number]:
                unrebased_prs.append(pr)
                continue

            # PR marked as no-rebase
            if self.links[pr_number] == -1:
                self.log.debug("PR %s is marked as no-rebase" % pr_number)
                continue

            # Test PRs marked as --rebased
            if not self.check_rebased_prs(repo, pr_number, target_branch):
                unrebased_prs.append(pr)

        # Print list of unrebased PRs
        if unrebased_prs:
            self.log.debug(
                "Found %s unrebased PRs from %s to %s"
                % (len(unrebased_prs), source_branch, target_branch))
            if write:
                fname = self.fname(source_branch)
                if os.path.exists(fname):
                    raise Stop("File already exists: %s" % fname)
                f = open(fname, "w")
                for pr in unrebased_prs:
                    print >> f, pr
            else:
                print "*"*100
                print "PRs on %s without note/comment for %s" \
                    % (source_branch, target_branch)
                print "*"*100
                for pr in unrebased_prs:
                    print pr

        return len(unrebased_prs)

    def check_rebased_prs(self, repo, pr_number, target_branch):
        targets, target_links = self.read_links(self.links, pr_number)
        for target in targets:
            target_pr = self.visit_pr(repo.origin, target)
            target_status = (target_pr.pull.state == 'open' or
                             target_pr.pull.merged)

            # Check  PR is open or merged against the target branch
            if (target_status and target_pr.get_base() == target_branch):
                self.log.debug("PR %s is rebased as %s on %s"
                               % (pr_number, target, target_branch))
                # List as rebased is both the source and target PRs are merged
                if target_pr.pull.merged and self.prs[pr_number].pull.merged:
                    self.rebasedprs.add(pr_number)
                return True
        return False

    def load_links(self, cache_dir=None, cache_name="cache"):
        """Load links from local cache"""

        if cache_dir is None:
            self.log.debug("No cache_dir specified. Skipping.")
            return

        cache_full_path = os.path.join(cache_dir, cache_name + '.cache')
        if not os.path.isfile(cache_full_path):
            self.log.debug("%s does not exist. Skipping.", cache_full_path)
            return

        import pickle
        with open(cache_full_path, 'rb') as handle:
            self.log.debug('Read links from %s', cache_full_path)
            self.links.update(pickle.loads(handle.read()))

    def dump_links(self, links, cache_dir=None, cache_name="cache"):
        """Cache links locally"""

        if cache_dir is None:
            self.log.debug("No cache_dir specified. Skipping.")
            return

        if not os.path.isdir(cache_dir):
            self.log.debug("%s does not exist. Skipping.", cache_dir)
            return

        import pickle
        cache_full_path = os.path.join(cache_dir, cache_name + '.cache')
        with open(cache_full_path, 'wb') as handle:
            self.log.debug('Dump links to %s', cache_full_path)
            pickle.dump(links, handle)

    def check_links(self, gh_repo):
        """Return a dictionary of PRs with missing rebase comments"""

        m = self.check_directed_links(self.links)

        # Ensure all nodes (PRs) are visited - handling chained links
        while not all(x in self.links.keys() for x in m.keys()):

            for pr_number in [key for key in m.keys()
                              if key not in self.links.keys()]:
                self.visit_pr(gh_repo, pr_number)

            m = self.check_directed_links(self.links)

        return m

    @staticmethod
    def check_directed_links(links):
        """Find mismatching comments in rebased PRs"""

        mismatch_dict = {}
        for source_pr in links.keys():
            # Do not check PRs without rebase comments or marked as no-rebase
            if links[source_pr] == -1 or links[source_pr] is None:
                continue

            targets, target_links = CheckPRs.read_links(links, source_pr)
            for target_pr, target_link in zip(targets, target_links):

                if target_pr not in links.keys():
                    # Target PR has not been visited
                    mismatch = True
                elif links[target_pr] is None or links[target_pr] == -1:
                    # Target PR has no rebase comment or marked as non-rebase
                    mismatch = True
                elif not any(x.startswith(target_link) for x
                             in links[target_pr]):
                    # Non-matching target PR rebase comments
                    mismatch = True
                else:
                    mismatch = False

                if mismatch:
                    if target_pr in mismatch_dict:
                        mismatch_dict[target_pr].append(target_link)
                    else:
                        mismatch_dict[target_pr] = [target_link]

        return mismatch_dict

    def visit_pr(self, gh_repo, pr_number):
        if pr_number not in self.prs.keys():
            pr = PullRequest(gh_repo.get_pull(pr_number))
            self.prs[pr_number] = pr

        if pr_number not in self.links.keys():
            self.links[pr_number] = None
            if pr.parse('no-rebase'):
                self.links[pr_number] = -1
            else:
                rebased_links = pr.parse(['rebased'])
                if rebased_links:
                    self.links[pr_number] = rebased_links

        return self.prs[pr_number]

    @staticmethod
    def read_links(links, pr_number):
        to_pattern = r"-to #(\d+)"
        from_pattern = r"-from #(\d+)"

        if not links[pr_number] or links[pr_number] == -1:
            return None, None

        targets = []
        target_links = []
        for link in links[pr_number]:
            match = re.match(to_pattern, link)
            if match:
                targets.append(int(match.group(1)))
                target_links.append('-from #%s' % pr_number)
            else:
                match = re.match(from_pattern, link)
                if match:
                    targets.append(int(match.group(1)))
                    target_links.append('-to #%s' % pr_number)

        return targets, target_links


class CheckStatus(GitHubCommand):
    """
    Check GitHub API status
    """
    NAME = "check-status"

    def __init__(self, sub_parsers):
        super(CheckStatus, self).__init__(sub_parsers)

        self.parser.add_argument(
            "-n", default=0,
            help="Number of status messages to read from history. Default: 0")

    def __call__(self, args):
        super(CheckStatus, self).__call__(args)
        self.login(args)

        api_status = self.gh.get_api_status()

        if args.n > 0:
            if int(args.n) == 1:
                messages = [self.gh.get_last_api_status_message()]
            else:
                messages = self.gh.get_api_status_messages()[0:int(args.n)-1]
                messages.reverse()

            for msg in messages:
                print("%s (%s) %s" % (msg.created_on, msg.status,
                      msg.body))

        if api_status.status != "good":
            raise Stop(1, "GitHub API state is %s as of %s"
                       % (api_status.status, api_status.last_updated))


class AlreadyMerged(GitHubCommand):
    """Detect branches local & remote which are already merged"""

    NAME = "already-merged"

    def __init__(self, sub_parsers):
        super(AlreadyMerged, self).__init__(sub_parsers)

        self.parser.add_argument(
            "target",
            help="Head to check against. E.g. master or origin/master")
        self.parser.add_argument(
            "ref", nargs="*",
            default=["refs/heads", "refs/remotes"],
            help="List of ref patterns to be checked. "
            "E.g. refs/remotes/origin")

    def __call__(self, args):
        super(AlreadyMerged, self).__call__(args)
        self.login(args)

        main_repo = self.gh.git_repo(self.cwd)
        try:
            self.already_merged(args, main_repo)
        finally:
            main_repo.cleanup()

    def already_merged(self, args, main_repo):
        fmt = "%(committerdate:iso8601) %(refname:short)   --- %(subject)"
        cmd = ["git", "for-each-ref", "--sort=committerdate"]
        cmd.append("--format=%s" % fmt)
        cmd += args.ref
        out = main_repo.communicate(*cmd)
        for line in out.split("\n"):
            if line:
                self.go(main_repo, line.rstrip(), args.target)

    def go(self, main_repo, input, target):
        parts = input.split(" ")
        branch = parts[3]
        tip = main_repo.communicate("git", "rev-parse", branch)
        mrg = main_repo.merge_base(branch, target)
        if tip == mrg:
            print input


class CleanSandbox(GitHubCommand):
    """Cleans snoopys-sandbox repo after testing

Removes all branches from your fork of snoopys-sandbox
    """

    NAME = "clean-sandbox"

    def __init__(self, sub_parsers):
        super(CleanSandbox, self).__init__(sub_parsers)

        group = self.parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '-f', '--force', action="store_true",
            help="Perform a clean of all non-master branches")
        group.add_argument(
            '-n', '--dry-run', action="store_true",
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


class ExternalIssues(GitHubCommand):
    """
    Find issues opened by non-org users
    """

    NAME = "external-issues"

    def __init__(self, sub_parsers):
        super(ExternalIssues, self).__init__(sub_parsers)

        self.parser.add_argument(
            'orgs', nargs="+",
            help="organizations that should be checked")

    def __call__(self, args):
        super(ExternalIssues, self).__call__(args)
        self.login(args)
        for org in args.orgs:
            query = "is:open"
            query += " is:issue"
            query += " user:%s" % org
            query += " archived:false"
            org = self.gh.get_organization(org)
            for m in org.get_members():
                query += " -author:%s" % m.login
            issues = []
            for issue in self.gh.search_issues(query):
                issues.append(' - [???] [\\[%s\\] %s ](%s) (%s)' % (
                    issue.repository.name,
                    issue.title,
                    issue.html_url,
                    issue.user.login,
                ))
            print "##", org.login, "(%s)" % len(issues), "##"
            print "\n".join(sorted(issues))


class UnsubscribedRepos(GitHubCommand):
    """
    Find repositories which the current user is not subscribed to
    """

    NAME = "unsubscribed-repos"

    def __init__(self, sub_parsers):
        super(UnsubscribedRepos, self).__init__(sub_parsers)

        self.parser.add_argument(
            'orgs', nargs="+",
            help="organizations that should be checked")

    def __call__(self, args):
        super(UnsubscribedRepos, self).__call__(args)
        self.login(args)
        login = self.gh.get_login()
        for org in args.orgs:
            print org
            org = self.gh.get_organization(org)
            for repo in org.get_repos():
                found = False
                for user in repo.get_subscribers():
                    if user.login == login:
                        found = True
                        break
                if not found:
                    print "\t", repo.name


class Label(GitHubCommand):
    """
    Query/add/remove labels from GitHub issues.
    """

    NAME = "label"

    def __init__(self, sub_parsers):
        super(Label, self).__init__(sub_parsers)

        self.parser.add_argument(
            'pr', nargs="*", type=int,
            help="The number of the pull request to check")

        # Actions
        group = self.parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--add', action='append',
            help='List labels attached to the pull request')
        group.add_argument(
            '--available', action='store_true',
            help='List all available labels for this repository')
        group.add_argument(
            '--list', action='store_true',
            help='List labels attached to the pull request')

    def __call__(self, args):
        super(Label, self).__call__(args)
        self.login(args)

        main_repo = self.gh.git_repo(self.cwd)
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
                pr = PullRequest(main_repo.origin.get_pull(args.pr))
                try:
                    pr.get_issue().add_to_labels(label)
                except github.GithubException, ge:
                    if self.gh.exc_is_not_found(ge):
                        raise Stop(10, "Can't add label: %s" % label.name)
                    raise

    def available(self, args, main_repo):
        if args.pr:
            print >>sys.stderr, "# Ignoring pull requests: %s" % args.pr
        for label in main_repo.origin.get_labels():
            print label.name

    def list(self, args, main_repo):
        for pr_num in args.pr:
            pr = PullRequest(main_repo.origin.get_pull(pr_num))
            for label in pr.get_labels():
                print label


class Rate(GitHubCommand):
    """
    Check current GitHub rate limit for user.
    """

    NAME = "rate"

    def __init__(self, sub_parsers):
        super(Rate, self).__init__(sub_parsers)

    def __call__(self, args):
        super(Rate, self).__call__(args)
        self.login(args)
        core, search = self.gh.get_rate_limits()
        for name, data in (("Core", core), ("Search", search)):
            msg = ("%(name)6s: %(remaining)4s remaining "
                   "from %(limit)4s. Reset at %(time)s")
            print msg % data


class Merge(FilteredPullRequestsCommand):
    """
    Merge Pull Requests opened against a specific base branch.

    Automatically merge all pull requests matching the input filters.
    It assumes that you have checked out the target branch locally and have
    updated any submodules. The SHA1s from the Pull Requests will be merged
    into the current branch. After the Pull Requests are merged, any open Pull
    Requests for each submodule matching the same filters will also be merged
    into the CURRENT submodule SHA1. A final commit will then update the
    submodules.
    """

    NAME = "merge"

    def __init__(self, sub_parsers):
        super(Merge, self).__init__(sub_parsers)
        self._configure_filters()
        self.parser.add_argument(
            '--comment', action='store_true',
            help='Add comment to conflicting PR')
        self.parser.add_argument(
            '--set-commit-status', action='store_true',
            help='Set success/failure status on latest commits in all PRs '
            'in the merge.')
        self.parser.add_argument(
            '--repository-config',
            help='Repository configuration file (YAML)')
        self.add_new_commit_args()

    def get_action(self):
        return "Merging"

    def __call__(self, args):
        super(Merge, self).__call__(args)
        self.login(args)

        self.init_main_repo(args)

        try:
            self.merge(args, self.main_repo)
        finally:
            if not args.info:
                self.log.debug("Cleaning remote branches created for merging")
                self.main_repo.rcleanup()

        if args.push is not None:
            self.push(args, self.main_repo)

    def merge(self, args, main_repo):

        self._parse_filters(args)
        self._log_filters(args.info)

        # Create commit message using command arguments
        commit_args = ["merge", args.base, "-D%s" % args.default]
        if args.include:
            for filt in args.include:
                commit_args.append("-I%s" % filt)
        if args.exclude:
            for filt in args.exclude:
                commit_args.append("-E%s" % filt)
        if args.check_commit_status:
            commit_args.append("-S%s" % args.check_commit_status)

        updated, merge_msg = main_repo.rmerge(
            self.filters, args.info,
            args.comment, commit_id=" ".join(commit_args),
            top_message=args.message,
            update_gitmodules=args.update_gitmodules,
            set_commit_status=args.set_commit_status)

        for line in merge_msg.split("\n"):
            self.log.info(line)
        return updated


class MilestoneCommand(GitRepoCommand):
    """
    Utility functions to manipulate GitHub milestones.
    """

    NAME = "milestone"

    def __init__(self, sub_parsers):
        super(MilestoneCommand, self).__init__(sub_parsers,
                                               set_defaults=False)

        subparsers = self.parser.add_subparsers(title="actions")
        list_parser = subparsers.add_parser('list', help='List milestones')
        list_parser.set_defaults(func=self.list)

        create_parser = subparsers.add_parser(
            'create', help='Create a new milestone')
        self.add_milestone_title(create_parser)
        self.add_milestone_properties(create_parser)
        create_parser.set_defaults(func=self.create)

        update_parser = subparsers.add_parser(
            'update', help='Update an existing milestone')
        self.add_milestone_title(update_parser)
        self.add_milestone_properties(update_parser)
        update_parser.set_defaults(func=self.update)

        delete_parser = subparsers.add_parser(
            'delete', help='Delete a new milestone')
        self.add_milestone_title(delete_parser)
        delete_parser.set_defaults(func=self.delete)

        close_parser = subparsers.add_parser(
            'close', help='Close an existing milestone')
        self.add_milestone_title(close_parser)
        close_parser.set_defaults(func=self.close)

    def add_milestone_title(self, parser):
        parser.add_argument(
            'title', type=str, help='Title of the milestone')

    def add_milestone_properties(self, parser):
        parser.add_argument(
            '--description', type=str, default='',
            help='Description of the milestone')
        parser.add_argument(
            '--date', type=str, default='',
            help='Due date of the milestone formatted as DD-MM-YYYY')

    def init_command(self, args):
        super(MilestoneCommand, self).__call__(args)
        self.login(args)
        return self.init_main_repo(args)

    def cmp_date(self, a, b):
        a = a[0]
        b = b[0]
        if a is None:
            return 1
        elif b is None:
            return -1
        else:
            return cmp(a, b)

    def list(self, args):
        fmt = "%-20s %-20s %-20s %-16s"
        header = fmt % ("NAME", "CREATED", "DUE", "ISSUES (CLOSED)")

        all_repos = self.init_command(args)
        for repo in all_repos:
            self.log.info(str(repo.origin))
            milestones = repo.origin.get_milestones()
            parsed = [(m.due_on, m) for m in milestones]
            parsed.sort(self.cmp_date)
            print header
            for due_on, m in parsed:
                due = due_on is not None and due_on or ""
                print fmt % (m.title, m.created_at, due,
                             "%-3s (%s)" % (m.open_issues, m.closed_issues))

    def check_write_permissions(self, repos):
        permissions = [repo.origin.permissions.push for repo in repos]
        if not all(permissions):
            raise Stop(4, '%s: User %s cannot edit milestones'
                       % (repo.origin, self.gh.get_login()))

    def format_milestone_properties(self, args):

        from datetime import datetime
        kwargs = {}
        if args.description:
            try:
                milestone_description = args.description % args.title
            except TypeError:
                milestone_description = args.description
            kwargs['description'] = milestone_description

        if args.date:
            try:
                kwargs['due_on'] = datetime.strptime(args.date, '%d-%m-%Y')
            except Exception:
                raise Stop(5, 'Date %s should be formatted as DD-MM-YYYY'
                           % args.date)
        return kwargs

    def create(self, args):
        kwargs = self.format_milestone_properties(args)
        all_repos = self.init_command(args)
        self.check_write_permissions(all_repos)
        for repo in all_repos:
            self.log.info(str(repo.origin))
            milestone = repo.origin.create_milestone(args.title, **kwargs)
            self.log.info('Created milestone %s' % milestone.title)

    def update(self, args):
        kwargs = self.format_milestone_properties(args)
        all_repos = self.init_command(args)
        self.check_write_permissions(all_repos)
        for repo in all_repos:
            self.log.info(str(repo.origin))
            milestone = repo.origin.get_milestone(args.title)
            if milestone:
                milestone.edit(milestone.title, **kwargs)
                self.log.info('Updated milestone %s' % args.title)

    def delete(self, args):
        all_repos = self.init_command(args)
        self.check_write_permissions(all_repos)
        for repo in all_repos:
            self.log.info(str(repo.origin))
            milestone = repo.origin.get_milestone(args.title)
            if milestone:
                milestone.delete()
                self.log.info('Deleted milestone %s' % args.title)

    def close(self, args):
        all_repos = self.init_command(args)
        self.check_write_permissions(all_repos)
        for repo in all_repos:
            self.log.info(str(repo.origin))
            milestone = repo.origin.get_milestone(args.title)
            if milestone:
                milestone.edit(milestone.title, state="closed")
                self.log.info('Closed milestone %s' % args.title)


class Rebase(GitRepoCommand):
    """Rebase Pull Requests opened against a specific base branch.

        The workflow currently is:

        1) Find the branch point for the original PR.
        2) Rebase all commits from the branch point to the tip.
        3) Create a branch named "rebase/develop/ORIG_NAME".
        4) If push is set, also push to GH, and switch branches.
        5) If pr is set, push to GH, open a PR, and switch branches.
        6) If delete is not set, omit the deleting of the newbranch.

        If --remote is not set, 'origin' will be used.
    """

    NAME = "rebase"

    def __init__(self, sub_parsers):
        super(Rebase, self).__init__(sub_parsers)

        self.parser.add_argument(
            '--no-fetch', action='store_true',
            help="Do not fetch the origin remote")
        for name, help in (
                ('pr', 'Skip creating a PR.'),
                ('push', 'Skip pushing to GitHub'),
                ('delete', 'Skip deleting local branch')):

            self.parser.add_argument(
                '--no-%s' % name, action='store_false',
                dest=name, default=True, help=help)
        self.parser.add_argument(
            '--continue', action="store_true", dest="_continue",
            help="Continue from a failed rebase")

        self.parser.add_argument(
            'PR', type=int, help="The number of the pull request to rebase")
        self.parser.add_argument(
            'newbase', type=str,
            help="The branch of origin onto which the PR should be rebased")

    def __call__(self, args):
        super(Rebase, self).__call__(args)
        self.login(args)

        args.shallow = True
        args.reset = False
        self.init_main_repo(args)
        if not args.no_fetch:
            self.main_repo.fetch(args.remote)
        try:
            self.rebase(args)
        finally:
            self.main_repo.cleanup()

    def rebase(self, args):

        # If we are pushing the branch somewhere, we likely will
        # be deleting the new one, and so should remember what
        # commit we are on now in order to go back to it.
        try:
            old_branch = self.main_repo.get_current_head()
        except Exception:
            old_branch = self.main_repo.get_current_sha1()

        pr, new_branch = self.local_rebase(args.PR, args.newbase, args.remote,
                                           args._continue)
        if args.push or args.pr:
            try:
                self.push_branch(new_branch)
                if args.pr:
                    self.open_pr(new_branch, args.newbase, pr)
            finally:
                self.main_repo.checkout_branch(old_branch)

            if args.delete:
                self.main_repo.delete_local_branch(new_branch, force=True)

    def local_rebase(self, pr_number, newbase, remote="origin", skip=False):

        # Remote information
        try:
            pr = PullRequest(self.main_repo.origin.get_pull(pr_number))
            self.log.info("PR %g: %s opened by %s against %s",
                          pr_number, pr.title, pr.head.user.name, pr.base.ref)
        except github.GithubException:
            raise Stop(16, 'Cannot find pull request %s' % pr_number)

        pr_head = pr.head.sha
        self.log.info("Head: %s", pr_head[0:6])
        self.log.info("Merged: %s", pr.is_merged())

        # Fail-fast if bad object
        if not self.main_repo.has_local_object(pr_head):
            raise Stop(17, 'Commit %s does not exists in local Git '
                       'repository. Fetch this remote first: %s'
                       % (pr_head, pr.head.user.login))

        # Fail-fast if local branch exist with the target name
        new_branch = "rebased/%s/%s" % (newbase, pr.head.ref)
        if self.main_repo.has_local_branch(new_branch):
            raise Stop(18, 'Branch %s already exists in local Git repository'
                       % new_branch)

        remote_newbase = "%s/%s" % (remote, newbase)
        if not skip:
            branching_sha1 = self.main_repo.find_branching_point(
                pr_head, "%s/%s" % (remote, pr.base.ref))

            try:
                self.main_repo.rebase(remote_newbase, branching_sha1, pr_head)
            except Exception:
                raise Stop(20, self.get_conflict_message(pr_number, newbase))

        # Fail-fast if sha1 is the same as the new base
        if self.main_repo.get_current_sha1() == \
                self.main_repo.get_sha1(remote_newbase):
            raise Stop(22, "No new commits between the rebased branch and %s"
                       % remote_newbase)
        self.main_repo.new_branch(new_branch)
        print >> sys.stderr, "# Created local branch %s" % new_branch

        return pr, new_branch

    def push_branch(self, new_branch):

        user = self.gh.get_login()
        # Fail-fast if remote branch exist with the target name
        if self.main_repo.has_remote_branch(new_branch, remote=user):
            raise Stop(19, 'Branch %s already exists in %s remote'
                       % (new_branch, user))

        remote = "git@github.com:%s/%s.git" % (
            user, self.main_repo.origin.name)
        push_msg = ""
        if user in self.main_repo.list_remotes():
            try:
                self.main_repo.push_branch(new_branch, remote=user)
                push_msg = "# Pushed %s to %s" % (new_branch, user)
            except Exception:
                self.log.info('Could not push to remote %s' % user)

        if not push_msg:
            self.main_repo.push_branch(new_branch, remote=remote)
            push_msg = "# Pushed %s to %s" % (new_branch, remote)
        print >> sys.stderr, push_msg

    def open_pr(self, new_branch, newbase, pr):

        user = self.gh.get_login()
        template_args = {
            "id": pr.number, "base": newbase,
            "title": pr.title, "body": pr.body}
        title = "%(title)s (rebased onto %(base)s)" % template_args
        body = """
This is the same as gh-%(id)s but rebased onto %(base)s.

----

%(body)s

                """ % template_args

        rebased_pr = PullRequest(self.main_repo.origin.open_pr(
            title, body, base=newbase, head="%s:%s" % (user, new_branch)))
        print rebased_pr.html_url

        # Add rebase comments
        pr.create_issue_comment('--rebased-to #%s' % rebased_pr.number)
        rebased_pr.create_issue_comment('--rebased-from #%s' % pr.number)

    def get_conflict_message(self, pr, newbase):
        msg = 'Rebasing failed\nYou are now in detached HEAD mode\n\n'
        msg += 'To keep on rebasing,\n'
        msg += '1) check the output of "git status" and fix the conflicts\n'
        msg += '2) re-add the conflicting files with "git add"\n'
        msg += '3) run "git rebase --continue"\n'
        msg += '4) repeat steps 1-3 until all conflicts are resolved\n'
        msg += '5) run "scc rebase --continue %s %s"\n\n' \
            % (pr, newbase)
        msg += 'To stop rebasing,\n'
        msg += '1) run "git rebase --abort"\n'
        msg += '2) checkout the desired branch, e.g "git checkout master"'
        return msg


class Token(GitHubCommand):
    """Utility functions to manipulate local and remote GitHub tokens"""

    NAME = "token"

    def __init__(self, sub_parsers):
        super(Token, self).__init__(sub_parsers, set_defaults=False)
        # No token args

        token_parsers = self.parser.add_subparsers(title="Subcommands")
        self._configure(token_parsers)

    def _configure(self, sub_parsers):
        help = "Print all known GitHub tokens and users"
        list = sub_parsers.add_parser("list", help=help, description=help)
        list.set_defaults(func=self.list)

        help = """Create a new token and set the value of GitHub token"""
        desc = help + ". See http://developer.github.com/v3/oauth/" \
            "#create-a-new-authorization for more information."
        create = sub_parsers.add_parser("create", help=help, description=desc)
        create.set_defaults(func=self.create)
        create.add_argument(
            '--no-set', action="store_true",
            help="Create the token but do not set it")
        create.add_argument(
            '--scope', '-s', type=str, action='append',
            default=DefaultList(["public_repo"]), choices=self.get_scopes(),
            help="Scopes to use for token creation. Default: ['public_repo']")

        help = "Set token to the specified value"
        set = sub_parsers.add_parser("set", help=help, description=help)
        set.add_argument('value', type=str, help="Value of the token to set")
        set.set_defaults(func=self.set)

        help = "Get the GitHub token"
        get = sub_parsers.add_parser("get", help=help, description=help)
        get.set_defaults(func=self.get)

        for x in (create, set, get):
            self.add_config_file_arguments(x)

    def get_scopes(self):
        """List available scopes for authorization creation"""

        return ['user', 'user:email', 'user:follow', 'public_repo', 'repo',
                'repo:status', 'delete_repo', 'notifications', 'gist']

    def add_config_file_arguments(self, parser):
        parser.add_argument(
            "--local", action="store_true",
            help="Access token only in local repository")
        parser.add_argument(
            "--user", action="store_true",
            help="Access token only in user configuration")

    def list(self, args):
        """List existing GitHub tokens and users"""

        super(Token, self).__call__(args)
        for key in ("github.token", "github.user"):
            for user, local, msg in \
                    ((False, True, "local"), (True, False, "user")):

                rv = git_config(key, user=user, local=local)
                if rv is not None:
                    print "[%s] %s=%s" % (msg, key, rv)

    def create(self, args):
        """Create a new GitHub token"""

        super(Token, self).__call__(args)
        user = git_config("github.user")
        if not user:
            raise Exception("No github.user configured")
        gh = get_github(user)
        user = gh.github.get_user()
        auth = user.create_authorization(args.scope, "scc token")
        print "Created authentification token %s" % auth.token
        if not args.no_set:
            git_config("github.token", user=args.user,
                       local=args.local, value=auth.token)

    def get(self, args):
        """Get the value of the GitHub token"""

        super(Token, self).__call__(args)
        token = git_config("github.token",
                           user=args.user, local=args.local)
        if token:
            print token

    def set(self, args):
        """Set the value of the GitHub token"""

        super(Token, self).__call__(args)
        git_config("github.token", user=args.user,
                   local=args.local, value=args.value)
        return


class TravisMerge(FilteredPullRequestsCommand):
    """
    Update submodules and merge Pull Requests in Travis CI jobs.

    Use the Travis environment variable to read the pull request number. Read
    the base branch using the GitHub API.
    """

    NAME = "travis-merge"

    def __init__(self, sub_parsers):
        super(TravisMerge, self).__init__(sub_parsers)

    def __call__(self, args):
        super(TravisMerge, self).__call__(args)
        args.no_ask = True  # Do not ask for login
        self.login(args)

        # Read pull request number from environment variable
        pr_key = 'TRAVIS_PULL_REQUEST'
        if pr_key in os.environ:
            pr_number = os.environ.get(pr_key)
            if pr_number == 'false':
                raise Stop(0, "Travis job is not a pull request")
        else:
            raise Stop(51, "No %s found. Re-run this command within a Travis"
                       " environment" % pr_key)

        args.reset = False
        self.init_main_repo(args)
        pr = PullRequest(self.main_repo.origin.get_pull(int(pr_number)))

        # Parse comments/description for PRs inclusion in the Travis build
        self._parse_dependencies(pr.get_base(), pr.parse('depends-on'))
        self._log_filters(args.info)

        try:
            updated, merge_msg = self.main_repo.rmerge(self.filters,
                                                       args.info)
            for line in merge_msg.split("\n"):
                self.log.info(line)
        finally:
            if not args.info:
                self.log.debug("Cleaning remote branches created for merging")
                self.main_repo.rcleanup()

    def get_action(self):
        return "Merging"

    def _parse_dependencies(self, base, comments):
        # Create default merge filters using the PR base ref
        self.filters = {}
        self.filters["base"] = base
        self.filters["include"] = {}
        self.filters["exclude"] = {}

        for comment in comments:
            found = self._parse_hash("include", comment.strip())

            if not found:
                self._parse_url("include", comment.strip())


class UpdateSubmodules(GitRepoCommand):
    """
    Similar to the 'merge' command, but only updates submodule pointers.
    """

    NAME = "update-submodules"

    def __init__(self, sub_parsers):
        super(UpdateSubmodules, self).__init__(sub_parsers)

        self.parser.add_argument(
            '--no-fetch', action='store_true',
            help="Fetch the latest target branch for all repos")
        self.parser.add_argument(
            '--no-pr', action='store_false',
            dest='pr', default=True, help='Skip creating a PR.')
        self.add_new_commit_args()

    def __call__(self, args):
        super(UpdateSubmodules, self).__call__(args)
        self.login(args)

        self.init_main_repo(args)

        try:
            if args.message is None:
                args.message = "Update %s submodules" % args.base
            self.log.info(args.message)
            updated, merge_msg = self.submodules(args, self.main_repo)

            if updated and args.push is not None:
                self.push(args, self.main_repo)

                if args.pr:

                    pr = self.get_open_pr(args)
                    body = merge_msg
                    if IS_JENKINS_JOB:
                        body += "\n\nGenerated by build [%s#%s](%s)." % \
                            (JOB_NAME, BUILD_NUMBER, BUILD_URL)
                    body += "\n\n----\n--no-rebase"

                    if pr is None:
                        title = args.message
                        user = self.gh.get_login()
                        pr = self.main_repo.origin.open_pr(
                            title, body,
                            base=args.base,
                            head="%s:%s" % (user, args.push))
                        self.log.info("New PR created: %s", pr.html_url)
                    else:
                        pr.edit_body(body)
                        self.log.info("PR %s updated", pr.get_number())
        finally:
            self.main_repo.rcleanup()

    def submodules(self, args, main_repo):
        for submodule in main_repo.submodules:
            submodule.cd(submodule.path)
            if not args.no_fetch:
                submodule.fetch(args.remote)
            # submodule.checkout_branch("%s/%s" % (args.remote, args.base))

        # Create commit message using command arguments
        self.filters = {}
        self.filters["base"] = args.base
        self.filters["include"] = {}
        self.filters["exclude"] = {}

        updated, merge_msg = main_repo.rmerge(
            self.filters,
            top_message=args.message,
            update_gitmodules=args.update_gitmodules,
            allow_empty=False)
        for line in merge_msg.split("\n"):
            self.log.info(line)
        return updated, merge_msg


class SetCommitStatus(FilteredPullRequestsCommand):
    """
    Set commit status on all pull requests with any of the given labels.
    It assumes that you have checked out the target branch locally and
    have updated any submodules.
    """

    NAME = "set-commit-status"

    def __init__(self, sub_parsers):
        super(SetCommitStatus, self).__init__(sub_parsers)
        self._configure_filters()
        self.parser.add_argument(
            '--status', '-s', type=str, required=True,
            choices=["success", "failure", "error", "pending"],
            help='Commit status.')
        self.parser.add_argument(
            '--message', '-m', required=True,
            help='Message to use for the commit status.')
        self.parser.add_argument(
            '--url', '-u',
            help='URL to use for the commit status.')
        self.parser.add_argument('base', type=str)

    def __call__(self, args):
        super(SetCommitStatus, self).__call__(args)
        self.login(args)
        self.init_main_repo(args)
        self.setCommitStatus(args, self.main_repo)

    def setCommitStatus(self, args, main_repo):
        self._parse_filters(args)
        self._log_filters(args.info)
        msg = main_repo.rset_commit_status(
            self.filters, args.status, args.message,
            args.url, info=args.info)
        for line in msg.split("\n"):
            self.log.info(line)

    def get_action(self):
        return "Setting commit status on"


class _TagCommands(GitRepoCommand):

    def __init__(self, sub_parsers):
        super(_TagCommands, self).__init__(sub_parsers)

        self.parser.add_argument(
            'version', type=str,
            help='Version number to use to construct the tag')

    def __call__(self, args):
        super(_TagCommands, self).__call__(args)

        if not self.check_version_format(args):
            raise Stop(23, '%s is not a valid version number. '
                       'See http://semver.org for more information.'
                       % args.version)

        self.login(args)
        self.init_main_repo(args)
        # Subclasses take over here

    def check_version_format(self, args):
        """Check format of version number"""

        pattern = '^[0-9]+[\.][0-9]+[\.][0-9]+(\-.+)*$'
        return re.match(pattern, args.version) is not None


class DeleteTags(_TagCommands):
    """
    Remove tags recursively across submodules.
    """

    NAME = "rm-tags"

    def __call__(self, args):
        super(DeleteTags, self).__call__(args)
        if args.remote in ("origin", "upstream"):
            raise Stop(2, ('"origin" and "upstream" are disabled. '
                           'Create a secondary remote for removing tags.'))
        self.main_repo.rtagdelete(args.version)


class TagRelease(_TagCommands):
    """
    Tag a release recursively across submodules.
    """

    NAME = "tag-release"

    def __init__(self, sub_parsers):
        super(TagRelease, self).__init__(sub_parsers)

        self.parser.add_argument(
            '--message', '-m', type=str,
            help='Tag message')
        self.parser.add_argument(
            '--push', action='store_true',
            help='Push new tag(s) to GitHub')
        self.parser.add_argument(
            '--sign', '-s', action='store_true',
            help='Annotate and GPG-sign the tag(s)')
        self.parser.add_argument(
            '--prefix', type=str,
            help='Custom prefix to apply in front of the tag.')

    def __call__(self, args):
        super(TagRelease, self).__call__(args)

        if args.message is None:
            args.message = 'Tag version %s' % args.version

        msg = self.main_repo.rtag(args.version, message=args.message,
                                  sign=args.sign, prefix=args.prefix)

        for line in msg.split("\n"):
            self.log.info(line)

        if args.push:
            user = self.gh.get_login()
            remote = "git@github.com:%s/" % (user) + "%s.git"
            self.main_repo.rpush('--tags', remote, force=True)
