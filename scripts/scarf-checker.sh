#!/bin/bash

# Text to be searched in each file
search_text='https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc'

# Flag to track if error is found
error_found=0

# Find all .md files in ./docs/book, excluding toc.md
while IFS= read -r file; do
    # Check if the file contains the search text
    if ! grep -qF "$search_text" "$file"; then
        echo "Error: File '$file' does not contain the scarf snippet."
        error_found=1
    fi
done < <(find docs/book -type f -name '*.md' ! -name 'toc.md')

# Exit with error if any file did not contain the text
if [ "$error_found" -eq 1 ]; then
    exit 1
fi

echo "All files contain the scarf snippet."
