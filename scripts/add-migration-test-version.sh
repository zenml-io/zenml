#!/bin/bash
set -e
set -x
set -o pipefail

# Check if both old and new version arguments are provided
if [ $# -ne 2 ]; then
    echo "Error: Incorrect number of arguments. Usage: $0 <old_version> <new_version>"
    exit 1
fi

OLD_VERSION=$1
NEW_VERSION=$2

# Fetch the last changes in the alembic history
ALEMBIC_HISTORY=$(alembic history | head -n 1)

# Check if the first line starts with the old version
if [[ $ALEMBIC_HISTORY == "$OLD_VERSION"* ]]; then
    echo "Alembic history starts with $OLD_VERSION. No changes needed."
    exit 0
else
    # Branch off
    NEW_BRANCH="feature/adding-$NEW_VERSION-to-the-migration-tests"
    git checkout -b "$NEW_BRANCH"

    # Add the new version to the VERSIONS list
    sed -i '' "/^VERSIONS=(.*)$/s/)/ \"$NEW_VERSION\")/" scripts/test-migrations.sh
    echo "Added new version $NEW_VERSION to scripts/test-migrations.sh"

    # Add, commit and push the new changes
    git add scripts/test-migrations.sh
    git commit -m "Adding the new version to the migration tests."
    git push origin "$NEW_BRANCH"

    # Open up a pull request
    gh pr create --base "develop" --head "$NEW_BRANCH" \
      --title "Add $NEW_VERSION to the migration tests" \
      --body "This PR adds $NEW_VERSION to the list of version in the migration test script." \
      --label "internal"
    exit 0
fi
