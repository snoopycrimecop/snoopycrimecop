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

import pytest
import re

from yaclifw.framework import main, Stop
from scc.git import Merge, EMPTY_MSG
from Sandbox import SandboxTest


class MergeTest(SandboxTest):

    def setup_method(self, method):

        super(MergeTest, self).setup_method(method)
        self.init_submodules()
        self.base = "dev_4_4"
        self.merge_branch = "merge/dev_4_4/test"
        self.branch = self.fake_branch(head=self.base)
        self.sha = self.sandbox.get_sha1(self.branch)
        self.sandbox.checkout_branch(self.base)

    def isMerged(self, ref='HEAD'):
        revlist = self.sandbox.communicate("git", "rev-list", ref)
        return self.sha in revlist.splitlines()

    def teardown_method(self, method):
        # Clean the initial branch. This will close the inital PRs
        self.sandbox.push_branch(":%s" % self.branch, remote=self.user)
        super(MergeTest, self).teardown_method(method)

    def merge(self, *args):
        self.sandbox.checkout_branch(self.origin_remote + "/" + self.base)
        args = ["merge", "--no-ask", self.base] + list(args)
        main("scc", args=args, items=[(Merge.NAME, Merge)])


class TestMergePullRequest(MergeTest):

    def setup_method(self, method):

        super(TestMergePullRequest, self).setup_method(method)
        self.pr = self.open_pr(self.branch, self.base)
        self.sandbox.checkout_branch(self.base)
        assert not self.isMerged()

    def create_status(self, state):
        """Create status on the head repository of the Pull Request"""
        from github.GithubObject import NotSet
        commit = self.pr.head.repo.get_commit(self.pr.head.sha)
        commit.create_status(
            state, NotSet, state[0].upper() + state[1:] + " state test")
        assert commit.get_statuses()[0].state == state

    def testMerge(self):

        self.merge()
        assert self.isMerged()

    def testMergeInfo(self):

        self.merge("--info")
        assert not self.isMerged()

    def testShallowMerge(self):

        pre_merge = self.sandbox.communicate("git", "submodule", "status")
        self.merge("--shallow")
        assert self.isMerged()
        post_merge = self.sandbox.communicate("git", "submodule", "status")
        assert pre_merge == post_merge

    def testMergePush(self):

        self.merge("--push", self.merge_branch)
        self.sandbox.fetch(self.user)
        assert self.isMerged("%s/%s" % (self.user, self.merge_branch))
        self.sandbox.push_branch(":%s" % self.merge_branch, remote=self.user)

    def testRemote(self):

        self.rename_origin_remote("gh")

        # scc merge without --remote should fail
        with pytest.raises(Stop):
            self.merge()

        # scc merge with --remote setup should pass
        self.merge("--remote", self.origin_remote)
        assert self.isMerged()

    @pytest.mark.parametrize('status', ['none', 'no-error', 'success-only'])
    def testStatus(self, status):

        # no status
        self.merge("-S", "%s" % status)
        assert self.isMerged() is (status != "success-only")

        # pending state
        self.create_status("pending")
        self.merge("-S", "%s" % status)
        assert self.isMerged() is (status != "success-only")

        # error state
        self.create_status("error")
        self.merge("-S", "%s" % status)
        assert self.isMerged() is (status == "none")

        # failure state
        self.create_status("failure")
        self.merge("-S", "%s" % status)
        assert self.isMerged() is (status == "none")

        # success state
        self.create_status("success")
        self.merge("-S", "%s" % status)
        assert self.isMerged()

    def testExcludeComment(self):

        self.pr.create_issue_comment('--exclude')
        self.merge()
        assert not self.isMerged()

    def testIncludeComment(self):

        self.pr.create_issue_comment('--foo')
        self.merge()
        assert not self.isMerged()
        self.merge('-Dnone','-Ifoo')
        assert self.isMerged()

    def testExcludeDescription(self):

        self.pr.edit(body=self.pr.body+'\n\n----\n--exclude')
        self.merge()
        assert not self.isMerged()

    def testEmptyDescription(self):

        self.pr.edit(state="closed")
        self.pr = self.open_pr(self.branch, self.base, description="")
        self.merge('--comment')
        assert self.isMerged()
        issue = self.sandbox.origin.get_issue(self.pr.number)
        assert issue.comments == 1
        comments = issue.get_comments()
        assert comments[0].body == EMPTY_MSG

    def testListMergedFiles(self):
        assert self.sandbox.list_merged_files(self.sha) == set([self.branch])

    def testListUpstreamChanges(self):
        assert self.sandbox.list_upstream_changes(self.sha) == set()
        upstream = self.fake_branch(head=self.base)
        assert self.sandbox.list_upstream_changes(self.sha, upstream) == set(
            [upstream])


class TestMergeBranch(MergeTest):

    def setup_method(self, method):

        super(TestMergeBranch, self).setup_method(method)
        self.push_branch(self.branch)
        self.merge_args = ["-I", "%s/%s:%s" % (
            self.user, self.sandbox.origin.name, self.branch)]

    def testMergeBranch(self):
        self.merge(*self.merge_args)
        assert self.isMerged()

    def testMergeBranchInfo(self):
        self.merge(*(self.merge_args + ['--info']))
        assert not self.isMerged()


class TestMergeConflicting(SandboxTest):

    def setup_method(self, method):
        super(TestMergeConflicting, self).setup_method(method)
        self.init_submodules()
        self.base = "dev_4_4"

        commits1 = [
            ('merge.txt', '1\n2\n3\n4\n5\n'),
            ('conflict.txt', 'A\n'),
        ]
        commits2 = [
            ('merge.txt', '1\n2\n3\n4\n5\n'),
            ('conflict.txt', 'B\n'),
        ]

        self.branch1 = self.fake_branch(head=self.base, commits=commits1)
        self.branch2 = self.fake_branch(head=self.base, commits=commits2)
        self.pr1 = self.open_pr(self.branch1, self.base)
        self.pr2 = self.open_pr(self.branch2, self.base)
        self.sha1 = self.sandbox.get_sha1(self.branch1)
        self.sha2 = self.sandbox.get_sha1(self.branch2)

        self.sandbox.checkout_branch(self.base)
        assert not self.isMerged(self.sha1)
        assert not self.isMerged(self.sha2)

    def isMerged(self, sha, ref='HEAD'):
        revlist = self.sandbox.communicate("git", "rev-list", ref)
        return sha in revlist.splitlines()

    def stripLastComment(self, pr):
        """
        Remove whitespace and leading dashes from the last comment
        """
        comment = None
        for comment in pr.get_issue_comments():
            pass
        if not comment:
            return []
        lines = [re.sub(r'[\s-]*(.*)\s*', r'\1', line)
                 for line in comment.body.splitlines()]
        return lines

    def merge(self, *args):
        self.sandbox.checkout_branch(self.origin_remote + "/" + self.base)
        args = ["merge", "--no-ask", self.base] + list(args)
        main("scc", args=args, items=[(Merge.NAME, Merge)])

    def testMerge(self):
        self.merge("--comment")
        c1 = self.stripLastComment(self.pr1)
        c2 = self.stripLastComment(self.pr2)

        assert self.isMerged(self.sha1)
        assert not self.isMerged(self.sha2)
        assert c1 == []
        assert c2[-2].startswith('PR #')
        assert c2[-1] == 'conflict.txt'

    def teardown_method(self, method):
        self.sandbox.push_branch(":%s" % self.branch1, remote=self.user)
        self.sandbox.push_branch(":%s" % self.branch2, remote=self.user)
        super(TestMergeConflicting, self).teardown_method(method)
