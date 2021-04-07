# ZenML Docs

ZenML is an extensible, open-source MLOps framework for creating production-ready Machine Learning pipelines - in a simple way.

## Usage

### Building the docs

If you'd like to develop on and build the ZenML Docs, you should:

* Clone this repository and run
* Run `pip install -r requirements.txt` \(it is recommended you do this within a virtual environment\)
* `cd docs`
* \(Recommended\) Remove the existing `book/_build/` directory
* Run `jupyter-book build book/`

A fully-rendered HTML version of the docs will be built in `book/_build/html/`.

### Hosting the book

The html version of the docs is hosted on the `gh-pages` branch of this repo. A GitHub actions workflow has been created that automatically builds and pushes the book to this branch on a push or pull request to main.

If you wish to disable this automation, you may remove the GitHub actions workflow and build the book manually by:

* Navigating to your local build; and running,
* `ghp-import -n -p -f book/_build/html`

This will automatically push your build to the `gh-pages` branch. More information on this hosting process can be found [here](https://book.org/publish/gh-pages.html#manually-host-your-book-with-github-pages).

## Contributors

We welcome and recognize all contributions. You can see a list of current contributors in the [contributors tab](https://github.com/maiot-io/zenml_docs/graphs/contributors).

## Credits

This project is created using the excellent open source [Jupyter Book project](https://book.org/) and the [executablebooks/cookiecutter-jupyter-book template](https://github.com/executablebooks/cookiecutter-jupyter-book).

