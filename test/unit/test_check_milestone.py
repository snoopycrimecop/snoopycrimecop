#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2014 University of Dundee & Open Microscopy Environment
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

from yaclifw.framework import parsers

from github.AuthenticatedUser import AuthenticatedUser
from github.Issue import Issue
from github.Milestone import Milestone
from github.PullRequest import PullRequest
from github.PullRequestPart import PullRequestPart
from github.Repository import Repository

from scc.git import CheckMilestone, PullRequest as PR
import pytest
from Mock import MoxTestBase


class TestCheckMilestone(MoxTestBase):

    def setup_method(self, method):
        super(TestCheckMilestone, self).setup_method(method)
        self.scc_parser, self.sub_parser = parsers()
        self.command = CheckMilestone(self.sub_parser)

        # Mocks
        # Create base of PullRequest
        self.base_user = self.mox.CreateMock(AuthenticatedUser)
        self.base_repo = self.mox.CreateMock(Repository)
        self.base = self.mox.CreateMock(PullRequestPart)
        self.base.repo = self.base_repo
        self.base.user = self.base_user
        self.base.ref = "mock-base-ref"
        self.pull = self.mox.CreateMock(PullRequest)
        self.pull.number = 0
        self.pull.title = 'test'
        self.pull.milestone = None
        self.pull.base = self.base
        self.issue = self.mox.CreateMock(Issue)
        self.milestones = []
        self.milestones.append(self.mox.CreateMock(Milestone))
        self.milestones[0].title = 'test 1'
        self.milestones.append(self.mox.CreateMock(Milestone))
        self.milestones[1].title = 'test 2'
        self.pr = PR(self.pull)

    def assign_milestone(self, milestone_index):
        if milestone_index is None:
            return
        self.pull.milestone = self.milestones[milestone_index]

    @pytest.mark.parametrize('milestone_index', [None, 0, 1])
    def test_no_milestone(self, milestone_index):
        self.assign_milestone(milestone_index)
        [mcheck, mset] = self.command.check_pr_milestone(self.pr, None)
        assert mcheck is (milestone_index is not None)
        assert not mset

    @pytest.mark.parametrize('milestone_index', [None, 0, 1])
    def test_check_existing_milestone(self, milestone_index):
        self.assign_milestone(milestone_index)
        if milestone_index != 0:
            self.base_repo.get_issue(self.pr.number).AndReturn(self.issue)
            self.issue.edit(milestone=self.milestones[0]).AndReturn(True)
            self.mox.ReplayAll()

        [mcheck, mset] = self.command.check_pr_milestone(
            self.pr, self.milestones[0])
        assert mcheck is (milestone_index is not None)
        assert mset == (milestone_index != 0)
