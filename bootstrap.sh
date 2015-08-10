#!/usr/bin/env bash

dir=$1
#basedir="cd "$(dirname "${BASH_SOURCE[0]}")" && pwd"
basedir=`pwd`

if [ "$dir" = "" ]; then
	echo "Repo dir (hit ENTER to use '$basedir')"
	read dir
fi

if [ "$dir" = "" ]; then
	dir=$basedir
fi

# Git
ln -s ${basedir}/gitconfig ~/.gitconfig

# Vim
ln -s ${basedir}/vimrc ~/.vimrc

