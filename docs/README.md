# ZenML Docs

## General documentation

We write our [documentation](https://docs.zenml.io/) in Markdown files and use [Gitbook](https://www.gitbook.com/) to build it.
The documentation source files can be found in this repository at `docs/book`

* You can edit the docs by simply editing the markdown files. Once the changes get merged into main, the docs will be automatically refreshed. (Might need a hard refresh in your browser)
* If you're adding a new page, make sure to add a reference to it inside the tables of contents `docs/book/toc.md`
* Make sure to be consistent with the existing docs (similar style/messaging, reuse existing images if they fit your use case)

## API Docs

The ZenML API docs are generated from our python docstrings using [Sphinx](https://www.sphinx-doc.org/en/master/). The API docs will be automatically updated each release using a Github workflow and can be found at [https://apidocs.zenml.io](https://apidocs.zenml.io/).

### Building the API Docs locally

To build them locally follow these steps:

* Clone the repository
* Install ZenML and all dependencies
```python
poetry install
poetry run zenml integration install -f
poetry run pip install click~=8.0.3 typing-extensions~=3.10.0.2
```
* Run  `poetry run bash scripts/generate-docs.sh` from the repository root

The generated HTML files will be inside the directory `docs/sphinx_docs/_build/html`

## Contributors

We welcome and recognize all contributions. You can see a list of current contributors [here](https://github.com/zenml-io/zenml/graphs/contributors).
