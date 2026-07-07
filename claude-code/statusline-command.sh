#!/bin/bash

# Read JSON input from stdin
input=$(cat)

# Extract values from JSON
model=$(echo "$input" | jq -r '.model.display_name')
cwd=$(echo "$input" | jq -r '.workspace.current_dir')

# Get directory name
dir=$(basename "$cwd")

# Get git branch and status (skip optional locks for performance)
if git -C "$cwd" rev-parse --git-dir > /dev/null 2>&1; then
    branch=$(git -C "$cwd" branch --show-current 2>/dev/null || echo "detached")
    
    # Check if working tree is clean (skip optional locks)
    if git -C "$cwd" diff-index --quiet HEAD -- 2>/dev/null; then
        git_status=""
    else
        git_status=" *"
    fi
    
    git_info=" on $(printf '\033[35m')$branch$(printf '\033[0m')$git_status"
else
    git_info=""
fi

# Build status line
printf "$(printf '\033[36m')%s$(printf '\033[0m') in $(printf '\033[33m')%s$(printf '\033[0m')%s" "$model" "$dir" "$git_info"
