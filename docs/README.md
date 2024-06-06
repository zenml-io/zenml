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

## Contributors

We welcome and recognize all contributions. You can see a list of current contributors [here](https://github.com/zenml-io/zenml/graphs/contributors).
