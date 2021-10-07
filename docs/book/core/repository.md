---
description: A ZenML repository the heart of your ZenML codebase.
---

# Repository

Every ZenML project starts inside a ZenML repository. Think of it just like a normal Git repository, except that there are some added bonuses on top! A repository is at the core of all ZenML activity. Every action that can be executed within ZenML must take place within a ZenML repository. ZenML repositories are inextricably tied to `git`. ZenML creates a `.zen` folder at the root of your repository to manage your assets and metadata.

To create a ZenML repository, do the following after having installed ZenML:

```text
zenml init
```

{% hint style="warning" %}
Please make sure to be inside a valid git repository before executing the above!
{% endhint %}

The initialization creates a local `.zen` folder where various information about your local configuration lives, e.g., the active [Stack](stacks.md) that you are using to run pipelines.

## The ZenML Repository Instance

In order to access information about your ZenML repository in code, you need to create a ZenML Repository instance:

```python
from zenml.core.repo.repo import Repository

repo = Repository()
```

Now the `repo` object can be used to fetch all sorts of information regarding the repository. For example, one can do:

```python
# Get all pipelines
pipelines = repo.get_pipelines()
```

Using these commands, one can always look back at what actions have been performed in this repository.

## Integration with Git

### Versioning custom code

We are not looking to reinvent the wheel, and we're not trying to interfere too much with established workflows. When it comes to versioning of code, that means a solid integration into Git.

In short: ZenML **optionally** uses Git SHAs to resolve your version-pinned pipeline code.

When you add steps to ZenML, you have the ability to specify a specific Git SHA for your code. ZenML ties into your local Git history and will automatically try to resolve the SHA into usable code. Every pipeline configuration will persist the combination of the class used, and the related SHA in the pipeline config.

The format used is: `class@git_sha`, where: \_\_

* _**class**: a fully-qualified python import path of a ZenML-compatible class, e.g. `my_module.my_class.MyClassName`_ 
* **git\_sha** \(optional\): a 40-digit string representing the commit git sha at which the class exists

You can, of course, run your code as-is and maintain version control via your own logic and your own automation. This is why the `git_sha` above is optional: If you run a pipeline where the `class` is not committed \(i.e. unstaged or staged but not committed\), then no `git_sha` is added to the config. In this case, each time the pipeline is run or loaded the `class` is loaded **as is** from the `class` path, directly from the working tree's current state.

{% hint style="info" %}
While it is faster to just keep running pipelines with un-pinned classes, each un-pinned class adds a technical debt to the ZenML repository. This is because there are no guarantees of reproducibility once a pipeline has a class that is un-pinned. We strongly advice to always commit all code before running pipelines.
{% endhint %}

#### Versioning built-in methods

Since ZenML comes with a lot of batteries included, and as ZenML is undergoing rapid development, we're providing a way to version built-in methods, too.

Specifying the version of a built-in method will be persisted in the pipeline config as `step.path@zenml_0.1.0`. E.g. `zenml.core.steps.data.bq_data_step.BQDataStep@zenml_0.1.4`

### Under the hood

When running a version-pinned piece of code, ZenML loads all SHA-pinned classes from your git history into memory. This is done via an - immediately reversed - in-memory checkout of the specified SHA.

#### Safe-guards with in-memory loading

In order to ensure this is not a destructive operation, ZenML does not allow the in-memory checkout if any of the files in the module folder where the `class` resides is un-committed. E.g. Attempting to load `my_module.step.MyStepClass@sha1` will fail if the `my_module.step` has any uncommitted files.

#### Organizing code

It is important to understand that when a pipeline is run, all custom classes used under-go a so-called `git-resolution` process. This means that wherever there is a custom class referenced in a Pipeline, all files within the module are checked to see if they are committed or not. If they are committed, then the class is successfully pinned with the relevant sha. If they are not, then a warning is thrown but the class is not pinned in the corresponding config. Therefore, it is important to consider not only the file where custom logic resides, but the entire module. This is also the reason that `upwards` relative imports are not permitted within these class files.

## Collaboration across multiple team members

Coming Soon

