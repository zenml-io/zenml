# ZenML Docs

ZenML is an extensible, open-source MLOps framework for creating production-ready Machine Learning pipelines - in a 
simple way.

## Usage

### Building the docs

If you'd like to develop on and build the ZenML Docs, you should:

- Clone this repository
- Run `pip install -r requirements.txt` (it is recommended you do this within a virtual environment)
- `cd docs`
- (Recommended) Remove the existing `book/_build/` directory
- Run `jupyter-book build book/`

A fully-rendered HTML version of the docs will be built in `book/_build/html/`.

### Building the Sphinx API docs

If you'd like to generate a local build of the Sphinx API docs, you should:

- Clone this repository
- Run `pip install apache-airflow~=2.2.0 gcsfs~=2021.9.0 click~=8.0.3
  torch~=1.10.0 facets-overview~=1.0.0 plotly~=5.4.0 pytorch_lightning
  scikit-learn tensorflow ipython`
- Run `poetry run bash scripts/generate-docs.sh` from the root of the `zenml`
  repository.


### Hosting the book

The html version of the docs is hosted on the `gh-pages` branch of this repo. A GitHub actions workflow has been 
created that automatically builds and pushes the book to this branch on a push or pull request to main.

If you wish to disable this automation, you may remove the GitHub actions workflow and build the book manually by:

- Navigating to your local build; and running,
- `ghp-import -n -p -f book/_build/html`

This will automatically push your build to the `gh-pages` branch. More information on this hosting process can be 
found [here](https://galdin.dev/blog/publishing-gitbook-to-github-pages/).

## Contributors

We welcome and recognize all contributions. You can see a list of current contributors in the 
[contributors tab](https://github.com/zenml-io/zenml/graphs/contributors).

## Credits

This project is created using the excellent open source [Jupyter Book project](https://jupyterbook.org/) and the 
[executablebooks/cookiecutter-jupyter-book template](https://github.com/executablebooks/cookiecutter-jupyter-book).
