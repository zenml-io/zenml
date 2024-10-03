import argparse
import os
import zipfile

def prepare_docs_update(source_dir: str):
    # Create a zip file
    zip_filename = 'docs_data.zip'
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk through the source directory
        for root, _, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, source_dir)

                # Add file to the zip
                try:
                    zipf.write(file_path, relative_path)
                    print(f"Added {relative_path} to the zip file")
                except Exception as e:
                    print(f"Error adding file {file_path} to zip: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare docs update")
    parser.add_argument("--source", required=True, help="Source directory for docs")
    args = parser.parse_args()

    prepare_docs_update(args.source)
    print("Docs data prepared and saved to docs_data.zip")