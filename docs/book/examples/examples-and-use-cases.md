---
description: Use CLI commands to quickly run ZenML examples.
---

# Run ZenML Examples Quickly

One of the best ways to learn ZenML is [through examples](https://github.com/zenml-io/zenml/tree/main/examples). ZenML 
has a [growing list of examples](https://github.com/zenml-io/zenml/tree/main/examples) showcasing many features and 
integrations.

There is no need to clone the ZenML repository to get access to examples quickly. 
Use the series of commands that begin with `zenml example` to download and even run examples.

Get the full list of available examples:

```bash
zenml example list
```

Pick an example to download into your current working directory:

```bash
zenml example pull quickstart
# at this point a `zenml_examples` dir will be created with the example(s) inside it.
# this dir will be located in your current working directory.
```

Some of our examples can even be run directly from the CLI. When ready to run the example, type the following 
command. If there are any dependencies needed to be downloaded for the example to run, the CLI will prompt you to 
install them.

```bash
zenml example run mlflow-tracking
```

Learn more about all of the ways you can interact with the examples and use them
over on [our blogpost about this feature
here](https://blog.zenml.io/examples-cli/).
