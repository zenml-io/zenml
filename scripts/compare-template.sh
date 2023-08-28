#!/bin/bash

folder1="examples/e2e"
folder2="examples/.tmp_compare_e2e"
exit_code=0 

mkdir $folder2
zenml init --path "$folder2" --template e2e_batch --template-with-defaults
sh scripts/format.sh

find "$folder1" -type f -print0 | while IFS= read -r -d '' file1; do
    # Get the relative path of the file1 within folder1
    relative_path="${file1#$folder1/}"
    
    # Construct the corresponding path in the second folder
    file2="$folder2/$relative_path"
    
    # Compare the contents of the two files
    if [ -f "$file2" ] && ! cmp -s "$file1" "$file2"; then
        echo "Files $file1 and $file2 have different content."
        exit_code=1  # Set exit code to 1 (mismatch detected)
    fi
done

rm -rf $folder2

exit $exit_code