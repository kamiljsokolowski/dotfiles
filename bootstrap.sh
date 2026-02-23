#!/usr/bin/env bash

dir=$1
#basedir="cd "$(dirname "${BASH_SOURCE[0]}")" && pwd"
basedir=$(pwd)

if [ "${dir}" = "" ]; then
  echo "Repo dir (hit ENTER to use '${basedir}')"
  read dir
fi

if [ "${dir}" = "" ]; then
  dir=${basedir}
fi

# Homebrew Bundle
if [ -f "Brewfile" ] && [ "$(uname -s)" = "Darwin" ]; then
  brew bundle check >/dev/null 2>&1 || {
    echo "==> Installing Homebrew dependencies…"
    brew bundle
  }
fi

# update Git submodulels (submodules could be updated during git clone)
cd ${dir}
git submodule init && git submodule update
cd -

# zsh
if [ -f ${HOME}/.zshrc ]; then
  rm -rf ${HOME}/.zshrc
fi
ln -s ${dir}/zsh/zshrc ${HOME}/.zshrc

# spaceship
if [ -f ${HOME}/.config/spaceship ]; then
  rm -rf ${HOME}/.config/spaceship
fi
ln -s ${dir}/spaceship/spaceship.zsh ${HOME}/.config/spaceship.zsh

# tmux
if [ -f ${HOME}/.tmux.conf ]; then
  rm -rf ${HOME}/.tmux.conf
fi
ln -s ${dir}/tmux/tmux.conf ${HOME}/.tmux.conf
if [ -d ${HOME}/.tmux ]; then
  rm -rf ${HOME}/.tmux
fi
ln -s ${dir}/tmux ${HOME}/.tmux

# Git
if [ -f ${HOME}/.gitconfig ]; then
  rm -rf ${HOME}/.gitconfig
fi
ln -s ${dir}/git/gitconfig ${HOME}/.gitconfig

# Vim
if [ -f ${HOME}/.vimrc ]; then
  rm -rf ${HOME}/.vimrc
fi
if [ -d ${HOME}/.vim ]; then
  rm -rf ${HOME}/.vim
fi
ln -s ${dir}/vim ${HOME}/.vim
