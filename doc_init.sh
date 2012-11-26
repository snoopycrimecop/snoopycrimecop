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

# doc_init.sh <folder_name>
# This script prepares a folder with content already present in it for
# "symlink swapping" deployment. After running the script, the contents
# of the <folder_name> will be stored in <folder_name>.live with a
# <folder_name> symlink pointing at it. Running this script might interrupt
# serving content - the mv operation introduces a window of content
# downtime.
set -e
set -u
set -x

NAME=$1

mkdir "${NAME}.live"
mv "${NAME}"/* "${NAME}.live"
rm -rf "${NAME}"
ln -s "${NAME}.live" "${NAME}"