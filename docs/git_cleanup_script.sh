#!/usr/bin/env bash
# docs/git_cleanup_script.sh
# Git cleanup script to untrack temporary sample render outputs from version control.

echo "Running repository hygiene cleanup..."
git rm --cached -f backend/app/pipeline/render/docker_output.html 2>/dev/null || true
git rm --cached -f backend/app/pipeline/render/langchain_output.html 2>/dev/null || true
echo "Cleanup completed successfully!"
