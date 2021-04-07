# What is a ZenML Repository

Every ZenML project starts inside a ZenML repository. Think of it just like a normal Git repository, except that there are some added bonuses on top! To create a ZenML repository, do the following after [having installed ZenML](../steps/installation.md).

```bash
zenml init
```

```text
Please make sure to be inside a valid git repository before executing the above!
```

The initialization does the following:

* Creates a default SQLite [Metadata Store](metadata-store.md) and local [Artifact Store](artifact-store.md) inside a 

  `.zenml` folder in the root of your repository. 

* Creates an empty `pipelines` directory at the root as well, which is 

  the path where all your [pipeline configurations](../pipelines/what-is-a-pipeline.md) will be stored. 

* Adds a `.zenml_config` YAML configuration file inside the `.zenml` folder that tracks defaults.

If you want to change your default Metadata Store, Artifact Store, or Pipelines Directory, please use the `zenml config` CLI group.

```bash
# Display the current property
zenml config PROPERTY get

# Set the current property
zenml config PROPERTY set [OPTIONS] ARGUMENTS
```

## Local vs Global Config

Similar to other tools like Git, ZenML both maintains a per-repository configuration as well as a global configuration on your machine. As mentioned above, the local configuration is stored in a `.zenml/` directory at the root of your repository. This configuration is written in YAML and may look like this:

```yaml
artifact_store: /path/to/zenml/repo/.zenml/local_store
metadata:
  args:
    uri: /path/to/zenml/repo/.zenml/local_store/metadata.db
  type: sqlite
pipelines_dir: /path/to/zenml/repo/pipelines
```

As you can see this file stores the `default` [Artifact Store](artifact-store.md), [Metadata Store](metadata-store.md) and [Pipelines Directory](pipeline-directory.md) which each of your pipelines will use by default when they are run.

The global config on the other hand stores `global` information such as if a unique anonymous UUID for your zenml installation as well as metadata regarding usage of your ZenML package. It can be found in most systems in the `.config` directory at the path `zenml/info.json`.

## Recommended Repository Structure

The only requirement for the structure of any ZenML repository is that it should be a Git enabled repository. However, we recommend structuring a ZenML repo as follows. Not everything here is required, it is simply an organization that maximizes the effectiveness of ZenML.

```text
repository
│   requirements.txt
│   pipeline_run_script.py
|   .gitignore
|   Dockerfile
|
└───.git 
|    
└───.zenml
|       .zenml_config
|       local_store/    
|
└───notebooks
|       pipeline_exploration.ipynb
|       pipeline_evaluation.ipynb 
|
└───pipelines
|       pipeline_1.yaml
|       pipeline_2.yaml
|       pipeline_n.yaml
|
└───split
|   │   __init__.py
|   |
|   └───my_split_module
|       │   step.py
|       |   __init__.py
|
└───preprocessing
|   │   __init__.py
|   |
|   └───my_preprocessing_module
|       │   step.py
|       |   __init__.py
|
└───trainers
|   │   __init__.py
|   |
|   └───my_trainer_module
|       │   step.py
|       |   __init__.py
|
└───other_step
    │   __init__.py
    |
    └───my_step_module
        │   step.py
        |   __init__.py
```

Some things to note:

There can be many scripts of the type **pipeline\_run\_script.py**, and can potentially be placed in their own directory. These sorts of files are where the actual ZenML pipeline is constructed. When using ZenML in a CI/CD setting with automated runs, these files can be checked into source control as well.

```text
You can put pipeline construction files anywhere within a ZenML repo, and not just the root.
ZenML figures out automatically from which context you are executing and always finds a reference to 
the root of the repository!
```

The **Dockerfile** is necessary in case [custom images](../backends/using-docker.md) are required for non-local pipeline runs. This too can be automated via a simple CI/CD scheme.

The **notebook directory** is for pre and post pipeline run analysis, to analyze what went right \(or wrong\) as the experiments develop. Whenever decisions are made and realized, the code developed here should be refactored into appropriate Step directories to be persisted and tracked by ZenML.

Notice that each type of **Step** has its own root folder, which contains individual modules for different implementations of it. This allows for flexible [git pinning](integration-with-git.md) and easier development as this repository grows.

Let us know your structuring via [Slack](https://github.com/maiot-io/zenml) so we can improve this recommendation!

## What next

Within the context of a ZenML repository, a user gets access to all the historical runs, results, artifacts and metadata associated with that repository. This can be done via the CLI or by accessing the [Repository Singleton](the-zenml-repository-instance.md) in Python.

