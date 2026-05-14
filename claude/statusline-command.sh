#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: statusline-command.sh
# Description: Claude Code status line — flat/minimal style with colored text,
#              pipe dividers, and a per-block gradient progress bar.
# Usage: Configured via Claude Code settings as the statusLine command.
#        Reads JSON from stdin; outputs a single-line ANSI-colored string.
# Dependencies: jq, git, awk
# -----------------------------------------------------------------------------
set -euo pipefail

# ── Color palette (256-color indices) ─────────────────────────────────────────
readonly COL_FOLDER=69    # cornflower blue
readonly COL_BRANCH=141   # light purple / violet
readonly COL_MODEL=179    # warm yellow / gold
readonly COL_DIV=240      # dark grey
readonly COL_BAR_TEXT=248 # light grey
readonly BAR_WIDTH=20
readonly COST_MAX_USD=200 # bar fills at $200.00; anything beyond pegs to full

# ── ANSI helpers ──────────────────────────────────────────────────────────────
fg256() { printf '\e[38;5;%sm' "$1"; }
ansi_reset() { printf '\e[0m'; }
ansi_bold() { printf '\e[1m'; }

# ── Gradient color ─────────────────────────────────────────────────────────────
# Returns a 256-color cube index on a green→yellow→red gradient for a 0-100 value.
# Uses the 6x6x6 cube (indices 16-231): R rises, G falls as pct increases.
gradient_color() {
	local pct="${1}" r g
	r=$(awk -v p="${pct}" 'BEGIN { printf "%d", p / 100 * 5 + 0.5 }')
	g=$(awk -v p="${pct}" 'BEGIN { printf "%d", (1 - p / 100) * 5 + 0.5 }')
	printf '%d' $((16 + 36 * r + 6 * g))
}

# ── Gradient color (cost) ─────────────────────────────────────────────────────
# Same formula as gradient_color but with b=5 fixed → cyan→blue→magenta palette.
gradient_color_cost() {
	local pct="${1}" r g
	r=$(awk -v p="${pct}" 'BEGIN { printf "%d", p / 100 * 5 + 0.5 }')
	g=$(awk -v p="${pct}" 'BEGIN { printf "%d", (1 - p / 100) * 5 + 0.5 }')
	printf '%d' $((16 + 36 * r + 6 * g + 5))
}

# ── Context bar ───────────────────────────────────────────────────────────────
# Outputs a colored block bar with "N% left" label.
build_bar() {
	local used_pct="${1}"
	local left_pct filled empty bar i block_pct

	left_pct=$(awk -v p="${used_pct}" 'BEGIN { printf "%.0f", 100 - p }')
	filled=$(awk -v p="${used_pct}" -v w="${BAR_WIDTH}" 'BEGIN { printf "%d", (p / 100) * w + 0.5 }')
	empty=$((BAR_WIDTH - filled))

	bar=""
	for ((i = 1; i <= filled; i++)); do
		block_pct=$(((i * 100) / BAR_WIDTH))
		bar+=$(fg256 "$(gradient_color "${block_pct}")")
		bar+="█"
	done
	bar+=$(fg256 238) # dark grey for empty blocks
	for ((i = 0; i < empty; i++)); do bar+="█"; done
	bar+=$(ansi_reset)

	printf '%s' "[${bar}$(fg256 "${COL_BAR_TEXT}")] ${left_pct}% left$(ansi_reset)"
}

# ── Cost bar ──────────────────────────────────────────────────────────────────
# Outputs a cyan→blue→magenta block bar with formatted dollar amount label.
build_cost_bar() {
	local cost_raw="${1}"
	local cost_pct filled empty bar i block_pct cost_fmt

	# Scale against COST_MAX_USD; cap at 100%
	cost_pct=$(awk -v c="${cost_raw}" -v m="${COST_MAX_USD}" \
		'BEGIN { p = c / m * 100; printf "%.1f", (p > 100) ? 100 : p }')
	filled=$(awk -v p="${cost_pct}" -v w="${BAR_WIDTH}" 'BEGIN { printf "%d", (p / 100) * w + 0.5 }')
	empty=$((BAR_WIDTH - filled))

	bar=""
	for ((i = 1; i <= filled; i++)); do
		block_pct=$(((i * 100) / BAR_WIDTH))
		bar+=$(fg256 "$(gradient_color_cost "${block_pct}")")
		bar+="█"
	done
	bar+=$(fg256 238) # dark grey for empty blocks
	for ((i = 0; i < empty; i++)); do bar+="█"; done
	bar+=$(ansi_reset)

	cost_fmt=$(awk -v c="${cost_raw}" 'BEGIN {
		if (c < 0.001) printf "$%.4f", c
		else if (c < 0.01) printf "$%.3f", c
		else printf "$%.2f", c
	}')

	printf '%s' "[${bar}$(fg256 "${COL_BAR_TEXT}")] ${cost_fmt}$(ansi_reset)"
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
	local input cwd model used_pct cost_raw folder branch div out

	input=$(cat)

	cwd=$(jq -r '.workspace.current_dir // .cwd // ""' <<<"${input}")
	model=$(jq -r '.model.display_name // .model.id // "unknown"' <<<"${input}")
	used_pct=$(jq -r '.context_window.used_percentage // empty' <<<"${input}")
	cost_raw=$(jq -r '.cost.total_cost_usd // empty' <<<"${input}")

	folder=$(basename "${cwd}")
	# git -C handles both normal repos and worktrees; falls back to short SHA on detached HEAD
	branch=$(git -C "${cwd}" symbolic-ref --short HEAD 2>/dev/null ||
		git -C "${cwd}" rev-parse --short HEAD 2>/dev/null ||
		true)

	div="$(ansi_reset)$(fg256 "${COL_DIV}") | $(ansi_reset)"

	out=""
	if [[ -n "${folder}" ]]; then
		out+="$(ansi_bold)$(fg256 "${COL_FOLDER}")${folder}$(ansi_reset)"
	fi
	if [[ -n "${branch}" ]]; then
		out+="${div}$(fg256 "${COL_BRANCH}")${branch}$(ansi_reset)"
	fi
	if [[ -n "${model}" ]]; then
		out+="${div}$(fg256 "${COL_MODEL}")${model}$(ansi_reset)"
	fi
	if [[ -n "${used_pct}" ]]; then
		out+="${div}$(build_bar "${used_pct}")"
	fi
	if [[ -n "${cost_raw}" ]]; then
		out+="${div}$(build_cost_bar "${cost_raw}")"
	fi

	printf '%s' "${out}"
}

main "$@"
