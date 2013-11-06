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

"""
Primary launching functions for omego. All Commands
which are present in the globals() of this module
will be presented to the user.
"""

import traceback
import sys

from framework import main, Stop
from git import AlreadyMerged, CheckMilestone, CheckStatus, Label, Merge, \
    Rebase, SetCommitStatus, TagRelease, Token, TravisMerge, UnrebasedPRs, \
    UpdateSubmodules
from deploy import Deploy
from version import Version


def entry_point():
    """
    External entry point which calls main() and
    if Stop is raised, calls sys.exit()
    """
    try:
        main(items=[
            (AlreadyMerged.NAME, AlreadyMerged),
            (CheckMilestone.NAME, CheckMilestone),
            (CheckStatus.NAME, CheckStatus),
            (Deploy.NAME, Deploy),
            (Label.NAME, Label),
            (Merge.NAME, Merge),
            (Rebase.NAME, Rebase),
            (Token.NAME, Token),
            (SetCommitStatus.NAME, SetCommitStatus),
            (TagRelease.NAME, TagRelease),
            (TravisMerge.NAME, TravisMerge),
            (Version.NAME, Version),
            (UnrebasedPRs.NAME, UnrebasedPRs),
            (UpdateSubmodules.NAME, UpdateSubmodules),
            ])
    except Stop, stop:
        print stop,
        sys.exit(stop.rc)
    except SystemExit:
        raise
    except:
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    entry_point()
