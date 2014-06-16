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

import os
import sys
from yaclifw.framework import Command, Stop


class Deploy(Command):
    """
    Deploy an update to a website using the "symlink swapping" strategy.
    See https://gist.github.com/3807742.
    """

    NAME = "deploy"

    def __init__(self, sub_parsers):
        super(Deploy, self).__init__(sub_parsers)

        self.parser.add_argument(
            '--init', action='store_true',
            help='Prepare a folder with content for "symlink swapping"')
        self.parser.add_argument(
            'folder', type=str,
            help="The folder to be deployed/updated")

    def __call__(self, args):
        super(Deploy, self).__call__(args)

        self.folder = args.folder
        self.live_folder = self.folder + ".live"
        self.tmp_folder = self.folder + ".tmp"

        if args.init:
            self.doc_init()
        else:
            self.doc_deploy()

    def doc_init(self):
        """
        Set up the symlink swapping structure to use the deployment script.
        """

        if not os.path.exists(self.folder):
            raise Stop(5, "The following path does not exist: %s. "
                       "Copy some contents to this folder and run"
                       " scc deploy --init again." % self.folder)

        if os.path.exists(self.live_folder):
            raise Stop(5, "The following path already exists: %s. "
                       "Run the scc deploy command without the --init"
                       " argument." % self.live_folder)

        self.copytree(self.folder, self.live_folder)
        self.rmtree(self.folder)
        self.symlink(self.live_folder, self.folder)

    def doc_deploy(self):
        """
        Deploy a new content using symlink swapping.

        Two symlinks get replaced during the lifetime of the script. Both
        operations are atomic.
        """

        if not os.path.exists(self.live_folder):
            raise Stop(5, "The following path does not exist: %s. "
                       "Pass --init to the scc deploy command to initialize "
                       "the symlink swapping." % self.live_folder)

        if not os.path.islink(self.folder):
            raise Stop(5, "The following path is not a symlink: %s. "
                       "Pass --init to the scc deploy command to initialize "
                       "the symlink swapping." % self.folder)

        if not os.path.exists(self.tmp_folder):
            raise Stop(5, "The following path does not exist: %s. "
                       "Copy the new content to be deployed to this folder "
                       "and  run scc deploy again." % self.tmp_folder)

        self.symlink(self.tmp_folder, self.folder)
        self.rmtree(self.live_folder)

        self.copytree(self.tmp_folder, self.live_folder)
        self.symlink(self.live_folder, self.folder)

        self.rmtree(self.tmp_folder)

    def copytree(self, src, dst):
        import shutil
        self.dbg("Copying %s/* to %s/*", src, dst)
        try:
            shutil.copytree(src, dst)
        except shutil.Error, e:
            for src, dst, error in e.args[0]:
                if os.path.islink(src):
                    print >> sys.stderr, "Could not copy symbolic link %s" \
                        % src
                else:
                    print >> sys.stderr, "Could not copy %s" % src

    def rmtree(self, src):
        import shutil
        self.dbg("Removing %s folder", src)
        shutil.rmtree(src)

    def symlink(self, src, link):

        if os.path.islink(link):
            self.dbg("Replacing symbolic link %s to point to %s", link, src)
            new = link + ".new"
            os.symlink(src, new)
            os.rename(new, link)
        else:
            self.dbg("Creating a symbolic link named %s pointing to %s",
                     link, src)
            os.symlink(src, link)
