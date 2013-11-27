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
import pytest

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
from Mock import MoxTestBase


class TestPullRequest(MoxTestBase):

    def setup_method(self, method):
        super(TestPullRequest, self).setup_method(method)
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

    def create_commit(self, ref):
        self.pull.head.sha = "mock-sha"
        self.commit = self.mox.CreateMock(Commit)
        if ref == 'head':
            self.head_repo.get_commit("mock-sha").AndReturn(self.commit)
        else:
            self.base_repo.get_commit("mock-sha").AndReturn(self.commit)

    def create_commit_status(self, state="pending"):
        status = self.mox.CreateMock(CommitStatus)
        status.state = state
        self.statuses.append(status)

    def get_unicode(self):
        return u"  # PR %s %s '%s'" % (
            self.pull.number, self.pr_user.login, self.pull.title)

    def test_get_user(self):
        assert self.pr.get_user() == self.pr_user

    def test_get_title(self):
        assert self.pr.get_title() == self.pull.title

    @pytest.mark.parametrize('title', ['title', u"£title"])
    @pytest.mark.parametrize('user', ['user', u"£user"])
    def test_str(self, title, user):
        self.pull.title = title
        self.pr_user.login = user
        assert unicode(self.pr) == self.get_unicode()
        assert str(self.pr) == self.get_unicode().encode("utf-8")

    def test_edit_body(self):
        self.pull.edit("new_body")
        self.mox.ReplayAll()
        self.pr.edit("new_body")

    def test_get_login(self):
        assert self.pr.get_login() == self.pr_user.login

    def test_get_number(self):
        assert self.pr.get_number() == self.pull.number

    def test_get_issue(self):
        self.create_issue()
        self.mox.ReplayAll()
        assert self.pr.get_issue() == self.issue

    def test_get_base(self):
        assert self.pr.get_base() == self.base.ref

    # Label tests
    @pytest.mark.parametrize('nlabels', [0, 1, 2])
    def test_get_labels(self, nlabels):
        self.create_issue()
        for x in range(nlabels):
            self.create_label()
        self.issue.labels = self.labels
        self.mox.ReplayAll()
        assert self.pr.get_labels() == ["mock-label" for x in range(nlabels)]

    # Comment tests
    @pytest.mark.parametrize('ncomments', [0, 1, 2])
    def test_get_comments(self, ncomments):
        self.create_issue()
        for x in range(ncomments):
            self.create_issue_comment()
        if ncomments > 0:
            self.base_repo.get_issue(self.pull.number).AndReturn(self.issue)
            self.issue.get_comments().AndReturn(self.comments)
        self.mox.ReplayAll()
        assert self.pr.get_comments() == \
            ["mock-comment" for x in range(ncomments)]

    @pytest.mark.parametrize('org_users', [[True, False, True]])
    def test_get_comments_whitelist(self, org_users):
        org = self.mox.CreateMock(Organization)
        self.create_issue()
        self.base_repo.get_issue(self.pull.number).AndReturn(self.issue)
        self.issue.get_comments().AndReturn(self.comments)

        comments = []
        for is_org_user in org_users:
            user = self.mox.CreateMock(NamedUser)
            org.has_in_public_members(user).AndReturn(is_org_user)
            self.create_issue_comment("mock-comment-%s" % is_org_user,
                                      user=user)
            if is_org_user:
                comments.append("mock-comment-%s" % is_org_user)

        self.mox.ReplayAll()
        whitelist = lambda x: org.has_in_public_members(x.user)
        assert self.pr.get_comments(whitelist=whitelist) == comments

    def test_create_issue_comment(self):
        comment = self.mox.CreateMock(IssueComment)
        self.pull.create_issue_comment("comment").AndReturn(comment)
        self.mox.ReplayAll()
        assert self.pr.create_issue_comment("comment") == comment

    # Commit/status tests
    def test_get_sha(self):
        self.pull.head.sha = "mock-sha"
        assert self.pr.get_sha() == self.pull.head.sha

    @pytest.mark.parametrize('ref', ["base", "head"])
    def test_get_last_commit(self, ref):
        self.create_commit(ref)
        self.mox.ReplayAll()
        assert self.pr.get_last_commit(ref=ref) == self.commit

    @pytest.mark.parametrize('ref', ["base", "head"])
    @pytest.mark.parametrize(
        'states', [None, ["pending"], ["success", "pneding"]])
    def test_get_last_status(self, ref, states):
        self.create_commit(ref)
        if states:
            for state in states:
                self.create_commit_status(state=state)
        self.commit.get_statuses().AndReturn(self.statuses)
        self.mox.ReplayAll()
        last_status = self.pr.get_last_status(ref=ref)
        if states is None:
            assert last_status is None
        else:
            assert last_status.state == states[0]

    @pytest.mark.parametrize('ref', ["base", "head"])
    @pytest.mark.parametrize('url', [None, "mock-url"])
    def test_create_status_default(self, ref, url):
        self.create_commit(ref)
        if url is None:
            self.commit.create_status("mock-status", NotSet, "mock-message")
        else:
            self.commit.create_status("mock-status", url, "mock-message")
        self.mox.ReplayAll()
        self.pr.create_status("mock-status", "mock-message", url, ref=ref)

    # Body/comment Parsing
    def test_parse_body_empty(self):
        pattern = 'pattern'
        assert self.pr.parse_body(pattern) == []

    def test_parse_body_nomatch(self):
        pattern = 'pattern'
        nomatch = '-nomatch'
        self.pull.body = "%s%s\n" % (pattern, nomatch)
        assert self.pr.parse_body(pattern) == []

    def test_parse_body_multimatch(self):
        pattern = 'pattern'
        match1 = '-match1'
        match2 = '-match2'
        self.pull.body = "--%s%s\n--%s%s" % (pattern, match1, pattern, match2)
        assert self.pr.parse_body(pattern) == [match1, match2]

    def test_parse_body_multipattern(self):
        pattern1 = 'pattern1'
        match1 = '-match1'
        pattern2 = 'pattern2'
        match2 = '-match2'
        self.pull.body = "--%s%s\n--%s%s" % (pattern1, match1, pattern2,
                                             match2)
        assert self.pr.parse_body(pattern1) == [match1]
        assert self.pr.parse_body(pattern2) == [match2]
        assert self.pr.parse_body([pattern1, pattern2]) == \
            [match1, match2]

    def test_parse_comments_none(self):
        self.create_issue()
        pattern = 'pattern'
        self.mox.ReplayAll()
        assert self.pr.parse_comments(pattern) == []

    def test_parse_comments_single(self):
        pattern = 'pattern'
        match = '-match1'
        self.create_issue()
        self.create_issue_comment("--%s%s\n" % (pattern, match))
        self.base_repo.get_issue(self.pull.number).AndReturn(self.issue)
        self.issue.get_comments().AndReturn(self.comments)
        self.mox.ReplayAll()
        assert self.pr.parse_comments(pattern) == [match]

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
        assert self.pr.parse_comments([pattern1, pattern2]) == \
            [match1, match2]

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
        assert self.pr.parse_comments([pattern1, pattern2]) == \
            [match1, match2]

    def test_parse_empty(self):
        pattern = 'pattern'
        self.create_issue()
        self.mox.ReplayAll()
        assert self.pr.parse(pattern) == []

    def test_parse_body_only(self):
        pattern = 'pattern'
        match = '-match'
        self.pull.body = "--%s%s\n" % (pattern, match)
        assert self.pr.parse(pattern) == [match]

    def test_parse_comment_only(self):
        pattern = 'pattern'
        match = '-match'
        self.create_issue()
        self.create_issue_comment("--%s%s\n" % (pattern, match))
        self.base_repo.get_issue(self.pull.number).AndReturn(self.issue)
        self.issue.get_comments().AndReturn(self.comments)
        self.mox.ReplayAll()
        assert self.pr.parse(pattern) == [match]

if __name__ == '__main__':
    import logging
    import unittest
    logging.basicConfig()
    unittest.main()
