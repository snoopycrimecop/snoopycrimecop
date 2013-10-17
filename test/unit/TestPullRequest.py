#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2013 University of Dundee & Open Microscopy Environment
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

import scc.git

from github.AuthenticatedUser import AuthenticatedUser
from github.Commit import Commit
from github.CommitStatus import CommitStatus
from github.GithubObject import NotSet
from github.Issue import Issue
from github.IssueComment import IssueComment
from github.Label import Label
from github.PullRequest import PullRequest
from github.PullRequestPart import PullRequestPart
from github.Repository import Repository
from mox import MoxTestBase


class TestPullRequest(MoxTestBase):

    def setUp(self):
        super(TestPullRequest, self).setUp()
        # Create base of PullRequest
        self.base_user = self.mox.CreateMock(AuthenticatedUser)
        self.base_repo = self.mox.CreateMock(Repository)
        self.base = self.mox.CreateMock(PullRequestPart)
        self.base.repo = self.base_repo
        self.base.user = self.base_user

        # Create head of PullRequest
        self.head_user = self.mox.CreateMock(AuthenticatedUser)
        self.head_repo = self.mox.CreateMock(Repository)
        self.head = self.mox.CreateMock(PullRequestPart)
        self.head.repo = self.head_repo
        self.head.user = self.head_user

        # Create owner of PullRequest
        self.pr_user = self.mox.CreateMock(AuthenticatedUser)

        # Create PullRequest and set user, base, head and properties
        self.pull = self.mox.CreateMock(PullRequest)
        self.pull.user = self.pr_user
        self.pull.base = self.base
        self.pull.head = self.head

        # Initialize
        self.comments = []
        self.labels = []
        self.statuses = []
        self.pr = scc.git.PullRequest(self.pull)

    def create_issue(self):
        self.pull.number = 0
        self.issue = self.mox.CreateMock(Issue)
        self.base_repo.get_issue(self.pull.number).AndReturn(self.issue)

    def create_label(self, name="mock-label"):
        label = self.mox.CreateMock(Label)
        label.name = name
        self.labels.append(label)

    def create_comment(self, body="mock-comment"):
        comment = self.mox.CreateMock(IssueComment)
        comment.body = body
        self.comments.append(comment)

    def create_commit(self, repo):
        self.pull.head.sha = "mock-sha"
        self.commit = self.mox.CreateMock(Commit)
        repo.get_commit("mock-sha").AndReturn(self.commit)

    def create_commit_status(self, state="pending"):
        status = self.mox.CreateMock(CommitStatus)
        status.state = state
        self.statuses.append(status)

    def test_get_user(self):
        self.assertEquals(self.pr.get_user(), self.pr_user)

    def test_get_title(self):
        self.pull.title = "mock-title"
        self.assertEquals(self.pr.get_title(), self.pull.title)

    def test_repr(self):
        self.pull.number = 0
        self.pr_user.login = "mock-user"
        self.pull.title = "mock-title"
        repr_str = "  # PR %s %s '%s'" % (
            self.pull.number, self.pr_user.login, self.pull.title)
        self.assertEquals(str(self.pr), repr_str)

    def test_edit_body(self):
        self.pull.edit("new_body")
        self.mox.ReplayAll()
        self.pr.edit("new_body")

    def test_get_login(self):
        self.pr_user.login = "mock-user"
        self.assertEquals(self.pr.get_login(), self.pr_user.login)

    def test_get_number(self):
        self.pull.number = 0
        self.assertEquals(self.pr.get_number(), self.pull.number)

    def test_get_issue(self):
        self.create_issue()
        self.mox.ReplayAll()
        self.assertEquals(self.pr.get_issue(), self.issue)

    def test_get_base(self):
        self.base.ref = "mock-ref"
        self.assertEquals(self.pr.get_base(), self.base.ref)

    # Label tests
    def test_get_labels_none(self):
        self.create_issue()
        self.issue.labels = self.labels
        self.mox.ReplayAll()
        self.assertEquals(self.pr.get_labels(), [])

    def test_get_labels_single(self):
        self.create_issue()
        self.create_label()
        self.issue.labels = self.labels
        self.mox.ReplayAll()
        self.assertEquals(self.pr.get_labels(), ["mock-label"])

    def test_get_labels_multiple(self):
        self.create_issue()
        self.create_label()
        self.create_label()
        self.issue.labels = self.labels
        self.mox.ReplayAll()
        self.assertEquals(self.pr.get_labels(), ["mock-label", "mock-label"])

    # Comment tests
    def test_get_comments_none(self):
        self.create_issue()
        self.issue.comments = 0
        self.mox.ReplayAll()
        self.assertEquals(self.pr.get_comments(), [])

    def test_get_comments_single(self):
        self.create_issue()
        self.create_comment()
        self.issue.comments = 1
        self.base_repo.get_issue(self.pull.number).AndReturn(self.issue)
        self.issue.get_comments().AndReturn(self.comments)
        self.mox.ReplayAll()
        self.assertEquals(self.pr.get_comments(), ["mock-comment"])

    def test_get_comments_multiple(self):
        self.create_issue()
        self.create_comment("mock-comment")
        self.create_comment("mock-comment")
        self.issue.comments = 2
        self.base_repo.get_issue(self.pull.number).AndReturn(self.issue)
        self.issue.get_comments().AndReturn(self.comments)
        self.mox.ReplayAll()
        self.assertEquals(self.pr.get_comments(),
                          ["mock-comment", "mock-comment"])

    def test_create_comment(self):
        self.create_issue()
        self.issue.create_comment("comment")
        self.mox.ReplayAll()
        self.pr.create_comment("comment")

    # Commit/status tests
    def test_get_sha(self):
        self.pull.head.sha = "mock-sha"
        self.assertEquals(self.pr.get_sha(), self.pull.head.sha)

    def test_get_last_commit_default(self):
        self.create_commit(self.base_repo)
        self.mox.ReplayAll()
        self.assertEquals(self.pr.get_last_commit(), self.commit)

    def test_get_last_commit_base(self):
        self.create_commit(self.base_repo)
        self.mox.ReplayAll()
        self.assertEquals(self.pr.get_last_commit("base"), self.commit)

    def test_get_last_commit_head(self):
        self.create_commit(self.head_repo)
        self.mox.ReplayAll()
        self.assertEquals(self.pr.get_last_commit("head"), self.commit)

    def test_get_last_status_default(self):
        self.create_commit(self.base_repo)
        self.commit.get_statuses().AndReturn(self.statuses)
        self.mox.ReplayAll()
        self.assertEquals(self.pr.get_last_status(), None)

    def test_get_last_status_base(self):
        self.create_commit(self.base_repo)
        self.commit.get_statuses().AndReturn(self.statuses)
        self.mox.ReplayAll()
        self.assertEquals(self.pr.get_last_status("base"), None)

    def test_get_last_status_head(self):
        self.create_commit(self.head_repo)
        self.commit.get_statuses().AndReturn(self.statuses)
        self.mox.ReplayAll()
        self.assertEquals(self.pr.get_last_status("head"), None)

    def test_get_last_status_single(self):
        self.create_commit(self.base_repo)
        self.create_commit_status('pending')
        self.commit.get_statuses().AndReturn(self.statuses)
        self.mox.ReplayAll()
        self.assertEquals(self.pr.get_last_status().state, 'pending')

    def test_get_last_status_multiple(self):
        self.create_commit(self.base_repo)
        self.create_commit_status('success')
        self.create_commit_status('pending')
        self.commit.get_statuses().AndReturn(self.statuses)
        self.mox.ReplayAll()
        self.assertEquals(self.pr.get_last_status().state, 'success')

    def test_create_status_default(self):
        self.create_commit(self.base_repo)
        self.commit.create_status("mock-status", NotSet, "mock-message")
        self.mox.ReplayAll()
        self.pr.create_status("mock-status", "mock-message", None)

    def test_create_status_base(self):
        self.create_commit(self.base_repo)
        self.commit.create_status("mock-status", NotSet, "mock-message")
        self.mox.ReplayAll()
        self.pr.create_status("mock-status", "mock-message", None, ref="base")

    def test_create_status_head(self):
        self.create_commit(self.head_repo)
        self.commit.create_status("mock-status", NotSet, "mock-message")
        self.mox.ReplayAll()
        self.pr.create_status("mock-status", "mock-message", None, ref="head")

    def test_create_status_url(self):
        self.create_commit(self.base_repo)
        self.commit.create_status("mock-status", "mock-url", "mock-message")
        self.mox.ReplayAll()
        self.pr.create_status("mock-status", "mock-message", "mock-url")

if __name__ == '__main__':
    import logging
    import unittest
    logging.basicConfig()
    unittest.main()
