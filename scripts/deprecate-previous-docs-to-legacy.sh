#!/bin/bash
set -e
set -x
set -o pipefail

# Constants
FILE="docs/book/introduction.md"

# Check if both old and new version arguments are provided
if [ $# -ne 2 ]; then
    echo "Error: Incorrect number of arguments. Usage: $0 <old_version> "
    exit 1
fi

# Fetch the old version
OLD_VERSION=$1

# Create a new branch
NEW_BRANCH="docs/adding-$OLD_VERSION-to-the-legacy-docs"
git checkout -b "$NEW_BRANCH"

# Create the new URL
LEGACY_URL="https://zenml-io.gitbook.io/zenml-legacy-documentation/v/${OLD_VERSION}/"

# Add the old version card to the table
sed -i "/<\/tbody>/i<tr><td>${OLD_VERSION}</td><td></td><td></td><td><a href=${LEGACY_URL}>${LEGACY_URL}</a></td></tr>" "$FILE"

# Add, commit, push and PR
git add $FILE
git commit -m "Deprecating the docs for version ${OLD_VERSION} to the legacy docs."
git push origin "$NEW_BRANCH"

gh pr create --base "docs/legacy-docs-page" --head "$NEW_BRANCH" \
  --title "Deprecate $NEW_VERSION docs to the legacy docs" \
  --body "This PR adds $NEW_VERSION to the legacy docs table and links it properly." \
  --label "internal"
