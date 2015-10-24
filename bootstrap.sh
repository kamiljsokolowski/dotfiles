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

# update Git submodulels (submodules could be updated during git clone)
cd ${basedir}
git submodule init && git submodule update
cd -

# Git
if [ -f ~/.gitconfig ]; then rm -rf ~/.gitconfig
fi
ln -s ${basedir}/gitconfig ~/.gitconfig

# tmux
if [ -f ~/.tmux.conf ]; then rm -rf ~/.tmux.conf
fi
ln -s ${basedir}/tmux.conf ~/.tmux.conf
if [ -d ~/.tmux ]; then rm -rf ~/.tmux
fi
ln -s ${basedir}/tmux ~/.tmux

# Vim
if [ -f ~/.vimrc ]; then rm -rf ~/.vimrc
fi
ln -s ${basedir}/vimrc ~/.vimrc
if [ -d ~/.vim ]; then rm -rf ~/.vim
fi
ln -s ${basedir}/vim ~/.vim
# Powerline (requires pip)
command -v pip >/dev/null 2>&1 || { echo >&2 "Did not found pip.. no powerlining for You today mate!"; exit 1; }
pip install --user powerline-status
# Powerline fonts
git clone https://github.com/powerline/fonts.git ~/powerline-fonts
~/powerline-fonts/install.sh

