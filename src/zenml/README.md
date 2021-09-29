Hello there! This is the repository for ZenML. ZenML is an open-source framework to create production-grade MLOps pipelines. 
If you would like to see the published pip package can be found [here](https://pypi.org/project/zenml).

This guide is intended to help you install ZenML from source, primarily for development purposes.

# Install from source

ZenML uses [poetry](https://python-poetry.org/) for packaging and dependency management. Please make sure you 
install it first before moving ahead.

## Clone the repo

```bash
git clone https://github.com/zenml-io/zenml.git

# or ssh
git clone git@github.com:zenml-io/zenml.git
```

## Create a virtualenv
To install with poetry, first create a virtualenv. Poetry can help with this, but you 
can also use your own virtualenv management tool. Please make sure the Python version is 
between the supported types (currently >=3.6 <9)

```bash
poetry shell
```

## Install dependencies
Then from the root of the package:
```bash
poetry install
```

This will only install non-optional dependencies (i.e. NO integrations). To install all integrations:

```bash
poetry install --extras all
```

If you would like to install the base package and only a few optional dependencies:

```bash
poetry install --extras airflow  # pass in here whatever you'd like
```

Poetry will install the ZenML package as an editable source (including all dev-dependencies), so now you should be good to go with 
that virtualenv. 

## Known quirks
Poetry is still relatively young. If it is not behaving as it should consider doing the following:

* Delete the poetry.lock file and run a fresh install.
* Run `poetry lock`. This will refresh your lock file.
* Run `poetry install` again to make sure you have the latest editable package installed.

# CLI
After doing the above, you should have the `zenml` CLI installed in your virtualenv. You can check this with:

```bash
zenml version
```

If this does not work, you can try:

```bash
poetry run zenml version
```

## Enabling auto completion on the CLI

For Bash, add this to ~/.bashrc:
```bash
eval "$(_zenml_COMPLETE=source_bash zenml)"
```

For Zsh, add this to ~/.zshrc:
```bash
eval "$(_zenml_COMPLETE=source_zsh zenml)"
```

For Fish, add this to ~/.config/fish/completions/foo-bar.fish:
```bash
eval (env _zenml_COMPLETE=source_fish zenml)
```

## Authors

* **ZenML GmbH** - [Company Website](https://zenml.io) - [Product Website](https://zenml.io) - [ZenML Docs](https://docs.zenml.io)