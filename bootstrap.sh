#!/usr/bin/env bash

dir=$1
#basedir="cd "$(dirname "${BASH_SOURCE[0]}")" && pwd"
basedir=`pwd`

if [ "${dir}" = "" ]; then
	echo "Repo dir (hit ENTER to use '${basedir}')"
	read dir
fi

if [ "${dir}" = "" ]; then
	dir=${basedir}
fi

# update Git submodulels (submodules could be updated during git clone)
cd ${dir}
git submodule init && git submodule update
cd -

# Git
if [ -f ${HOME}/.gitconfig ]; then rm -rf ${HOME}/.gitconfig
fi
ln -s ${dir}/gitconfig ${HOME}/.gitconfig

# tmux
if [ -f ${HOME}/.tmux.conf ]; then rm -rf ${HOME}/.tmux.conf
fi
ln -s ${dir}/tmux.conf ${HOME}/.tmux.conf
if [ -d ${HOME}/.tmux ]; then rm -rf ${HOME}/.tmux
fi
ln -s ${dir}/tmux ${HOME}/.tmux

# Vim
if [ -f ${HOME}/.vimrc ]; then rm -rf ${HOME}/.vimrc
fi
ln -s ${dir}/vimrc ${HOME}/.vimrc
if [ -d ${HOME}/.vim ]; then rm -rf ${HOME}/.vim
fi
ln -s ${dir}/vim ${HOME}/.vim
# Powerline (requires pip)
command -v pip >/dev/null 2>&1 || { echo >&2 "Did not found pip.. no powerlining for You today mate!"; exit 1; }
pip install --user powerline-status
# Powerline fonts
git clone https://github.com/powerline/fonts.git ${HOME}/powerline-fonts
${HOME}/powerline-fonts/install.sh

