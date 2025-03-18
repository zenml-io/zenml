# ZenML Docs

## General documentation

We write our [documentation](https://docs.zenml.io/) in Markdown files and use [GitBook](https://www.gitbook.com/) to build it.
The documentation source files can be found in this repository at `docs/book`

* You can edit the docs by simply editing the markdown files. Once the changes
  get merged into main, the docs will be automatically refreshed. (Note: you
  might need to refresh your browser.)
* If you're adding a new page, make sure to add a reference to it inside the tables of contents `docs/book/toc.md`
* Make sure to be consistent with the existing docs (similar style/messaging, reuse existing images if they fit your use case)

## SDK Docs

The ZenML SDK docs are generated from our Python docstrings using [mkdocs](https://www.mkdocs.org/). 
The SDK docs will be automatically updated each release using a Github workflow and can be found 
at[https://sdkdocs.zenml.io](https://sdkdocs.zenml.io/).

### Building the SDK Docs locally

To build them locally follow these steps:

* Clone the repository
* Install ZenML and Jinja2 dependencies
```bash
pip3 install -e ".[server,dev]"
pip3 install "Jinja2==3.0.3"
```
* Modify `docs/mkdocs.yml` as follows:
```yaml
watch:
  - ../src/zenml
```
```yaml
watch:
  - src/zenml
```
* Run `python3 docs/mkdocstrings_helper.py`
* Run:
```bash
rm -rf src/zenml/zen_stores/migrations/env.py
rm -rf src/zenml/zen_stores/migrations/versions
rm -rf src/zenml/zen_stores/migrations/script.py.mako
```
* Run `mkdocs serve -f docs/mkdocs.yml -a localhost:<PORT>` from the repository root - 
running it from elsewhere can lead to unexpected errors. This script will compose the docs hierarchy
and serve it (http://127.0.0.1:<PORT>/).

## Link Checker Tool

The `link_checker.py` script is a utility tool for managing and validating links in our documentation.
It helps maintain the quality of our documentation by:

* Finding broken or outdated links
* Converting relative links to absolute URLs
* Validating link accessibility
* Supporting both directory-wide and file-specific scanning

### Usage

The script supports several modes of operation:

```bash
# Find all links containing 'docs.zenml.io' in a directory
python link_checker.py --dir docs/book --substring docs.zenml.io

# Check specific files for links containing 'how-to'
python link_checker.py --files file1.md file2.md --substring how-to

# Preview link replacements without making changes
python link_checker.py --files file1.md --replace-links --dry-run

# Replace and validate links
python link_checker.py --files file1.md --replace-links --validate-links

# Transform paths using custom URL mappings
python link_checker.py --dir docs/book --replace-links --url-mapping user-guide=user-guides
```

### Features

1. **Link Detection**:
   - Scans for various link types (inline, reference-style, HTML, bare URLs)
   - Supports substring-based filtering
   - Works with both directories and individual files

2. **Link Transformation**:
   - Converts relative documentation links to absolute URLs
   - Handles README.md files and various link formats
   - Preserves fragments and query parameters
   - Supports custom URL path mappings to transform specific path segments

3. **Link Validation**:
   - Validates links via HTTP requests
   - Parallel validation for better performance
   - Detailed error reporting

### Requirements

For link validation functionality, the `requests` package is required:
```bash
pip install requests
```

## Contributors

We welcome and recognize all contributions. You can see a list of current contributors [here](https://github.com/zenml-io/zenml/graphs/contributors).
