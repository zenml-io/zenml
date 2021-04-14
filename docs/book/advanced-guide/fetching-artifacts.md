---
description: 'Structure your steps, pipelines, backends and more.'
---

# ZenML Repository Guidelines

The only requirement for the structure of any ZenML repository is that it should be a **Git enabled repository**. ZenML works on some assumptions of the underlying git repository that it is built on top of.

## Components

ZenML has the following core components:

* [Steps](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/getting-started/steps/what-is-a-step.md)
* [Datasources](../datasources/what-is-a-datasource.md)
* [Pipelines](../pipelines/what-is-a-pipeline.md)
* [Backends](../backends/what-is-a-backend.md)

Each component has its own intricacies and its own rules of precisely how to extend them. However, there are some rules that are general when writing ZenML code:

* All components have `Base` classes, e.g., `BaseDatasource`, `BasePipeline`, `BaseStep` etc that need to be inherited from.
* All custom classes must exist within its own `module` \(directory\) in a ZenML repo.
* All components follow the same Git-pinning methodology outlined [below](fetching-artifacts.md#integration-with-git).

## Recommended Repository Structure

. We recommend structuring a ZenML repo as follows. Not everything here is required, it is simply an organization that maximizes the effectiveness of ZenML.

```yaml
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

Some things to note: There can be many scripts of the type **pipeline\_run\_script.py**, and can potentially be placed in their own directory. These sorts of files are where the actual ZenML pipeline is constructed. When using ZenML in a CI/CD setting with automated runs, these files can be checked into source control as well.  

{% hint style="info" %}
You can put pipeline construction files anywhere within a ZenML repo, and not just the root. ZenML figures out automatically from which context you are executing and always finds a reference to the root of the repository!
{% endhint %}

The **Dockerfile** is necessary in case [custom images](../backends/using-docker.md) are required for non-local pipeline runs. This too can be automated via a simple CI/CD scheme. The **notebook directory** is for pre and post pipeline run analysis, to analyze what went right \(or wrong\) as the experiments develop. Whenever decisions are made and realized, the code developed here should be refactored into appropriate Step directories to be persisted and tracked by ZenML. Notice that each type of **Step** has its own root folder, which contains individual modules for different implementations of it. This allows for flexible [git pinning](integration-with-git.md) and easier development as this repository grows. Let us know your structuring via [Slack](https://github.com/maiot-io/zenml) so we can improve this recommendation!

## Integration with Git

ZenML does not reinvent the wheel, or interfere too much with established workflows. When it comes to versioning of code, this means a solid integration into Git.

Concretely, ZenML **optionally** uses Git SHAs to resolve your version-pinned pipeline code.

At pipeline run time, ZenML ties into your local Git history and automatically resolves the SHA into usable code. Every pipeline configuration will persist the combination of the class used, and the related SHA in the [pipeline config](https://github.com/maiot-io/zenml/blob/1b4e7d68c6d1c9c92e04d7b52ebb1cc63a20fde5/docs/book/pipelines/what-is-a-pipeline.md). The format used is: `class@git_sha`, where:

* **class**: a fully-qualified python import path of a ZenML-compatible class, e.g. `my_module.my_class.MyClassName`  __
* _**git\_sha**_ **\(optional\)**: a 40-digit string representing the commit git sha at which the class exists

You can, of course, run your code as-is and maintain version control via your own logic and your own automation. This is why the `git_sha` above is optional: If you run a pipeline where the `class` is not committed \(i.e. unstaged or staged but not committed\), then no `git_sha` is added to the config. In this case, each time the pipeline is run or loaded the `class` is loaded **as is** from the `class` path, directly from the working tree's current state.

```text
While it is faster to just keep running pipelines with un-pinned classes, each un-pinned class adds a technical debt to the ZenML repository. This is because there are no 
guarantees of reproducibility once a pipeline has a class that is un-pinned. We strongly advise to always commit all code before running pipelines.
```

#### Versioning built-in methods

Since ZenML comes with a lot of batteries included, and as ZenML is undergoing rapid development, we're providing a way to version built-in methods, too.

Specifying the version of a built-in method will be persisted in the pipeline config as `step.path@zenml_0.1.0`. E.g. `zenml.steps.data.bq_data_step.BQDataStep@zenml_0.1.4`

### What happens under-the-hood?

When running a version-pinned piece of code, ZenML loads all SHA-pinned classes from your git history into memory. This is done via an - immediately reversed - in-memory checkout of the specified SHA.

#### Safe-guards with in-memory loading

In order to ensure this is not a destructive operation, ZenML does not allow the in-memory checkout if any of the files in the module folder where the `class` resides is un-committed. E.g. Attempting to load `my_module.step.MyStepClass@sha1` will fail if the `my_module.step` has any uncommitted files.

#### Organizing code

It is important to understand that when a pipeline is run, all custom classes used, whether they be `Steps`, `Datasources`, or `Backends` under-go a so-called `git-resolution` process. This means that wherever there is a custom class referenced in a Pipeline, all files within the module are checked to see if they are committed or not. If they are committed, then the class is successfully pinned with the relevant sha. If they are not, then a warning is thrown but the class is not pinned in the corresponding config. Therefore, it is important to consider not only the file where custom logic resides, but the entire module. This is also the reason that `upwards` relative imports are not permitted within these class files.

We recommend that users [follow our recommendation](https://github.com/maiot-io/zenml/blob/1b4e7d68c6d1c9c92e04d7b52ebb1cc63a20fde5/docs/book/getting-started/organizing-zenml.md)to structure their ZenML repositories, to avoid any potential Git-related issues.

### Example of how ZenML + Git function together

Let's say we created a TrainerStep and placed it in our ZenML repository here:

```text
repository
│   requirements.txt
│   pipeline_run.py
│
└───trainers
    │   __init__.py
    |
    └───my_awesome_trainer
        │   my_trainer_step.py
        |   __init__.py
```

where the contents of `my_trainer_step.py` are:

```python
from zenml.steps.trainer import BaseTrainerStep


class MyAwesomeTrainer(BaseTrainerStep):
    def run_fn(self, *args, **kwargs):
        a = 1
        # create a great trainer here.
```

If we commit everything and then run a pipeline like so:

```python
from zenml.pipelines import TrainingPipeline
from trainers.my_awesome_trainer.my_trainer_step import MyAwesomeTrainer

training_pipeline = TrainingPipeline(name='My Awesome Pipeline')

# Fill in other steps

# Add a trainer
training_pipeline.add_trainer(MyAwesomeTrainer(
    loss='binary_crossentropy',
    last_activation='sigmoid',
    output_units=1,
    metrics=['accuracy'],
    epochs=20))

training_pipeline.run()
```

Then the corresponding pipeline YAML may look like:

```yaml
version: '1'

steps:
  training:
    args: {}
    source: trainers.my_awesome_trainer.my_trainer_step.MyAwesomeTrainer@e9448e0abbc6f03252578ca877bc80c94f137edd
  ...
```

Notice the `source` key is tagged with the full path to trainer class and the sha `e9448e0abbc6f03252578ca877bc80c94f137edd`. If we ever load this pipeline or step using e.g. `repo.get_pipeline_by_name()` then the following would happen:

* All files within the directory `trainers/my_awesome_trainer/` would be checked to see if committed or not. Only if all files are committed properly would ZenML allow for loading the pipeline.
* The directory `repository/trainers/my_awesome_trainer/` would be checked out to sha `e9448e0a`. This is achieved by executing `git checkout e9448e0a -- trainers/my_awesome_trainer/`
* The module is loaded using the standard Python `importlib` library.
* The git checkout is reverted.

{% hint style="info" %}
We change `e9448e0abbc6f03252578ca877bc80c94f137edd` to `e9448e0a` for readability purposes.
{% endhint %}

This way, all ZenML custom classes can be used in different environments, and reproducibility is ensured.

