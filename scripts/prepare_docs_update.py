import argparse
import os
import zipfile


def prepare_docs_update(source):
    # Create a zip file
    with zipfile.ZipFile("docs_data.zip", "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source)
                zipf.write(file_path, arcname)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare ZenML docs update")
    parser.add_argument("--source", required=True, help="Source directory")

    args = parser.parse_args()
    prepare_docs_update(args.source)
