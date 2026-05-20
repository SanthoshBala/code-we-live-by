#!/usr/bin/env bash
# Posts screenshots of frontend pages to a GitHub PR.
# Usage: bash scripts/post_pr_screenshots.sh <PR_NUMBER> [/path1] [/path2] ...
#
# Requires:
#   - Backend running on port 8000 (cd backend && uv run uvicorn app.main:app --port 8000)
#   - Frontend dev server on port 3000 (cd frontend && npm run dev)
#     If port 3000 is occupied: lsof -ti :3000 | xargs kill -9
#   - gh CLI authenticated
#   - npx available

set -euo pipefail

PR_NUMBER="${1:?Usage: $0 <PR_NUMBER> [/path1] [/path2] ...}"
shift
PATHS=("${@:- /}")

# Verify gh is authenticated
if ! gh auth status &>/dev/null; then
    echo "Error: gh CLI not authenticated. Run: gh auth login" >&2
    exit 1
fi

# Verify frontend dev server is reachable on port 3000
if ! curl -sf http://localhost:3000 -o /dev/null; then
    echo "Error: Frontend not responding on http://localhost:3000" >&2
    echo "  Start with: cd frontend && npm run dev" >&2
    echo "  If port 3000 is occupied: lsof -ti :3000 | xargs kill -9" >&2
    exit 1
fi

# Install Playwright browser if not already present
npx --yes playwright install chromium --with-deps &>/dev/null

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

echo "Taking screenshots..."
ENTRY_PATHS=()
ENTRY_SLUGS=()
ENTRY_FILES=()

for path in "${PATHS[@]}"; do
    # Sanitize path to a filename-safe slug (collapse any non-alphanumeric run to -)
    slug=$(echo "$path" | sed 's|^/||; s|[^a-zA-Z0-9._-]|-|g; s|-\+|-|g; s|-$||')
    slug="${slug:-home}"
    output="${TMPDIR}/${slug}.png"

    if npx playwright screenshot "http://localhost:3000${path}" "$output" \
            --full-page --wait-for-timeout 2000 2>/dev/null; then
        echo "  OK  http://localhost:3000${path}"
        ENTRY_PATHS+=("$path")
        ENTRY_SLUGS+=("$slug")
        ENTRY_FILES+=("$output")
    else
        echo "  SKIP  http://localhost:3000${path} (page not reachable)" >&2
    fi
done

if [ ${#ENTRY_PATHS[@]} -eq 0 ]; then
    echo "No screenshots captured." >&2
    exit 1
fi

# Derive repo and PR head branch
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
BRANCH=$(gh pr view "$PR_NUMBER" --json headRefName -q .headRefName)

echo "Uploading screenshots to ${REPO}@${BRANCH}..."
COMMIT_SHAS=()
REMOTE_PATHS=()

for i in "${!ENTRY_PATHS[@]}"; do
    slug="${ENTRY_SLUGS[$i]}"
    file="${ENTRY_FILES[$i]}"
    remote_path=".github/pr-screenshots/pr-${PR_NUMBER}-${slug}.png"

    response=$(gh api --method PUT \
        "/repos/${REPO}/contents/${remote_path}" \
        -f "message=chore: add PR #${PR_NUMBER} screenshot" \
        -f "content=$(base64 < "$file")" \
        -f "branch=${BRANCH}")

    commit_sha=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin)['commit']['sha'])")
    COMMIT_SHAS+=("$commit_sha")
    REMOTE_PATHS+=("$remote_path")
    echo "  uploaded  ${remote_path}"
done

# Build comment using commit-SHA-pinned raw URLs. These URLs remain valid even
# after the files are deleted from the branch, because the commit is still
# reachable through the branch history.
BODY="## Screenshots\n\n"
for i in "${!ENTRY_PATHS[@]}"; do
    path="${ENTRY_PATHS[$i]}"
    raw_url="https://raw.githubusercontent.com/${REPO}/${COMMIT_SHAS[$i]}/${REMOTE_PATHS[$i]}"
    BODY+="**\`${path:-/}\`**\n![Screenshot of ${path:-/}](${raw_url})\n\n"
done

gh pr comment "$PR_NUMBER" --body "$(printf "%b" "$BODY")"
echo "Posted screenshots to PR #${PR_NUMBER}"

# Clean up the uploaded files from the branch. The comment URLs above are
# pinned to their commit SHAs and will continue to resolve after deletion.
echo "Cleaning up uploaded files..."
for i in "${!REMOTE_PATHS[@]}"; do
    remote_path="${REMOTE_PATHS[$i]}"
    blob_sha=$(gh api "/repos/${REPO}/contents/${remote_path}?ref=${BRANCH}" \
        -q .sha 2>/dev/null || true)
    if [ -n "$blob_sha" ]; then
        gh api --method DELETE \
            "/repos/${REPO}/contents/${remote_path}" \
            -f "message=chore: remove PR #${PR_NUMBER} screenshot" \
            -f "sha=${blob_sha}" \
            -f "branch=${BRANCH}" &>/dev/null
        echo "  removed  ${remote_path}"
    fi
done
