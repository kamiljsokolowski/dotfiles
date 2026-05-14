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
# ZSH: must live in $HOME, not ~/.config — symlink manually
ln -s ~/.dotfiles/zsh/.zshenv ~/.zshenv

# Symlink all configs to ~/.config/ via GNU Stow
stow -v .

# Claude Code expects ~/.claude — symlink to the stow-managed location
ln -s ~/.config/claude ~/.claude
```
