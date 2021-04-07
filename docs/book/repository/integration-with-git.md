# Integration with Git

## Versioning custom code

We are not looking to reinvent the wheel, and we're not trying to interfere too much with established workflows. When it comes to versioning of code, 
that means a solid integration into Git.

In short: ZenML **optionally** uses Git SHAs to resolve your version-pinned pipeline code. 

When you [add custom code](../getting-started/creating-custom-logic.md) to ZenML, you have the ability to specify a specific Git SHA for your code.
ZenML ties into your local Git history and will automatically try to resolve the SHA into usable code. 
Every pipeline configuration will persist the combination of the class used, and the related SHA in the 
[pipeline config](../pipelines/what-is-a-pipeline.md). 

```{hint}
The format used is: `class@git_sha`, where:

* **class**: a fully-qualified python import path of a ZenML-compatible class, e.g. `my_module.my_class.MyClassName`
* **git_sha** (optional): a 40-digit string representing the commit git sha at which the class exists
```

You can, of course, run your code as-is and maintain version control via your own logic and your own automation. This is why the `git_sha` above is optional: If 
you run a pipeline where the `class` is not committed (i.e. unstaged or staged but not committed), then no `git_sha` is added to the config. In this case, 
each time the pipeline is run or loaded the `class` is loaded **as is** from the `class` path, directly from the working tree's current state. 

```{warning}
While it is faster to just keep running pipelines with un-pinned classes, each un-pinned class adds a technical debt to the ZenML repository. This is because there are no 
guarantees of reproducibility once a pipeline has a class that is un-pinned. We strongly advise to always commit all code before running pipelines.
```

### Versioning built-in methods

Since ZenML comes with a lot of batteries included, and as ZenML is undergoing rapid development, we're providing a way to version built-in methods, too.

Specifying the version of a built-in method will be persisted in the pipeline config as `step.path@zenml_0.1.0`. 
E.g. `zenml.steps.data.bq_data_step.BQDataStep@zenml_0.1.4`

## Under the hood
When running a version-pinned piece of code, ZenML loads all SHA-pinned classes from your git history into memory.
This is done via an - immediately reversed - in-memory checkout of the specified SHA.

### Safe-guards with in-memory loading
In order to ensure this is not a destructive operation, ZenML does not allow the in-memory checkout if any of the files in the 
module folder where the `class` resides is un-committed. E.g. Attempting to load `my_module.step.MyStepClass@sha1` will fail 
if the `my_module.step` has any uncommitted files.

### Organizing code
It is important to understand that when a pipeline is run, all custom classes used, whether they be `Steps`, `Datasources`, or `Backends` under-go 
a so-called `git-resolution` process. This means that wherever there is a custom class referenced in a Pipeline, all files within the module are checked 
to see if they are committed or not. If they are committed, then the class is successfully pinned with the relevant sha. If they are not, then a warning is 
thrown but the class is not pinned in the corresponding config. Therefore, it is important to consider not only the file where custom logic resides, but the 
entire module. This is also the reason that `upwards` relative imports are not permitted within these class files. 

We recommend that users [follow our recommendation](../getting-started/organizing-zenml.md)to structure their ZenML repositories, to avoid 
any potential Git-related issues.

### A concrete example
Let's say we created a custom TrainerStep like and placed it in our ZenML repository here:

```
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

datasource:
  ...

environment:
  ...

steps:
  training:
    args: {}
    source: trainers.my_awesome_trainer.my_trainer_step.MyAwesomeTrainer@e9448e0abbc6f03252578ca877bc80c94f137edd
  ...
```

Notice the `source` key is tagged with the full path to trainer class and the sha `e9448e0abbc6f03252578ca877bc80c94f137edd`. If we ever load this pipeline 
or step using e.g. `repo.get_pipeline_by_name()` then the following would happen:

```{hint}
We change `e9448e0abbc6f03252578ca877bc80c94f137edd` to `e9448e0a` for readability purposes.
```

* All files within the directory `trainers/my_awesome_trainer/` would be checked to see if committed or not. Only if all files are committed properly would 
ZenML allow for loading the pipeline.
* The directory `repository/trainers/my_awesome_trainer/` would be checked out to sha `e9448e0a`. This is achieved by executing 
`git checkout e9448e0a -- trainers/my_awesome_trainer/`
* The module is loaded using the standard Python `importlib` library.
* The git checkout is reverted.

This way, all ZenML custom classes can be used in different environments, and reproducibility is ensured.