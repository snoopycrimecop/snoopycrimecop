#!/bin/sh

# Copyright (C) 2012 Glencoe Software, Inc. All Rights Reserved.
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

# doc_deploy.sh <folder_name>
# The script assumes that following naming rules apply:
# - <folder_name> is an existing symlink to "live" content being served
#   (created by init.sh),
# - <folder_name>.live is the data that <folder_name> symlinks to,
# - <folder_name>.tmp is the new content produced by Hudson.
#
# Once the Hudson job finishes and the artifacts get deployed to necronamcer,
# this script is run with the deployment target folder name as the parameter.
# Two symlinks get replaced during the lifetime of the script. Both operations
# are atomic. See https://gist.github.com/3807742.
set -e
set -u
set -x

NAME=$1

ln -s "${NAME}.tmp" "${NAME}.new"
mv -T "${NAME}.new" "${NAME}"
rm -rf "${NAME}.live"/*
cp -aH "${NAME}.tmp"/* "${NAME}.live"
ln -s "${NAME}.live" "${NAME}.new"
mv -T "${NAME}.new" "${NAME}"
rm -rf "${NAME}.tmp"