import os
import argparse


def main(source_repo_path, output_path, code_links_base_url, mint_json_location):
    print(f"Source repo path: {os.path.abspath(source_repo_path)}")
    print(f"Output path: {os.path.abspath(output_path)}")
    print(f"Code links base URL: {code_links_base_url}")
    print(f"mint.json location: {mint_json_location}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Mintlify SDK documentation")
    parser.add_argument("--source_repo_path", default=".", help="Path to the source repository")
    parser.add_argument("--output_path", default="docs/mintlify/lazydocs", help="Path to output the generated documentation")
    parser.add_argument("--code_links_base_url", default="https://github.com/zenml-io/zenml/tree/main/src/zenml", help="Base URL for code links")
    parser.add_argument("--mint_json_location", default="docs/mintlify/mint.json", help="Location of the mint.json file")

    args = parser.parse_args()

    main(args.source_repo_path, args.output_path, args.code_links_base_url, args.mint_json_location)
