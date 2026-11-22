# XDG Base Directory
export XDG_CONFIG_HOME="${HOME}/.config"
export XDG_DATA_HOME="${HOME}/.local/share"
export XDG_STATE_HOME="${HOME}/.local/state"
export XDG_CACHE_HOME="${HOME}/.cache"

## Keep $HOME clean - redirect zsh files to XDG
export ZDOTDIR="${XDG_CONFIG_HOME}/zsh"

# Editor
export EDITOR="nvim"
export VISUAL="nvim"

# GPG
export GPG_TTY=$(tty)

# Path
## Personal binaries, scripts etc.
export PATH="$HOME/.local/bin:$PATH"

# Prompt
export STARSHIP_CONFIG="$HOME/.config/starship/starship.toml"
