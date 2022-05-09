# ZenML Docs

## General documentation

We write our [documentation](https://docs.zenml.io/) in Markdown files and use [Gitbook](https://www.gitbook.com/) to build it.
The documentation source files can be found in this repository at `docs/book`

* You can edit the docs by simply editing the markdown files. Once the changes
  get merged into main, the docs will be automatically refreshed. (Note: you
  might need to refresh your browser.)
* If you're adding a new page, make sure to add a reference to it inside the tables of contents `docs/book/toc.md`
* Make sure to be consistent with the existing docs (similar style/messaging, reuse existing images if they fit your use case)

## API Docs

The ZenML API docs are generated from our Python docstrings using [mkdocs](https://www.mkdocs.org/). 
The API docs will be automatically updated each release using a Github workflow and can be found 
at[https://apidocs.zenml.io](https://apidocs.zenml.io/).

### Building the API Docs locally

To build them locally follow these steps:

* Clone the repository
* Install ZenML and all dependencies
```python
poetry install
poetry run zenml integration install -y
poetry run pip install click~=8.0.3 typing-extensions~=3.10.0.2
```
* Run `poetry run bash scripts/serve_api_docs.sh` from the repository root - 
running it from elsewhere can lead to unexpected errors. This script will compose the docs hierarchy
and serve it (default location is http://127.0.0.1:8000/).
* In case port 8000 is taken you can also manually go into the docs folder within your terminal and
run `mkdocs serve` from there

The generated `.md` files will be inside the directory `docs/mkdocs/`

## Contributors

We welcome and recognize all contributions. You can see a list of current contributors [here](https://github.com/zenml-io/zenml/graphs/contributors).
