# The ZenML Repository Instance

In order to access information about your ZenML repository in code, you need to access the ZenML [Repository instance](https://github.com/maiot-io/zenml/blob/main/zenml/core/repo/repo.py). 
This object is a Singleton and can be fetched any time from within your Python code simply by executing:

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
repo.compare_training_pipelines()
```
```{note}
The full list of commands can be found within the Repository class definition.
```

Using these commands, one can always look back at what actions have been performed in this repository. 

It is important to note that most of the methods listed above involve parsing the [config YAML files](../pipelines/what-is-a-pipeline.md) in your [Pipelines Directory](pipeline-directory.md). Therefore, by changing the pipelines directory or manipulating it, you may lose a lot of valuable information regarding how the repository developed over time.
