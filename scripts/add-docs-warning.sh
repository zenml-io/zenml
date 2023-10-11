#!/bin/bash
set -e
set -x
set -o pipefail

# Define the function to process each version
process_version() {
    version=$1
    echo "Processing version $version..."
    
    # Checkout and update the release branch
    git checkout "release/$version"
    git pull origin "release/$version"
    
    # Create a new branch for the updates
    new_branch="backport/automated-update-version-$version-docs"
    git checkout -b "$new_branch"
    
    # Run the Python script to update the documentation
    python3 scripts/add-docs-warning.py

    # Commit and push the updates
    find docs/book -name '*.md' -exec git add {} +
    git commit -m "Update old docs with warning message"
    git push origin "$new_branch"
    
    # Open a Pull Request
    gh pr create --base "release/$version" --head "$new_branch" \
        --title "Add warning header to docs for version $version" \
        --body "This PR updates the documentation for version $version with the warning message to be displayed on Gitbook." \
        --label "documentation" --label "backport" --label "internal"
    
    # Pause for 5 seconds
    sleep 5
}

versions=$@

# Process each version
for version in $versions; do
    process_version $version
done
