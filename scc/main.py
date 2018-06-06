#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2013-2014 University of Dundee & Open Microscopy Environment
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

"""
Primary launching functions for omego. All Commands
which are present in the globals() of this module
will be presented to the user.
"""

import traceback
import sys

from yaclifw.framework import main, Stop
from git import AlreadyMerged
from git import CheckLabels
from git import CheckMilestone
from git import CheckPRs
from git import CheckStatus
from git import DeleteTags
from git import ExternalIssues
from git import Label
from git import Merge
from git import MilestoneCommand
from git import Rate
from git import Rebase
from git import SetCommitStatus
from git import TagRelease
from git import Token
from git import TravisMerge
from git import UnsubscribedRepos
from git import UpdateSubmodules
from deploy import Deploy
from version import Version


def entry_point():
    """
    External entry point which calls main() and
    if Stop is raised, calls sys.exit()
    """
    try:
        main("scc", items=[
            (AlreadyMerged.NAME, AlreadyMerged),
            (CheckLabels.NAME, CheckLabels),
            (CheckMilestone.NAME, CheckMilestone),
            (CheckPRs.NAME, CheckPRs),
            (CheckStatus.NAME, CheckStatus),
            (Deploy.NAME, Deploy),
            (DeleteTags.NAME, DeleteTags),
            (Label.NAME, Label),
            (ExternalIssues.NAME, ExternalIssues),
            (Merge.NAME, Merge),
            (MilestoneCommand.NAME, MilestoneCommand),
            (Rate.NAME, Rate),
            (Rebase.NAME, Rebase),
            (SetCommitStatus.NAME, SetCommitStatus),
            (Token.NAME, Token),
            (TagRelease.NAME, TagRelease),
            (TravisMerge.NAME, TravisMerge),
            (Version.NAME, Version),
            (UnsubscribedRepos.NAME, UnsubscribedRepos),
            (UpdateSubmodules.NAME, UpdateSubmodules),
            ])
    except Stop, stop:
        print stop,
        sys.exit(stop.rc)
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print "Cancelled"
        sys.exit(1)
    except Exception:
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    entry_point()
