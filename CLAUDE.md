# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Deployment

Clone to `~/.dotfiles`, then:

```bash
# .zshenv must be in $HOME (not ~/.config), so it's symlinked manually
ln -s ~/.dotfiles/zsh/.zshenv ~/.zshenv

# Symlink all other configs to ~/.config/ via GNU Stow
stow -v .
```

To re-apply after changes: `stow -v .` (from `~/.dotfiles`)
To remove symlinks: `stow -vD .`

## Architecture

**GNU Stow + XDG Base Directory.** Each top-level directory is a Stow "package". Stow symlinks its contents into `~/.config/` (configured in `.stowrc`). The result: `~/.config/nvim/` → `~/.dotfiles/nvim/`, etc.

**Exceptions handled in `.stowrc`:**
- `zsh/.zshenv` — manually symlinked to `~/.home` instead
- `vim/*` — excluded entirely (legacy, kept for reference only)
- Top-level non-config files (`Brewfile`, `README.md`, etc.) — ignored

## Tool Stack

| Tool | Config dir | Notes |
|------|-----------|-------|
| Zsh | `zsh/` | Oh-My-Zsh + Spaceship prompt; `.zshenv` sets `ZDOTDIR` |
| Neovim | `nvim/` | LazyVim-based; plugins via `lazy.nvim` |
| Tmux | `tmux/` | Prefix `Ctrl+A`; plugins via TPM at `~/.tmux/plugins/tpm` |
| Git | `git/` | Uses `diff-so-fancy` pager |
| Ghostty | `ghostty/` | Primary terminal; Catppuccin Mocha theme |
| Spaceship | `spaceship/` | Prompt theme config |
| Vim | `vim/` | Legacy fallback; excluded from Stow |

## Neovim (LazyVim)

- Entry: `nvim/init.lua` bootstraps `lazy.nvim`
- Core config: `nvim/lua/config/` (options, keymaps, autocmds, lazy setup)
- Plugin overrides/additions: `nvim/lua/plugins/`
- Lua formatter config: `nvim/stylua.toml`

## Tmux

TPM plugins are installed at `~/.tmux/plugins/` (outside this repo). After adding a plugin to `tmux/tmux.conf`, install with `prefix + I` inside a tmux session.

## Skills

- `tmux-reference`: load when working with any tmux code in this repo
