#!/usr/bin/env bash
#
# Deploy the Google Forms package into the eduwonder site (eduwonderlab /
# neft-teacher-pipeline, served at https://eduwonderlab.vercel.app).
#
# What it does:
#   1. Clones the eduwonder repo (or uses an existing checkout via $REPO_DIR).
#   2. Copies the forms page + data into  <repo>/google-forms/  and also writes
#      <repo>/google-forms/index.html  so /google-forms/ serves the page directly.
#   3. Adds a discoverable "Google Forms" card + top button to GITHUB_DASHBOARD.html
#      (idempotent — safe to re-run).
#   4. Commits to branch  add-google-forms  and pushes.
#
# Usage:
#   ./deploy-to-eduwonder.sh                      # clone over HTTPS and push
#   REPO_DIR=/path/to/eduwonder ./deploy-to-eduwonder.sh   # use an existing clone
#   REPO_URL=...  BRANCH=...  ./deploy-to-eduwonder.sh     # override defaults
#
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_URL="${REPO_URL:-https://github.com/Baltimoreteacher1/eduwonderlab.git}"
BRANCH="${BRANCH:-add-google-forms}"

# 1. obtain the repo
if [ -n "${REPO_DIR:-}" ]; then
  echo "Using existing checkout: $REPO_DIR"
else
  REPO_DIR="$(mktemp -d)/eduwonder"
  echo "Cloning $REPO_URL ..."
  git clone "$REPO_URL" "$REPO_DIR"
fi
cd "$REPO_DIR"
git checkout -B "$BRANCH"

# 2. copy the package
DEST="$REPO_DIR/google-forms"
mkdir -p "$DEST"
for f in forms-index.html forms-data.json question-bank.csv create-forms.gs README.md .gitignore; do
  cp "$SRC_DIR/$f" "$DEST/$f"
done
cp "$SRC_DIR/forms-index.html" "$DEST/index.html"   # so /google-forms/ serves the page
echo "Copied package into $DEST"

# 3. add a dashboard card + top button (idempotent)
DASH="$REPO_DIR/GITHUB_DASHBOARD.html"
if [ -f "$DASH" ]; then
  python3 - "$DASH" <<'PY'
import sys, re
path = sys.argv[1]
html = open(path, encoding="utf-8").read()
if "NEFT_GFORMS" in html:
    print("Dashboard already has the Google Forms link — skipping.")
else:
    button = ('\n        <a class="button secondary" href="./google-forms/" '
              'data-neft="NEFT_GFORMS">\U0001F4DD Google Forms (Notes / Practice / Quiz)</a>')
    html = re.sub(r'(<div class="top-actions">)', r'\1' + button, html, count=1)
    card = ('\n        <article class="card" data-neft="NEFT_GFORMS" '
            'data-tags="google forms quiz notes practice autograded all lessons">\n'
            '          <h3>\U0001F4DD Google Forms — all 74 lessons</h3>\n'
            '          <p>Notes, Practice, and autograded Quiz forms for every Grade 6 '
            'math lesson, with answer keys and feedback.</p>\n'
            '          <a href="./google-forms/">Open the Forms index</a>\n'
            '        </article>')
    html = re.sub(r'(<section class="grid" id="cards">)', r'\1' + card, html, count=1)
    open(path, "w", encoding="utf-8").write(html)
    print("Added Google Forms card + button to the dashboard.")
PY
else
  echo "GITHUB_DASHBOARD.html not found — skipping dashboard link (files still deployed)."
fi

# 4. commit + push
git add google-forms GITHUB_DASHBOARD.html 2>/dev/null || git add google-forms
if git diff --cached --quiet; then
  echo "Nothing to commit — already up to date."
  exit 0
fi
git commit -m "Add Google Forms (Notes / Practice / autograded Quiz) for all 74 lessons"
for i in 1 2 3 4; do
  git push -u origin "$BRANCH" && break || { echo "push retry $i"; sleep $((2**i)); }
done

echo
echo "Pushed branch '$BRANCH'. Open a PR and merge to main; Vercel will deploy to"
echo "https://eduwonderlab.vercel.app/google-forms/"
