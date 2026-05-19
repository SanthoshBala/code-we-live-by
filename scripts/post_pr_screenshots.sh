#!/usr/bin/env bash
# Posts screenshots of frontend pages to a GitHub PR.
# Usage: bash scripts/post_pr_screenshots.sh <PR_NUMBER> [/path1] [/path2] ...
# Requires: dev server running on localhost:3000, gh CLI authenticated, npx

set -euo pipefail

PR_NUMBER="${1:?Usage: $0 <PR_NUMBER> [/path1] [/path2] ...}"
shift
PATHS=("${@:- /}")

# Verify gh is authenticated
if ! gh auth status &>/dev/null; then
    echo "Error: gh CLI not authenticated. Run: gh auth login" >&2
    exit 1
fi

# Verify dev server is reachable
if ! curl -sf http://localhost:3000 -o /dev/null; then
    echo "Error: Dev server not responding on http://localhost:3000" >&2
    echo "Run: cd frontend && npm run dev" >&2
    exit 1
fi

# Install Playwright browser if not already present
npx --yes playwright install chromium --with-deps &>/dev/null

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

echo "Taking screenshots..."
FILES=()
ENTRIES=()
for path in "${PATHS[@]}"; do
    slug=$(echo "$path" | sed 's|^/||; s|/|-|g')
    slug="${slug:-home}"
    output="${TMPDIR}/${slug}.png"

    if npx playwright screenshot "http://localhost:3000${path}" "$output" --full-page 2>/dev/null; then
        echo "  OK  http://localhost:3000${path}"
        FILES+=("$output")
        ENTRIES+=("${path}:${slug}")
    else
        echo "  SKIP  http://localhost:3000${path} (page not reachable)" >&2
    fi
done

if [ ${#FILES[@]} -eq 0 ]; then
    echo "No screenshots captured." >&2
    exit 1
fi

# Upload all screenshots to a single public gist
echo "Uploading to GitHub Gist..."
GIST_URL=$(gh gist create --public "${FILES[@]}" --desc "Screenshots for PR #${PR_NUMBER}")
GIST_ID="${GIST_URL##*/}"
GH_USER=$(gh api user -q .login)

# Build PR comment body
BODY="## Screenshots\n\n"
for entry in "${ENTRIES[@]}"; do
    path="${entry%%:*}"
    slug="${entry##*:}"
    raw_url="https://gist.githubusercontent.com/${GH_USER}/${GIST_ID}/raw/${slug}.png"
    BODY+="**\`${path:-/}\`**\n![Screenshot of ${path:-/}](${raw_url})\n\n"
done

gh pr comment "$PR_NUMBER" --body "$(printf "%b" "$BODY")"
echo "Posted screenshots to PR #${PR_NUMBER} — gist: ${GIST_URL}"
