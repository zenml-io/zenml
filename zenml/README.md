<h1>
  <a href="https://maiot.io">
    <img src=https://maiot.io/assets/images/maiot.png alt="maiot ZenML" width=55>
  </a>
  &nbsp;maiot ZenML&nbsp;
  <a href="https://docs.maiot.io"><img alt="release" src=https://img.shields.io/badge/-docs-26CB7C></a>
  <a href="https://github.com/maiot-io/zenml/releases"><img alt="release" src=https://img.shields.io/github/v/tag/maiot-io/zenml?color=431d93></a>
</h1>

#### Automate ML with repeatable pipelines

<!---
    <img src=https://gblobscdn.gitbook.com/assets%2F-MCl0MaN3pJfPa2vq2Rb%2F-MJSVuyKMUm7L-4iDzD1%2F-MJSVynHi27dMZrQHXwE%2Farchitectural-overview.png alt="maiot ZenML">
-->

Hello there! This is the repository for the  maiot ZenML. If you would like to see the published 
pip package can be found [here](https://pypi.org/project/zenml).

ZenML is a platform that lets you create machine learning pipelines for production use-cases.
Our [website](https://maiot.io) gives an overview of the features of ZenML and if you find 
it interesting, you can sign up for an early access [here](https://maiot.io/#early-access). You can also learn 
more about how to use ZenML [here](https://docs.maiot.io).

## How to install from pip

You can easily install `zenml` using pip:
```bash
pip install zenml
```

## How to install from source
On the other hand, if you like to install from the source directly, you can follow:
```bash
make venv
source venv/bin/activate
make install
make build
```

## Known errors in installation
If you run into a `psutil` error, please install the python-dev libraries:

```bash
sudo apt update
sudo apt install python3.x-dev
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

* **maiot GmbH** - [maiot.io](https://maiot.io) - [maiot Docs](https://docs.maiot.io)