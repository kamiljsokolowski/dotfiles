Dotfiles
========

The life-time project that is my configuration files set.

Deployment
----------

Clone this repository:

```Shell
git clone https://github.com/sokolowskik/dotfiles.git ~/.dotfiles
```

cd in to the dotfiles dir

```Shell
cd ~/.dotfiles
```

and run it (repo location is optional):

```Shell
# (for ZSH to check ~/.config/zsh dir for config) this needs to be executed outside of GNU Stow
ln -s ~/.dotfiles/zsh/.zshenv ~/.zshenv

stow -v .
```

