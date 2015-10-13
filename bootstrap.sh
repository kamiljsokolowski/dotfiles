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
if [ -f ~/.gitconfig ]; then rm -rf ~/.gitconfig
fi
ln -s ${basedir}/gitconfig ~/.gitconfig

# tmux
if [ -f ~/.tmux.conf ]; then rm -rf ~/.tmux.conf
fi
ln -s ${basedir}/tmux.conf ~/.tmux.conf
mkdir -p ~/.tmux/plugins
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm

# Vim
if [ -f ~/.vimrc ]; then rm -rf ~/.vimrc
fi
ln -s ${basedir}/vimrc ~/.vimrc
# Powerline (requires pip)
pip install --user powerline-status
# Powerline fonts
git clone https://github.com/powerline/fonts.git ~/powerline-fonts
~/powerline-fonts/install.sh

