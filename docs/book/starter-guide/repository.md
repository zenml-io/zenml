# Creating your ZenML repository

Every **ZenML** project starts inside a **ZenML repository**. Think of it just like a normal Git repository, except that there are some added bonuses on top! In order to create a **ZenML repository**, create a git repo and do the following within this repository:

```text
zenml init
```

The initialization will execute the following steps:

* It will create a **default** local SQLite Metadata Store and Artifact Store inside a `.zenml` folder in the root of your repository.
* It will create an empty `pipelines` directory at the root as well, which is the path where all your pipeline configurations will be stored on **default**.
* Adds a `.zenml_config` YAML configuration file inside the `.zenml` folder that tracks these defaults.

If you want to change your **Metadata Store**, **Artifact Store**, or **Pipelines Directory**, please use the `zenml config` CLI group.

```bash
# Display the current property
zenml config PROPERTY get

# Set the current property
zenml config PROPERTY set [OPTIONS] ARGUMENTS
```

## Local and Global Config[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/repository/what-is-a-repository.html#local-vs-global-config)

Similar to other tools like Git, ZenML maintains both a per-repository configuration as well as a global configuration on your machine. As mentioned above, the local configuration is stored in a `.zenml/` directory at the root of your repository. This configuration is written in YAML and may look like this:

```yaml
artifact_store: /path/to/zenml/repo/.zenml/local_store
metadata:
  args:
    uri: /path/to/zenml/repo/.zenml/local_store/metadata.db
  type: sqlite
pipelines_dir: /path/to/zenml/repo/pipelines
```

As you can see this file stores the default **Artifact Store**, **Metadata Store** and **Pipelines Directory** which each of your pipelines will use by default when they are run.

The global config on the other hand stores `global` information such as if a unique anonymous UUID for your zenml installation as well as metadata regarding usage of your ZenML package. It can be found in most systems in the `.config` directory at the path `zenml/info.json`.

## The ZenML Repository Instance[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/repository/the-zenml-repository-instance.html#the-zenml-repository-instance)

In order to access information about your **ZenML repository** in code, you need to access the **ZenML Repository** instance. This object is a singleton and can be fetched any time from within your Python code simply by executing:

```python
from zenml.repo import Repository

# We recommend to add the type hint for auto-completion in your IDE/Notebook
repo: Repository = Repository.get_instance()
```

Now the `repo` object can be used to fetch all sorts of information regarding the repository. For example, one can do:

```python
# Get all datasources
datasources = repo.get_datasources()

# Get all pipelines
pipelines = repo.get_pipelines()

# List all registered steps in the 
steps = repo.get_step_versions()

# Get a step by its version
step_object = get_step_by_version(step_type, version)

# Compare all pipelines in the repository
repo.compare_training_runs()
```

The full list of commands can be found within the Repository class definition. Using these commands, one can always look back at what actions have been performed in this repository.

{% hint style="warning" %}
It is important to note that most of the methods listed above involve parsing the config YAML files in your Pipelines Directory. Therefore, if you change the `pipelines` directory or manipulate it, you may lose a lot of valuable information regarding how the repository developed over time.
{% endhint %}

## What's next?

* As we now have our **ZenML repository** set up, we can go ahead and start developing our first **pipeline**.
* If you want to learn more about how the git integration works under the hood, you can go ahead and check here.
* Moreover, if you would like to see our suggestions on how to organize your repository you can check here.

