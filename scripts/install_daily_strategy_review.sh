#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
label="com.vnpy.daily-strategy-review"
source_plist="$repo_root/scripts/launchd/$label.plist"
target_dir="$HOME/Library/LaunchAgents"
target_plist="$target_dir/$label.plist"

mkdir -p "$target_dir" "$repo_root/var/strategy_reviews"
cp "$source_plist" "$target_plist"

launchctl bootout "gui/$(id -u)" "$target_plist" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$target_plist"
launchctl enable "gui/$(id -u)/$label"

echo "installed $label -> $target_plist"
echo "daily run: 23:30 local time"
