Hello there! This is the repository for ZenML. ZenML is an open-source framework to create production-grade MLOps pipelines. 
If you would like to see the published pip package can be found [here](https://pypi.org/project/zenml).

This guide is intended to help you install ZenML from source, primarily for development purposes.

# Install from source

## Clone the repo

```bash
git clone https://github.com/zenml-io/zenml.git

# or ssh
git clone git@github.com:zenml-io/zenml.git
```

## Create a virtualenv

To install the local ZenML files in an isolated environment, first create and activate
a virtualenv by running 

```bash
python -m venv <VIRTUALENV_NAME>
source <VIRTUALENV_NAME>/bin/activate
```

## Upgrade pip

Installing editable packages from a `pyproject.toml` using pip requires a new version
of pip, so we first make sure pip is up to date:

```bash
pip install --upgrade pip
```

## Install dependencies

Then from the root of the package:
```bash
pip install -e ".[server,dev]"
```

This will install the ZenML package as an editable source (including all dev-dependencies), so now you should be good to go with 
that virtualenv. 

# CLI
After doing the above, you should have the `zenml` CLI installed in your virtualenv. You can check this with:

```bash
zenml version
```

## Enabling auto completion on the CLI

For Bash, add this to ~/.bashrc:
```bash
eval "$(_ZENML_COMPLETE=bash_source zenml)"
```

For Zsh, add this to ~/.zshrc:
```bash
eval "$(_ZENML_COMPLETE=zsh_source zenml)"
```

For Fish, add this to ~/.config/fish/config.fish:
```bash
_ZENML_COMPLETE=fish_source zenml | source
```

For faster shell startup, write the generated script to a file and source that
file from your shell configuration instead of evaluating the command on every
new shell. Static command and option completion is local. Resource-name
completion may query your configured ZenML store or server and returns no
dynamic suggestions when the backend is unavailable.

## Authors

* **ZenML GmbH** - [Company Website](https://zenml.io) - [Product Website](https://zenml.io) - [ZenML Docs](https://docs.zenml.io)
