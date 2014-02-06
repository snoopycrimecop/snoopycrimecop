#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2012-2014 Glencoe Software, Inc. All Rights Reserved.
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

import pytest

from scc.framework import main, Stop
from scc.deploy import Deploy


class TestDeployInit(object):

    def deploy(self, tmpdir):
        args = ["deploy", "--init", str(tmpdir.join('test'))]
        main(args=args, items=[("deploy", Deploy)])

    def testInvalidFolder(self, tmpdir):
        with pytest.raises(Stop):
            self.deploy(tmpdir)

    def testExistingLiveFolder(self, tmpdir):
        tmpdir.mkdir('test')
        tmpdir.mkdir('test.live')
        with pytest.raises(Stop):
            self.deploy(tmpdir)

    def testFile(self, tmpdir):
        init_file = tmpdir.mkdir('test').join('foo')
        init_file.write('foo')
        self.deploy(tmpdir)
        assert tmpdir.join('test.live').check(dir=1)
        assert tmpdir.join('test').readlink() == str(tmpdir.join('test.live'))
        assert tmpdir.join('test.live').join('foo').check(file=1)
        assert tmpdir.join('test.live').join('foo').read() == 'foo'

    @pytest.mark.parametrize('broken', [True, False])
    def testSymlink(self, tmpdir, broken):
        init_file = tmpdir.mkdir('test').join('foo')
        init_file.write('foo')
        link = tmpdir.join('test').join('link')
        link.mksymlinkto(init_file)
        if broken:
            init_file.remove()
        assert link.check(link=1)
        assert link.readlink() == str(init_file)
        self.deploy(tmpdir)
        if broken:
            assert not tmpdir.join('test.live').join('link').check(file=1)
        else:
            assert tmpdir.join('test.live').join('link').check(file=1)
            assert tmpdir.join('test.live').join('link').read() == 'foo'


class TestDeploy(object):

    def deploy(self, tmpdir):
        args = ["deploy", str(tmpdir.join('test'))]
        main(args=args, items=[("deploy", Deploy)])

    def init(self, tmpdir):
        init_file = tmpdir.mkdir('test.live').join('foo')
        init_file.write('foo')
        link = tmpdir.join('test')
        link.mksymlinkto(tmpdir.join('test.live'))

    def testNoInit(self, tmpdir):
        tmpdir.mkdir('test')
        tmpdir.mkdir('test.tmp')
        with pytest.raises(Stop):
            self.deploy(tmpdir)

    def testWrongInit(self, tmpdir):
        tmpdir.mkdir('test')
        tmpdir.mkdir('test.live')
        with pytest.raises(Stop):
            self.deploy(tmpdir)

    def testMissingTmpFolder(self, tmpdir):
        self.init(tmpdir)
        with pytest.raises(Stop):
            self.deploy(tmpdir.join('test'))

    def testFile(self, tmpdir):
        self.init(tmpdir)
        new_file = tmpdir.mkdir('test.tmp').join('bar')
        new_file.write('bar')
        self.deploy(tmpdir)
        assert not tmpdir.join('test.tmp').check(dir=1)
        assert not new_file.check(file=1)
        assert not tmpdir.join('test.live').join('foo').check(file=1)
        assert tmpdir.join('test.live').join('bar').check(file=1)
        assert tmpdir.join('test.live').join('bar').read() == 'bar'

    @pytest.mark.parametrize('broken', [True, False])
    def testSymlink(self, tmpdir, broken):
        self.init(tmpdir)
        new_file = tmpdir.mkdir('test.tmp').join('bar')
        new_file.write('bar')
        link = tmpdir.join('test.tmp').join('link')
        link.mksymlinkto(new_file)
        if broken:
            new_file.remove()
        assert link.check(link=1)
        assert link.readlink() == str(new_file)
        self.deploy(tmpdir)
        if broken:
            assert not tmpdir.join('test.live').join('link').check(file=1)
        else:
            assert tmpdir.join('test.live').join('link').check(file=1)
            assert tmpdir.join('test.live').join('link').read() == 'bar'
