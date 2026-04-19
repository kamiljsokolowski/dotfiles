---
name: tmux-reference
description: >
  tmux idioms, config quirks, and dotfiles-specific patterns.
  Load when the conversation involves writing, reviewing, or
  debugging `.conf` files under `tmux/`, scripting tmux CLI
  commands, or any tmux session/window/pane management work.
user-invocable: false
---

# tmux Reference

When working with tmux config or scripts in this repo, apply the rules below.
For dense lookup tables, see `reference/config.md` and `reference/scripting.md`.

## Active Config Facts (tmux/)

- **Prefix:** `C-a` (not default `C-b`)
- **Mode keys:** vi
- **Plugins:** tpm · tmux-sensible · tmux-resurrect · tmux-continuum
- **Known footgun:** `default-terminal "xterm-256color"` in `tmux/tmux.conf:2` is incorrect —
  must be `tmux-256color` inside tmux. See `reference/config.md` → Footguns.

## Rules

- When suggesting config changes, use the correct option scope (`-g`/`-s`/`-wg`/`-p`).
- Prefer stable IDs (`$N`/`@N`/`%N`) over names in scripts — names can change.
- `source-file` accumulates; it does not reset existing options. Flag this when relevant.
- `#(command)` in status strings is async and cached — warn if used for latency-sensitive values.
- When writing `split-window` or `new-window`, default to `-c '#{pane_current_path}'` unless
  a different cwd is explicitly required.

## Reference

| File | Contents |
|------|----------|
| `reference/config.md` | Option scopes, key options table, format strings, style syntax, conditionals, footguns |
| `reference/scripting.md` | CLI commands, key bindings, targets, idiomatic patterns, TPM, scripting cheatsheet |
