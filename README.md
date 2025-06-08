Dotfiles
========

The life-time project that is my configuration files set.

Pre-reqs
--------

Diff-so-fancy
- MacOS
```Shell
brew install diff-so-fancy
```

Deployment
----------

Clone this repository:

```Shell
git clone --recursive https://github.com/sokolowskik/dotfiles.git
```

`bootstrap.sh` script should already be executable. Otherwise simply execute:

```Shell
chmod +x bootstrap.sh
```

and run it (repo location is optional):

```Shell
./bootstrap.sh <repo_dir>
./bootstrap.sh
```

Installing TMUX plugins
-----------------------

Hit `prefix + I` when inside an active tmux session and all the plugins will be installed in to `~/.tmux/plugins`.

