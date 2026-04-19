# tmux Config Reference

## File Loading Order

```
/etc/tmux.conf
~/.tmux.conf                              # standard location
$XDG_CONFIG_HOME/tmux/tmux.conf          # tmux 3.2+, only if ~/.tmux.conf absent
```

Config loaded once at server start. Changes require `source-file ~/.tmux.conf` or server restart.

## Option Scopes

| Flag | Scope | Example |
|------|-------|---------|
| `set -g OPT VAL` | Session (global) | `set -g history-limit 50000` |
| `set -s OPT VAL` | Server | `set -s escape-time 10` |
| `set -wg OPT VAL` | Window (global) | `set -wg mode-keys vi` |
| `set -p OPT VAL` | Pane | `set -p remain-on-exit on` |
| `set -Fg OPT VAL` | Format-expanded at use time | status strings |

Aliases: `setw` = `set-window-option` = `set -w`

## Key Options

| Option | Scope | Default | Notes |
|--------|-------|---------|-------|
| `escape-time` | server | 500ms | Delay between Esc and M-x. 10–50ms locally; ≥100ms over SSH |
| `default-terminal` | session | `screen` | Must be `tmux-256color` or `screen-*` **inside** tmux — never `xterm-*` |
| `history-limit` | session | 2000 | Per-pane scrollback lines |
| `base-index` | session | 0 | First window number |
| `renumber-windows` | session | off | Auto-close index gaps on window close |
| `mouse` | session | off | All-or-nothing; `on` captures all mouse events |
| `focus-events` | server | off | Pass focus in/out to programs (required by Neovim) |
| `prefix` / `prefix2` | session | `C-b` / — | Primary and optional second prefix |
| `mode-keys` | window | emacs | `vi` for vim-style copy mode |
| `status-keys` | session | emacs | `vi` for vi-style command line |
| `status-interval` | session | 15s | Status bar refresh rate |
| `status-position` | session | bottom | `top` or `bottom` |
| `synchronize-panes` | window | off | Broadcast input to all panes in window |
| `remain-on-exit` | window | off | Keep pane open after process exits |
| `aggressive-resize` | window | off | Resize to smallest *active* client (not all clients) |
| `set-clipboard` | server | external | OSC 52 clipboard: `on`/`external`/`off` |
| `window-size` | session | `latest` (3.3+) | `largest`/`smallest`/`latest`/`manual` |

## Format Strings

Used in `status-left`, `status-right`, `pane-border-format`, `-F` flags, `display-message`.

```
#{session_name}       current session name
#{window_index}       window number
#{window_name}        window name
#{pane_index}         pane number
#{pane_title}         title set by app or select-pane -T
#{pane_current_path}  cwd of active process in pane
#{pane_id}            stable pane ID (%N)
#{session_id}         stable session ID ($N)
#{window_id}          stable window ID (@N)
#(command)            shell command output — async, cached
#[style]              inline style: #[fg=red,bold]
#{?flag,true,false}   conditional
```

Conditional example:
```
#{?window_zoomed_flag,[Z],}   # show [Z] when pane is zoomed
```

## Style Syntax

```
fg=COLOR bg=COLOR bold dim underscore italics reverse default
```

Colors: `black red green yellow blue magenta cyan white`, `colour0`–`colour255`, `#RRGGBB`
True color (`#RRGGBB`) requires `Tc` terminfo override:
```conf
set -ag terminal-overrides ",xterm-256color:Tc"
```

## Config Conditionals (parse-time)

```conf
%if #{==:#{TERM},xterm-256color}
  set -g terminal-overrides ",xterm-256color:Tc"
%elif #{==:#{TERM},screen-256color}
  set -g default-terminal "screen-256color"
%else
  set -g default-terminal "tmux-256color"
%endif
```

`%if` evaluates at parse time; `if-shell` evaluates at execution time.

## Array Options

Options with indexed storage: `command-alias`, `terminal-features`, `terminal-overrides`,
`status-format`, `update-environment`, `user-keys`, hooks.

```conf
set -g status-format[0] 'format for status line 0'
set -ag terminal-features ',xterm-256color:RGB'   # append to next free index
set -g command-alias[100] 'sv=split-window -v'    # define alias
```

## User Options

Prefix with `@` — all are strings, no type restrictions:
```conf
set -g @my_option 'value'       # session scope
set -wg @my_window_opt 'val'    # window scope
```
Plugins use `@plugin_name` by convention.

## Footguns

### `default-terminal` must NOT be `xterm-*` inside tmux
`$TERM` inside tmux must be `tmux-256color` (preferred) or `screen-256color`.
`xterm-*` causes broken italics, display glitches, incorrect capability reporting.
`terminal-overrides` is for the *outer* terminal — separate concern.

```conf
# Correct
set -g default-terminal "tmux-256color"            # TERM inside tmux
set -ag terminal-overrides ",xterm-256color:Tc"    # outer terminal → true color
```

### `source-file` accumulates, does not reset
Re-sourcing appends. `bind-key` overrides are fine (last write wins).
Array options like `@plugin` duplicate on each source — TPM loads plugins twice.
Full reset requires server restart.

### `#(command)` is async and cached
Status bar shell commands run in background; output lags behind.
Not suitable for latency-sensitive values. Refresh bounded by `status-interval`.

### Dashed pane border lines
UTF-8 box-drawing rendered incorrectly on some terminals:
```conf
set -as terminal-overrides ",*:U8=0"
```

### Frozen terminal on attach
Some terminals reject window-title sequences → freeze requiring `kill -9`:
```conf
set -g set-titles off
```

### `automatic-rename` CPU drain
Runs `ps` repeatedly. Disable when idle CPU matters:
```conf
setw -g automatic-rename off
```

### Socket deleted while server runs
`pkill -USR1 tmux` causes server to recreate socket. Sessions survive.

### Mouse is all-or-nothing
`mouse on` captures all events — native text selection lost.
Bypass: hold **Shift** (Linux) or **Option** (macOS/iTerm2).

### Window sizing — padding dots on attach
Pre-3.3: constrained to smallest client.
Fix: `tmux attach -d`, or `set -g window-size largest` (overflow risk on small terminals).
3.3+ default is `latest`.

## Version Notes

| Version | Change |
|---------|--------|
| 3.3 | `window-size latest` became default |
| 3.2 | XDG config path; `prefix /` describe-key |
| 3.1 | `{}` quoting for literal blocks |
| 3.0 | `%if`/`%elif`/`%else`/`%endif` conditionals |
| 2.9 | `window-size` option added |
| 2.1 | `mouse on` unified (replaced per-feature options) |
