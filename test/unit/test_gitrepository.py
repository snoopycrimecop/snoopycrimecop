#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2015 University of Dundee & Open Microscopy Environment
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

from scc.git import GitRepository
import pytest
from Mock import MoxTestBase

import logging
import subprocess


class MockGitRepository(GitRepository):

    def __init__(self, gh, path):
        self.log = logging.getLogger("test.test_gitrepository")
        self.dbg = self.log.debug
        self.info = self.log.info
        self.debugWrap = None
        self.infoWrap = None
        self.errorWrap = None

        self.gh = gh
        self.path = path

    def __del__(self):
        pass


class MockPopen(object):

    class MockIO(object):

        def __init__(self):
            self.n_close = 0

        def close(self):
            self.n_close += 1

    def __init__(self, rcode, retout, reterr):
        self.stdout = self.MockIO()
        self.stderr = self.MockIO()
        self.returncode = rcode
        self.retout = retout
        self.reterr = reterr
        self.n_wait = 0

    def communicate(self):
        return self.retout, self.reterr

    def wait(self):
        self.n_wait += 1
        return self.returncode


class TestGitRepository(MoxTestBase):

    def setup_popen(self, rcode, stderr, stdout):
        repo = MockGitRepository(None, '.')
        self.mox.StubOutWithMock(subprocess, 'Popen')
        p = MockPopen(rcode, 'out', 'err')
        subprocess.Popen(
            ('cmd', 'a', 'b'), stdout=stdout, stderr=stderr).AndReturn(p)
        return repo, p

    @pytest.mark.parametrize('no_wait', [True, False])
    @pytest.mark.parametrize('return_stderr', [True, False])
    def test_communicate(self, tmpdir, no_wait, return_stderr):
        repo, p = self.setup_popen(0, subprocess.PIPE, subprocess.PIPE)
        self.mox.ReplayAll()

        r = repo.communicate(
            'cmd', 'a', 'b', no_wait=no_wait, return_stderr=return_stderr)
        if return_stderr:
            assert r == ('out', 'err')
        else:
            assert r == 'out'
        assert p.stdout.n_close == 1
        assert p.stderr.n_close == 1
        assert p.n_wait == 0

    def test_communicate_fail(self):
        repo, p = self.setup_popen(1, subprocess.PIPE, subprocess.PIPE)
        self.mox.ReplayAll()

        with pytest.raises(Exception) as exc_info:
            repo.communicate('cmd', 'a', 'b')
        assert exc_info.value.message.startswith('Failed to run ')
        assert p.stdout.n_close == 1
        assert p.stderr.n_close == 1
        assert p.n_wait == 0

    @pytest.mark.parametrize('no_wait', [True, False])
    def test_call_no_wait(self, no_wait):
        repo, p = self.setup_popen(0, None, None)
        self.mox.ReplayAll()

        r = repo.call_no_wait('cmd', 'a', 'b', no_wait=no_wait)
        assert r == p
        assert p.stdout.n_close == 0
        assert p.stderr.n_close == 0
        assert p.n_wait == 0

    @pytest.mark.parametrize('no_wait', [True, False])
    def test_call(self, no_wait):
        repo, p = self.setup_popen(0, None, None)
        self.mox.ReplayAll()

        r = repo.call_no_wait('cmd', 'a', 'b', no_wait=no_wait)
        assert r == p
        assert p.stdout.n_close == 0
        assert p.stderr.n_close == 0
        assert p.n_wait == 0 if no_wait else 1

    def test_call_fail(self):
        repo, p = self.setup_popen(1, None, None)
        self.mox.ReplayAll()

        with pytest.raises(Exception) as exc_info:
            repo.call('cmd', 'a', 'b')
        assert exc_info.value.message == 'rc=1'
        assert p.stdout.n_close == 0
        assert p.stderr.n_close == 0
        assert p.n_wait == 1
