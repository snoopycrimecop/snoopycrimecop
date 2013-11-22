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
from github.NamedUser import NamedUser
from github.Organization import Organization
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
        self.base.ref = "mock-base-ref"

        # Create head of PullRequest
        self.head_user = self.mox.CreateMock(AuthenticatedUser)
        self.head_repo = self.mox.CreateMock(Repository)
        self.head = self.mox.CreateMock(PullRequestPart)
        self.head.repo = self.head_repo
        self.head.user = self.head_user
        self.base.ref = "mock-head-ref"

        # Create owner of PullRequest
        self.pr_user = self.mox.CreateMock(AuthenticatedUser)
        self.pr_user.login = "mock-user"

        # Create PullRequest and set user, base, head and properties
        self.pull = self.mox.CreateMock(PullRequest)
        self.pull.user = self.pr_user
        self.pull.base = self.base
        self.pull.head = self.head
        self.pull.title = "mock-title"
        self.pull.body = ""
        self.pull.number = 0

        # Initialize
        self.comments = []
        self.labels = []
        self.statuses = []
        self.pr = scc.git.PullRequest(self.pull)

    def create_issue(self):
        self.issue = self.mox.CreateMock(Issue)
        self.issue.comments = 0
        self.base_repo.get_issue(self.pull.number).AndReturn(self.issue)

    def create_label(self, name="mock-label"):
        label = self.mox.CreateMock(Label)
        label.name = name
        self.labels.append(label)

    def create_issue_comment(self, body="mock-comment", user=None):
        comment = self.mox.CreateMock(IssueComment)
        comment.body = body
        if user:
            comment.user = user
        else:
            comment.user = self.head_user
        self.issue.comments += 1
        self.comments.append(comment)

    def create_commit(self, repo):
        self.pull.head.sha = "mock-sha"
        self.commit = self.mox.CreateMock(Commit)
        repo.get_commit("mock-sha").AndReturn(self.commit)

    def create_commit_status(self, state="pending"):
        status = self.mox.CreateMock(CommitStatus)
        status.state = state
        self.statuses.append(status)

    def get_unicode(self):
        return u"  # PR %s %s '%s'" % (
            self.pull.number, self.pr_user.login, self.pull.title)

    def test_get_user(self):
        self.assertEquals(self.pr.get_user(), self.pr_user)

    def test_get_title(self):
        self.assertEquals(self.pr.get_title(), self.pull.title)

    def test_str(self):
        self.assertEquals(unicode(self.pr), self.get_unicode())
        self.assertEquals(str(self.pr), self.get_unicode().encode("utf-8"))

    def test_str_unicode_title(self):
        self.pull.title = u"£unicode"
        self.assertEquals(unicode(self.pr), self.get_unicode())
        self.assertEquals(str(self.pr), self.get_unicode().encode("utf-8"))

    def test_str_unicode_user(self):
        self.pr_user.login = u"£user"
        self.assertEquals(unicode(self.pr), self.get_unicode())
        self.assertEquals(str(self.pr), self.get_unicode().encode("utf-8"))

    def test_edit_body(self):
        self.pull.edit("new_body")
        self.mox.ReplayAll()
        self.pr.edit("new_body")

    def test_get_login(self):
        self.assertEquals(self.pr.get_login(), self.pr_user.login)

    def test_get_number(self):
        self.assertEquals(self.pr.get_number(), self.pull.number)

    def test_get_issue(self):
        self.create_issue()
        self.mox.ReplayAll()
        self.assertEquals(self.pr.get_issue(), self.issue)

    def test_get_base(self):
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
        self.mox.ReplayAll()
        self.assertEquals(self.pr.get_comments(), [])

    def test_get_comments_single(self):
        self.create_issue()
        self.create_issue_comment()
        self.base_repo.get_issue(self.pull.number).AndReturn(self.issue)
        self.issue.get_comments().AndReturn(self.comments)
        self.mox.ReplayAll()
        self.assertEquals(self.pr.get_comments(), ["mock-comment"])

    def test_get_comments_multiple(self):
        self.create_issue()
        self.create_issue_comment("mock-comment")
        self.create_issue_comment("mock-comment")
        self.base_repo.get_issue(self.pull.number).AndReturn(self.issue)
        self.issue.get_comments().AndReturn(self.comments)
        self.mox.ReplayAll()
        self.assertEquals(self.pr.get_comments(),
                          ["mock-comment", "mock-comment"])

    def test_get_comments_whitelist(self):
        org = self.mox.CreateMock(Organization)
        org_user_1 = self.mox.CreateMock(NamedUser)
        org_user_2 = self.mox.CreateMock(NamedUser)
        ext_user = self.mox.CreateMock(NamedUser)
        self.create_issue()
        self.create_issue_comment("mock-comment-1", user=org_user_1)
        self.create_issue_comment("mock-comment-2", user=ext_user)
        self.create_issue_comment("mock-comment-3", user=org_user_2)
        self.base_repo.get_issue(self.pull.number).AndReturn(self.issue)
        self.issue.get_comments().AndReturn(self.comments)
        org.has_in_public_members(org_user_1).AndReturn(True)
        org.has_in_public_members(ext_user).AndReturn(False)
        org.has_in_public_members(org_user_2).AndReturn(True)
        self.mox.ReplayAll()
        whitelist = lambda x: org.has_in_public_members(x.user)
        self.assertEquals(self.pr.get_comments(whitelist=whitelist),
                          ["mock-comment-1", "mock-comment-3"])

    def test_create_issue_comment(self):
        comment = self.mox.CreateMock(IssueComment)
        self.pull.create_issue_comment("comment").AndReturn(comment)
        self.mox.ReplayAll()
        self.assertEqual(self.pr.create_issue_comment("comment"), comment)

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

    # Body/comment Parsing
    def test_parse_body_empty(self):
        pattern = 'pattern'
        self.assertEquals(self.pr.parse_body(pattern), [])

    def test_parse_body_nomatch(self):
        pattern = 'pattern'
        nomatch = '-nomatch'
        self.pull.body = "%s%s\n" % (pattern, nomatch)
        self.assertEquals(self.pr.parse_body(pattern), [])

    def test_parse_body_multimatch(self):
        pattern = 'pattern'
        match1 = '-match1'
        match2 = '-match2'
        self.pull.body = "--%s%s\n--%s%s" % (pattern, match1, pattern, match2)
        self.assertEquals(self.pr.parse_body(pattern), [match1, match2])

    def test_parse_body_multipattern(self):
        pattern1 = 'pattern1'
        match1 = '-match1'
        pattern2 = 'pattern2'
        match2 = '-match2'
        self.pull.body = "--%s%s\n--%s%s" % (pattern1, match1, pattern2,
                                             match2)
        self.assertEquals(self.pr.parse_body(pattern1), [match1])
        self.assertEquals(self.pr.parse_body(pattern2), [match2])
        self.assertEquals(self.pr.parse_body([pattern1, pattern2]),
                          [match1, match2])

    def test_parse_comments_none(self):
        self.create_issue()
        pattern = 'pattern'
        self.mox.ReplayAll()
        self.assertEquals(self.pr.parse_comments(pattern), [])

    def test_parse_comments_single(self):
        pattern = 'pattern'
        match = '-match1'
        self.create_issue()
        self.create_issue_comment("--%s%s\n" % (pattern, match))
        self.base_repo.get_issue(self.pull.number).AndReturn(self.issue)
        self.issue.get_comments().AndReturn(self.comments)
        self.mox.ReplayAll()
        self.assertEquals(self.pr.parse_comments(pattern), [match])

    def test_parse_comments_single_multipattern(self):
        pattern1 = 'pattern1'
        match1 = '-match1'
        pattern2 = 'pattern2'
        match2 = '-match2'
        self.create_issue()
        self.create_issue_comment("--%s%s\n--%s%s\n"
                                  % (pattern1, match1, pattern2, match2))
        self.base_repo.get_issue(self.pull.number).AndReturn(self.issue)
        self.issue.get_comments().AndReturn(self.comments)
        self.mox.ReplayAll()
        self.assertEquals(self.pr.parse_comments([pattern1, pattern2]),
                          [match1, match2])

    def test_parse_comments_multiple(self):
        pattern1 = 'pattern1'
        match1 = '-match1'
        pattern2 = 'pattern2'
        match2 = '-match2'
        self.create_issue()
        self.create_issue_comment("--%s%s\n" % (pattern1, match1))
        self.create_issue_comment("--%s%s\n" % (pattern2, match2))
        self.base_repo.get_issue(self.pull.number).AndReturn(self.issue)
        self.issue.get_comments().AndReturn(self.comments)
        self.mox.ReplayAll()
        self.assertEquals(self.pr.parse_comments([pattern1, pattern2]),
                          [match1, match2])

    def test_parse_empty(self):
        pattern = 'pattern'
        self.create_issue()
        self.mox.ReplayAll()
        self.assertEquals(self.pr.parse(pattern), [])

    def test_parse_body_only(self):
        pattern = 'pattern'
        match = '-match'
        self.pull.body = "--%s%s\n" % (pattern, match)
        self.assertEquals(self.pr.parse(pattern), [match])

    def test_parse_comment_only(self):
        pattern = 'pattern'
        match = '-match'
        self.create_issue()
        self.create_issue_comment("--%s%s\n" % (pattern, match))
        self.base_repo.get_issue(self.pull.number).AndReturn(self.issue)
        self.issue.get_comments().AndReturn(self.comments)
        self.mox.ReplayAll()
        self.assertEquals(self.pr.parse(pattern), [match])

if __name__ == '__main__':
    import logging
    import unittest
    logging.basicConfig()
    unittest.main()
