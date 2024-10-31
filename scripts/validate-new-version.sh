#!/bin/bash
set -e
set -o pipefail

# Constants
LABEL_BREAKING_CHANGE="breaking-change"

# Check if the planned version is passed as an argument
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <new_planned_version>"
  exit 1
fi

# Input: new planned version
PLANNED_VERSION="$1"

# Check if the version fits the SemVer formatting
if [[ ! "$PLANNED_VERSION" =~ ^[0-9]+(\.[0-9]+){2}$ ]]; then
  echo "::error::Error: Invalid version format '$PLANNED_VERSION'. The version must be in the format X.X.X (e.g., 0.4.0, 1.21.51)."
  exit 1
fi

# Get the latest release information
LATEST_RELEASE=$(gh release view --json tagName,publishedAt -q '{tag: .tagName, date: .publishedAt}')

# Extract the tag and date from the latest release JSON
TAG=$(echo "$LATEST_RELEASE" | jq -r .tag)
TAG_DATE=$(echo "$LATEST_RELEASE" | jq -r .date)

# Check if the latest release information was retrieved successfully
if [ "$TAG" == "null" ]; then
  echo "No releases found."
  exit 1
fi

# Parse the latest tag for versioning
IFS='.' read -r MAJOR MINOR PATCH <<< "$TAG"
IFS='.' read -r P_MAJOR P_MINOR P_PATCH <<< "$PLANNED_VERSION"

# List PRs merged after the latest release date and filter by breaking change label
PRS=$(gh pr list --search "is:merged merged:>$TAG_DATE label:$LABEL_BREAKING_CHANGE base:develop" --json number,title)

# Check if the PRs list for breaking changes is empty
if [ -z "$PRS" ]; then
  IDEAL_NEW_VERSION="$MAJOR.$MINOR.$((PATCH + 1))"

  # Warn in case of a mismatch
  if [ "$PLANNED_VERSION" != "$IDEAL_NEW_VERSION" ]; then
    echo "::warning::Warning: The new planned version '$PLANNED_VERSION' is not the same as the ideal version '$IDEAL_NEW_VERSION'."
  fi
else
  IDEAL_NEW_VERSION="$MAJOR.$((MINOR + 1)).0"

  # Fail in case of a mismatch
  if [ "$P_MINOR" -le "$MINOR" ] && [ "$P_MAJOR" -le "$MAJOR" ]; then
    PR_NUMBERS=$(echo "$PRS" | jq -r 'map("\(.number):\(.title)") | join(", ")')
    echo "::error::Error: There are PRs ($PR_NUMBERS) with breaking changes merged after the release '$TAG'. In this case, the new ideal version is '$IDEAL_NEW_VERSION' instead of '$PLANNED_VERSION'."""
    exit 1
  fi

  if [ "$PLANNED_VERSION" != "$IDEAL_NEW_VERSION" ]; then
    echo "::warning::Warning: The new planned version '$PLANNED_VERSION' is not the same as the ideal version '$IDEAL_NEW_VERSION'. Please, make sure this '$PLANNED_VERSION' is selected on purpose."
  fi

fi
