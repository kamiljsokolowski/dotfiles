# tmux Scripting & Commands Reference

## CLI Commands

| Command | Description |
|---------|-------------|
| `tmux new -s NAME` | New named session |
| `tmux new -As NAME` | Attach if exists, else create |
| `tmux ls` | List sessions |
| `tmux a -t NAME` | Attach to named session |
| `tmux a -d -t NAME` | Attach, detach all other clients |
| `tmux kill-session -t NAME` | Kill named session |
| `tmux kill-session -a` | Kill all except current |
| `tmux kill-server` | Kill everything |
| `tmux source ~/.tmux.conf` | Reload config |
| `tmux source-file -n ~/.tmux.conf` | Syntax-check without applying |
| `tmux show -g` / `-s` / `-wg` | Show session / server / window options |
| `tmux list-keys` | All key bindings |
| `tmux info` | Server/session/window/pane state |
| `tmux display-message -p '#{pane_id}'` | Print format to stdout |

## Key Bindings (prefix = `C-a` in this config)

### Sessions
| Binding | Action |
|---------|--------|
| `prefix $` | Rename session |
| `prefix d` | Detach |
| `prefix s` | Tree view (sessions) |
| `prefix (` / `)` | Previous / next session |
| `prefix D` | Choose client to detach |

### Windows
| Binding | Action |
|---------|--------|
| `prefix c` | New window |
| `prefix ,` | Rename window |
| `prefix &` | Kill window (confirm) |
| `prefix n` / `p` | Next / previous window |
| `prefix l` | Last active window |
| `prefix 0–9` | Select by index |
| `prefix '` | Prompt for window index |
| `prefix .` | Move window |
| `prefix w` | Tree view (windows) |

### Panes
| Binding | Action |
|---------|--------|
| `prefix %` | Split → left/right (vertical divider) |
| `prefix "` | Split → top/bottom (horizontal divider) |
| `prefix x` | Kill pane |
| `prefix z` | Toggle zoom |
| `prefix !` | Break pane into its own window |
| `prefix q` | Show pane numbers; type to select |
| `prefix o` | Cycle panes |
| `prefix ;` | Last active pane |
| `prefix {` / `}` | Swap with prev / next pane |
| `prefix C-o` | Rotate panes in window |
| `prefix Space` | Cycle layouts |
| `prefix m` / `M` | Mark / unmark pane |
| `prefix h/j/k/l` | Select pane (this config; replaces arrows) |
| `prefix C-←→↑↓` | Resize 1 cell |
| `prefix M-←→↑↓` | Resize 5 cells |

### Layouts (`prefix M-1` through `M-5`)
`even-horizontal` · `even-vertical` · `main-horizontal` · `main-vertical` · `tiled`

### Copy Mode (vi keys — set in this config)
| Binding | Action |
|---------|--------|
| `prefix [` | Enter copy mode |
| `prefix ]` | Paste top buffer |
| `prefix =` | Choose buffer to paste |
| `prefix PgUp` | Enter copy mode, scroll up |
| `q` | Exit |
| `h/j/k/l` | Move cursor |
| `w` / `b` | Word forward / backward |
| `v` | Begin selection |
| `y` or `Enter` | Copy selection and exit |
| `Esc` | Clear selection |
| `/` / `?` | Search forward / backward |
| `n` / `N` | Next / previous match |
| `g` / `G` | Top / bottom of history |

### Alerts
| Binding | Action |
|---------|--------|
| `prefix M-n` | Next window with alert |
| `prefix M-p` | Previous window with alert |

## Targets

Syntax: `session:window.pane` — all parts optional, resolved from current context.

| Form | Matches |
|------|---------|
| `mysession` | Prefix match on session name |
| `=mysession` | Exact session name |
| `$3` | Session by ID |
| `@5` | Window by ID |
| `%11` | Pane by ID |
| `{last}` / `!` | Last active window/pane |
| `{next}` / `+` | Next |
| `{previous}` / `-` | Previous |
| `{top}` `{bottom}` `{left}` `{right}` | Positional pane |
| `{top-left}` `{bottom-right}` etc. | Corner pane |
| `{up-of}` `{down-of}` `{left-of}` `{right-of}` | Relative pane |
| `{start}` / `^` | First window |
| `{end}` / `$` | Last window |

## Idiomatic Patterns

### Split preserving cwd
```conf
bind '"' split-window -c '#{pane_current_path}'
bind '%' split-window -h -c '#{pane_current_path}'
bind c new-window -c '#{pane_current_path}'
```

### Create or attach (script-safe)
```bash
tmux new-session -A -s main
```

### Scripting: capture newly created pane ID
```bash
pane_id=$(tmux split-window -P -F '#{pane_id}' -d)
```

### Scripting: send keys to specific pane
```bash
tmux send-keys -t "$pane_id" 'kubectl get pods' Enter
tmux send-keys -t "$pane_id" -l 'literal text, no key parsing'
```

### Scripting: capture pane output
```bash
tmux capture-pane -pt "$pane_id" -S -          # full history to stdout
tmux capture-pane -pt "$pane_id" -S -100 -E -1 # last 100 lines
# -e  include escape sequences
# -J  join wrapped lines (preserves word boundaries)
# -N  preserve trailing spaces
```

### Scripting: list panes with custom format
```bash
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{pane_current_command}'
```

### Reload config
```conf
bind r source-file ~/.tmux.conf \; display 'Config reloaded'
```

### Broadcast to all panes
```conf
bind S setw synchronize-panes \; display 'Sync toggled'
```

### Toggle pane logging
```conf
bind P pipe-pane -o 'cat >>~/tmux-pane-#W.log' \; display 'Logging toggled'
```

### Modal key table
```conf
bind -Tmytable x list-keys              # binding inside custom table
bind -Troot C-x switch-client -Tmytable # enter custom table from root
```

### Pipe pane I/O
```bash
tmux pipe-pane 'cat >~/mypanelog'   # redirect output to file
tmux pipe-pane                       # stop piping (no args)
tmux pipe-pane -I 'cat somefile'    # send file contents to pane as input
```

### Run shell command in background pane
```bash
tmux split-window -d 'long-running-command'   # -d keeps focus on current pane
```

### Detect if inside tmux
```bash
[ -n "$TMUX" ] && echo "inside tmux"
echo "$TMUX_PANE"   # stable pane ID, e.g. %11
```

## TPM (Tmux Plugin Manager)

| Action | Method |
|--------|--------|
| Declare plugin | `set -g @plugin 'owner/repo'` in `tmux.conf` |
| Install plugins | `prefix + I` |
| Update plugins | `prefix + U` |
| Remove unlisted | `prefix + Alt+u` |

Plugins install to `~/.tmux/plugins/` (outside this repo by design).
TPM must be initialized at the **very bottom** of `tmux.conf`:
```conf
run '~/.tmux/plugins/tpm/tpm'
```
