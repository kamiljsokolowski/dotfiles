Dotfiles
========

The life-time project that is my configuration files set.

Deployment
----------

Clone this repository:

```Shell
git clone -bare https://github.com/sokolowskik/dotfiles.git
```

Make bootstrap.sh script executable:

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

Simply hit `prefix + I` when inside an active tmux session and all the plugins will be installed in to `~/.tmux/plugins`.


Vim Powerline plugin setup
--------------------------

Install `pip` - Python package manager - before setting up `Powerline`.

In order to make `Powerline` special symbols display properly, terminal needs to be manually configured to use the patched font (this is OS-dependent).

