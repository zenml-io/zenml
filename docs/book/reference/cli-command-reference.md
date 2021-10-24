---
description: Learn more about how to use the ZenML command-line tool
---

# CLI

The ZenML CLI tool is usually downloaded and installed via PyPI and a `pip install zenml` command. Please see the Installation & Setup section above for more information about that process.

## How to use the CLI

Our CLI behaves similarly to many other CLIs for basic features. In order to find out which version of ZenML you are running, type:

```bash
zenml version
```

If you ever need more information on exactly what a certain command will do, use the `--help` flag attached to the end of your command string.

For example, to get a sense of all of the commands available to you while using the `zenml` command, type:

```bash
zenml --help
```

If you were instead looking to know more about a specific command, you can type something like this:

```bash
zenml metadata register --help
```

This will give you information about how to register a metadata store. \(See below for more on that\).

## Beginning a Project

When you begin a project, you should first initialize your base project directory as a Git repository. To do this, type:

```bash
git init
```

Once your directory is setup with a \(usually hidden\) `.git` folder, initialize the directory with ZenML's own config and resource management tools. Type:

```bash
zenml init
```

This is all you need to begin using all the MLOps goodness that ZenML provides!

If your repository is not initialized as a `git` repository, the CLI will let you know with an error message. By default, `zenml init` will install its own hidden `.zen` folder inside the current directory from which you are running the command. You can also pass in a directory path manually using the `--repo_path` option:

```bash
zenml init --repo_path /path/to/dir
```

If you wish to specify that you do not want analytics to be transmitted back to ZenML about your usage of the tool, pass in `False` to the `--analytics_opt_in` option:

```bash
zenml init --analytics_opt_out
```

If you wish to delete all data relating to your project from the directory, use the `zenml clean` command. This will:

* delete all pipelines
* delete all artifacts
* delete all metadata

_Note that the_ `clean` _command is not implemented for the current version._

## Customizing your Metadata Store

The configuration of each pipeline, step, backend, and produced artifacts are all tracked within the metadata store. By default ZenML initialises your repository with a metadata store kept on your local machine. If you wish to register a new metadata store, do so with the `register` command:

```bash
zenml metadata register METADATA_STORE_NAME METADATA_STORE_TYPE [--OPTIONS]
```

If you wish to list the metadata stores that have already been registered within your ZenML project / repository, type:

```bash
zenml metadata list
```

If you wish to delete a particular metadata store, pass the name of the metadata store into the CLI with the following command:

```bash
zenml metadata delete METADATA_STORE_NAME
```

## Customizing your Artifact Store

The artifact store is where all the inputs and outputs of your pipeline steps are stored. By default ZenML initialises your repository with an artifact store with everything kept on your local machine. If you wish to register a new artifact store, do so with the `register` command:

```bash
zenml artifact register ARTIFACT_STORE_NAME ARTIFACT_STORE_TYPE [--OPTIONS]
```

If you wish to list the artifact stores that have already been registered within your ZenML project / repository, type:

```bash
zenml artifact list
```

If you wish to delete a particular artifact store, pass the name of the artifact store into the CLI with the following command:

```bash
zenml artifact delete ARTIFACT_STORE_NAME
```

## Customizing your Orchestrator

An orchestrator is a special kind of backend that manages the running of each step of the pipeline. Orchestrators administer the actual pipeline runs. By default ZenML initialises your repository with an orchestrator that runs everything on your local machine.

If you wish to register a new orchestrator, do so with the `register` command:

```bash
zenml orchestrator register ORCHESTRATOR_NAME ORCHESTRATOR_TYPE [--ORCHESTRATOR_OPTIONS]
```

If you wish to list the orchestrators that have already been registered within your ZenML project / repository, type:

```bash
zenml orchestrator list
```

If you wish to delete a particular orchestrator, pass the name of the orchestrator into the CLI with the following command:

```bash
zenml orchestrator delete ORCHESTRATOR_NAME
```

## Administering the Stack

The stack is a grouping of your artifact store, your metadata store and your orchestrator. With the ZenML tool, switching from a local stack to a distributed cloud environment can be accomplished with just a few CLI commands.

To register a new stack, you must already have registered the individual components of the stack using the commands listed above.

Use the `zenml stack register` command to register your stack. It takes four arguments as in the following example:

```bash
zenml stack register STACK_NAME \
    -m METADATA_STORE_NAME \
    -a ARTIFACT_STORE_NAME \
    -o ORCHESTRATOR_NAME
```

Each corresponding argument should be the name you passed in as an identifier for the artifact store, metadata store or orchestrator when you originally registered it.

To list the stacks that you have registered within your current ZenML project, type:

```bash
zenml stack list
```

To delete a stack that you have previously registered, type:

```bash
zenml stack delete STACK_NAME
```

By default, ZenML uses a local stack whereby all pipelines run on your local computer. If you wish to set a different stack as the current active stack to be used when running your pipeline, type:

```bash
zenml stack set STACK_NAME
```

This changes a configuration property within your local environment.

To see which stack is currently set as the default active stack, type:

```bash
zenml stack get
```

