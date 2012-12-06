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


FUNCTIONALITY
-------------

    merge:

Automatically merge all pull requests with any of the given labels.
It assumes that you have checked out the target branch locally and
have updated any submodules. The SHA1s from the PRs will be merged
into the current branch. AFTER the PRs are merged, any open PRs for
each submodule with the same tags will also be merged into the
CURRENT submodule sha1. A final commit will then update the submodules.

    rebase:

TBD

"""

import os
import github  # PyGithub
import subprocess
import logging
import threading
import argparse
import difflib

fmt = """%(asctime)s %(levelname)-5.5s %(message)s"""
logging.basicConfig(level=10, format=fmt)

log = logging.getLogger("scc")
dbg = log.debug
logging.getLogger('github').setLevel(logging.INFO)
log.setLevel(logging.DEBUG)

def get_token():
    """
    Get the Github API token.
    """
    try:
        p = call("git", "config", "--get",
            "github.token", stdout = subprocess.PIPE).communicate()[0]
        token = p.split("\n")[0]
    except Exception:
        token = None
    return token

def get_github(login_or_token = None, password = None):
    """
    Use the global Github manager to retrieve or create a Github instance.
    Github instances can be constructed using an OAuth2 token, a Github login
    and password or anonymously.
    """
    return gh_manager.get_instance(login_or_token, password)

def get_github_repo(username, reponame, *args):
    """
    Use the global Github repository manager to retrieve or create a Github
    repository. Github repository are constructed by passing the user and the
    repository name as in https://github.com/username/reponame.git
    """
    return gh_repo_manager.get_instance((username, reponame), *args)

def get_git_repo(path, *args):
    """
    Use the global Git repository manager to retrieve or create a local Git
    repository. Git repository instances are constructed by passing the path
    of the directory containing the repository.
    """
    return git_manager.get_instance(os.path.abspath(path), *args)

class GHWrapper(object):
    FACTORY = github.Github

    def __init__(self, login_or_token = None, password = None):
        if password is not None:
            self.create_instance(login_or_token, password)
        elif login_or_token is not None:
            try:
                self.create_instance(login_or_token)
            except github.GithubException:
                password = self.ask_password(login_or_token)
                if password is not  None:
                    self.create_instance(login_or_token, password)
        else:
            self.create_instance()

    def get_login(self):
        return self.github.get_user().login

    def create_instance(self, *args):
        self.github = self.FACTORY(*args)

    def __getattr__(self, key):
        dbg("github.%s", key)
        return getattr(self.github, key)

    def get_rate_limiting(self):
        requests = self.github.rate_limiting
        dbg("Remaining requests: %s out of %s", requests[0], requests[1])

    def ask_password(self, login):
        """
        Reads from standard in.
        """
        try:
            while True:
                rv = raw_input("Enter password for user %s:" % login)
                if not rv:
                    print "Input required"
                    continue
                return rv
        except KeyboardInterrupt:
            raise Exception("Cancelled")

class Manager(object):
    """
    Manage object creation/retrieval using a dictionary/identification keys.
    """
    def __init__(self):
        self.dictionary = {}
        self.current_key = None

    def get_instance(self, key = None, *args):
        """
        Get instance of object identified by a given key. If the dictionary
        has the input key, returns the corresponding value else instantiate 
        the object and add to the dictionary.
        """
        obj = None
        if self.dictionary.has_key(key):
            obj = self.dictionary[key]
            self.retrieve_message(obj, key)
        else:
            obj = self.create_instance(key, *args)
            self.create_message(obj, key)
            self.dictionary[key] = obj
        self.current_key = key
        return obj

    def get_current(self):
        """
        Get current object in the manager, i.e. the object associated with
        the current_key.
        """
        if self.dictionary.has_key(self.current_key):
            obj = self.dictionary[self.current_key]
            return obj
        else:
            return None

    def create_instance(self, key, *args):
        pass

    def create_message(self, key, *args):
        pass

    def retrieve_message(self, key, *args):
        pass

class GHManager(Manager):
    FACTORY = GHWrapper

    def create_instance(self, login_or_token = None, password = None):
        gh = self.FACTORY(login_or_token, password)
        return gh

    def retrieve_message(self, gh, login_or_token):
        if login_or_token:
            dbg("Retrieve Github instance identified as %s",
                gh.get_login())
        else:
            dbg("Retrieve anonymous Github instance")

    def create_message(self, gh, login_or_token):
        if login_or_token:
            dbg("Create Github instance identified as %s",
                gh.get_login())
        else:
            dbg("Create anonymous Github instance")

gh_manager = GHManager()
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
        """Register the Pull Request and its corresponding Issue"""
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

class GitHubRepository(object):

    def __init__(self, user_name, repo_name, gh = None):
        if not gh:
            gh = gh_manager.get_current()
            if not gh:
                raise Exception("No Github instance created in the Github manager")

        try:
            self.repo = gh.get_user(user_name).get_repo(repo_name)
            if self.repo.organization:
                self.org = gh.get_organization(self.repo.organization.login)
            else:
                self.org = None
        except:
            log.error("Failed to find %s/%s", user_name, repo_name, exc_info=1)
            raise Exception("Did not find %s/%s")

    def __getattr__(self, key):
        return getattr(self.repo, key)

    def get_owner(self):
        return self.owner.login

    def is_whitelisted(self, user):
        if self.org:
            status = self.org.has_in_public_members(user)
        else:
            status = False
        return status

class GHRepoManager(Manager):
    """Manager of Github repositories"""
    FACTORY = GitHubRepository

    def create_instance(self, key, *args):
        repo = self.FACTORY(key[0], key[1], *args)
        return repo

    def retrieve_message(self, repo, *args):
        dbg("Retrieve Github repository: %s/%s", repo.get_owner(), repo.name)

    def create_message(self, repo, *args):
        dbg("Register Github repository %s/%s", repo.get_owner(), repo.name)

gh_repo_manager = GHRepoManager()

class GitRepository(object):

    def __init__(self, path, reset=False):
        """
        Register the git repository path, return the current status and
        register the Github origin remote.
        """

        log.info("")
        self.path =  os.path.abspath(path)

        if reset:
            self.reset()
        self.get_status()

        self.reset = reset

        # Register the origin remote
        [user_name, repo_name] = self.get_remote_info("origin")
        self.origin = get_github_repo(user_name, repo_name)
        self.candidate_pulls = []

    def find_candidates(self, filters):
        """Find candidate Pull Requests for merging."""
        dbg("## PRs found:")
        directories_log = None

        # Loop over pull requests opened aainst base
        pulls = [pull for pull in self.origin.get_pulls() if (pull.base.ref == filters["base"])]
        for pull in pulls:
            pullrequest = PullRequest(self.origin, pull)
            labels = [x.lower() for x in pullrequest.get_labels()]

            found = self.origin.is_whitelisted(pullrequest.get_user())

            if not found:
                if filters["include"]:
                    whitelist = [filt for filt in filters["include"] if filt.lower() in labels]
                    if whitelist:
                        dbg("# ... Include %s", whitelist)
                        found = True

            if not found:
                continue

            # Exclude PRs if exclude labels are input
            if filters["exclude"]:
                blacklist = [filt for filt in filters["exclude"] if filt.lower() in labels]
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

    def get_status(self):
        """Return the status of the git repository including its submodules"""
        cd(self.path)
        dbg("Check current status")
        call("git", "log", "--oneline", "-n", "1", "HEAD")
        call("git", "submodule", "status")

    def reset(self):
        """Reset the git repository to its HEAD"""
        cd(self.path)
        dbg("Resetting...")
        call("git", "reset", "--hard", "HEAD")

    def info(self):
        """List the candidate Pull Request to be merged"""
        for pullrequest in self.candidate_pulls:
            print "# %s" % " ".join(pullrequest.get_labels())
            print "%s %s by %s for \t\t[???]" % \
                (pullrequest.pr.issue_url, pullrequest.get_title(), pullrequest.get_login())
            print

    def fast_forward(self, base, remote = "origin"):
        """Execute merge --ff-only against the current base"""
        dbg("## Merging base to ensure closed PRs are included.")
        p = subprocess.Popen(["git", "merge", "--ff-only", "%s/%s" % (remote, base)], stdout = subprocess.PIPE).communicate()[0]
        log.info(p.rstrip("/n"))

    def get_remote_info(self, remote_name):
        """
        Return user and repository name of the specified remote.

        Origin remote must be on Github, i.e. of type
        *github/user/repository.git
        """
        
        cd(self.path)
        originurl = call("git", "config", "--get", \
            "remote." + remote_name + ".url", stdout = subprocess.PIPE, \
            stderr = subprocess.PIPE).communicate()[0]

        # Read user from origin URL
        dirname = os.path.dirname(originurl)
        assert "github" in dirname, 'Origin URL %s is not on GitHub' % dirname
        user = os.path.basename(dirname)
        if ":" in dirname:
            user = user.split(":")[-1]

        # Read repository from origin URL
        basename = os.path.basename(originurl)
        repo = os.path.splitext(basename)[0]
        log.info("Repository: %s/%s", user, repo)
        return [user , repo]

    def merge(self, comment=False, commit_id = "merge"):
        """Merge candidate pull requests."""
        dbg("## Unique users: %s", self.unique_logins())
        for key, url in self.remotes().items():
            call("git", "remote", "add", key, url)
            call("git", "fetch", key)

        conflicting_pulls = []
        merged_pulls = []

        for pullrequest in self.candidate_pulls:
            premerge_sha, e = call("git", "rev-parse", "HEAD", stdout = subprocess.PIPE).communicate()
            premerge_sha = premerge_sha.rstrip("\n")

            try:
                call("git", "merge", "--no-ff", "-m", \
                        "%s: PR %s (%s)" % (commit_id, pullrequest.get_number(), pullrequest.get_title()), pullrequest.get_sha())
                merged_pulls.append(pullrequest)
            except:
                call("git", "reset", "--hard", "%s" % premerge_sha)
                conflicting_pulls.append(pullrequest)

                msg = "Conflicting PR."
                job_dict = ["JOB_NAME", "BUILD_NUMBER", "BUILD_URL"]
                if all([key in os.environ for key in job_dict]):
                    job_values = [os.environ.get(key) for key in job_dict]
                    msg += " Removed from build [%s#%s](%s). See the [console output](%s) for more details." % \
                        (job_values[0], job_values[1], job_values[2], job_values[2] +"/consoleText")
                dbg(msg)

                if comment and get_token():
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

    def submodules(self, filters, info=False, comment=False, commit_id = "merge"):
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
                submodule_repo = get_git_repo(directory, self.reset)
                if info:
                    submodule_repo.info()
                else:
                    submodule_repo.fast_forward(filters["base"])
                    submodule_repo.find_candidates(filters)
                    submodule_repo.merge(comment)
                submodule_repo.submodules(info)
            finally:
                try:
                    if submodule_repo:
                        submodule_repo.cleanup()
                finally:
                    cd(cwd)

        call("git", "commit", "--allow-empty", "-a", "-n", "-m", \
                "%s: Update all modules w/o hooks" % commit_id)

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
            if self.origin.private:
                url = "git@github.com:%s/%s.git"  % (user, self.origin.name)
            else:
                url = "git://github.com/%s/%s.git" % (user, self.origin.name)
            remotes[key] = url
        return remotes

    def cleanup(self):
        """Remove remote branches created for merging."""
        for key in self.remotes().keys():
            try:
                call("git", "remote", "rm", key)
            except Exception:
                log.error("Failed to remove", key, exc_info=1)

class GitRepoManager(Manager):
    """Manager of local git repositories"""
    FACTORY = GitRepository

    def create_instance(self, path, *args):
        repo = self.FACTORY(path, *args)
        return repo

    def retrieve_message(self, repo, *args):
        dbg("Retrieve Git repository: %s", repo.path)

    def create_message(self, repo, *args):
        dbg("Register Git repository %s", repo.path)

git_manager = GitRepoManager()

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
    if not os.path.abspath(os.getcwd()) == os.path.abspath(directory):
        dbg("cd %s", directory)
        os.chdir(directory)


class Command(object):
    pass


class Merge(Command):

    def __init__(self, sub_parsers):

        merge_help = 'Merge Pull Requests opened against a specific base branch.'
        merge_parser = sub_parsers.add_parser("merge",
                help=merge_help, description=merge_help)
        merge_parser.set_defaults(func=self.__call__)

        merge_parser.add_argument('--reset', action='store_true',
            help='Reset the current branch to its HEAD')
        merge_parser.add_argument('--info', action='store_true',
            help='Display merge candidates but do not merge them')
        merge_parser.add_argument('--comment', action='store_true',
            help='Add comment to conflicting PR')
        merge_parser.add_argument('base', type=str)
        merge_parser.add_argument('--include', nargs="*",
            help='PR labels to include in the merge')
        merge_parser.add_argument('--exclude', nargs="*",
            help='PR labels to exclude from the merge')
        merge_parser.add_argument('--buildnumber', type=int, default=None,
            help='The build number to use to push to team.git')

    def __call__(self, args):
        gh = get_github(get_token())
        log.info("Merging PR based on: %s", args.base)
        log.info("Excluding PR labelled as: %s", args.exclude)
        log.info("Including PR labelled as: %s", args.include)

        filters = {}
        filters["base"] = args.base
        filters["include"] = args.include
        filters["exclude"] = args.exclude
        cwd = os.path.abspath(os.getcwd())
        main_repo = get_git_repo(cwd, args.reset)
        main_repo.find_candidates(filters)

        def commit_id(filters):
            """
            Return commit identifier generated from base branch, include and
            exclude labels.
            """
            commit_id = "merge"+"_into_"+filters["base"]
            if filters["include"]:
                commit_id += "+" + "+".join(filters["include"])
            if filters["exclude"]:
                commit_id += "-" + "-".join(filters["exclude"])
            return commit_id

        try:
            if not args.info:
                main_repo.merge(args.comment, commit_id = commit_id(filters))
            main_repo.submodules(filters, args.info, args.comment, commit_id = commit_id(filters))  # Recursive

            if args.buildnumber:
                newbranch = "HEAD:%s/%g" % (args.base, args.build_number)
                call("git", "push", "team", newbranch)
        finally:
            main_repo.cleanup()


class Rebase(Command):

    def __init__(self, sub_parsers):
        rebase_help = 'Rebase Pull Requests opened against a specific base branch.'
        rebase_parser = sub_parsers.add_parser("rebase",
                help=rebase_help, description=rebase_help)
        rebase_parser.set_defaults(func=self.__call__)

        rebase_parser.add_argument('PR', type=int, help="The number of the pull request to rebase")
        rebase_parser.add_argument('newbase', type=str, help="The branch of origin onto which the PR should be rebased")

    def __call__(self, args):
        gh = get_github(get_token())
        cwd = os.path.abspath(os.getcwd())
        main_repo = get_git_repo(cwd, False)

        try:
            pr = main_repo.origin.get_pull(args.PR)
            log.info("PR %g: %s opened by %s against %s", args.PR, pr.title, pr.head.user.name, pr.base.ref)
            pr_head = pr.head.sha
            log.info("Head: %s", pr_head[0:6])
            log.info("Merged: %s", pr.is_merged())
        except:
            log.error("Failed to find PR %g", args.PR, exc_info=1)

        branching_sha1 = self.findBranchingPoint(pr_head, "origin/"+pr.base.ref)
        self.rebase(args.newbase, branching_sha1[0:6], pr_head)

    def rebase(self, newbase, upstream, sha1):
        command = ["git", "rebase", "--onto", \
                "origin/%s" % newbase, "%s" % upstream, "%s" % sha1]
        dbg("Calling '%s'" % " ".join(command))
        p = subprocess.Popen(command)
        rc = p.wait()
        if rc:
            raise Exception("rc=%s" % rc)

    def getRevList(self, commit):
        revlist_cmd = lambda x: ["git","rev-list","--first-parent","%s" % x]
        p = subprocess.Popen(revlist_cmd(commit), stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        dbg("Calling '%s'" % " ".join(revlist_cmd(commit)))
        (revlist, stderr) = p.communicate('')

        if stderr or p.returncode:
            print "Error output was:\n%s" % stderr
            print "Output was:\n%s" % stdout
            return False

        return revlist.splitlines()

    def findBranchingPoint(self, topic_branch, main_branch):
        # See http://stackoverflow.com/questions/1527234/finding-a-branch-point-with-git

        topic_revlist = self.getRevList(topic_branch)
        main_revlist = self.getRevList(main_branch)

        # Compare sequences
        s = difflib.SequenceMatcher(None, topic_revlist, main_revlist)
        matching_block = s.get_matching_blocks()
        if matching_block[0].size == 0:
            raise Exception("No matching block found")

        sha1 = main_revlist[matching_block[0].b]
        log.info("Branching SHA1: %s" % sha1[0:6])
        return sha1


if __name__ == "__main__":

    scc_parser = argparse.ArgumentParser(description='Snoopy Crime Cop Script')
    sub_parsers = scc_parser.add_subparsers(title="Subcommands")

    for MyCommand in globals().values():
        if not isinstance(MyCommand, type): continue
        if not issubclass(MyCommand, Command): continue
        if Command == MyCommand: continue
        MyCommand(sub_parsers)

    ns = scc_parser.parse_args()
    ns.func(ns)
