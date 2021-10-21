---
description: >-
  We discuss some of the fundamental framework decisions we have made and why we
  made them
---

# Framework Design

One of the biggest questions often left unasked when designing a new framework is **WHY**?

* Why did you design this interface this way?
* Why did you choose this abstraction over another seemingly easy way?
* Why did you select this integration and not another?
* and many more..

When designing a framework as broad as ZenML, the team is probably making hundreds of micro-decisions weekly. While all of these are impossible to capture, we have decided to capture the most key decisions here, and hopefully illuminate why we built ZenML this way.

## Pipelines and Pipeline runs: Separating Configuration From Implementation

We decided early on that we wanted to clearly define what a Pipeline and a Pipeline Run were. Here is the key:

* Pipelines define the **data dependencies** between steps.
* Pipeline runs define the **parameters** of each step.

The advantage of this is that the user need only define a pipeline once, but can reuse that pipeline with different parameters. So then I can do the following:

```python
def my_pipeline(
    step_1,
    step_2
)
    # connect the two together
    step_2(step_1())
    
run_1 = my_pipeline(
    step_1=first_step_first_version()
    step_2=second_step(Params(my_param=2))

run_2 = my_pipeline(
    step_1=first_step_second_version(param=3)
    step_2=second_step(Params(my_param=1))

# compare them
```

The above design also lends itself to swapping in and out different step logic if the INTERFACE of the steps remain consistent.

## Steps

One small step for data scientist..

### Simple Functions

We wanted to make a simple Python functiosn be ZenML steps with one decorator:

```python
@step
def returns_one() -> int:
    return 1

@step
def adds(x: int) -> int:
    return x + 2  # we can only add two :-(

@pipeline
def pipeline(first, second):
    second(first())

# Tie interface to implementation
run = pipeline(
  first=returns_one(),
  second=adds()
)
```
While the above looks nice, it has two assumptions:

* The function signatures take `Data Artifacts`, so what happens if I want to parameterize it when im running the pipeline. I don't want to be able to just pass data between steps, but also inject it at run time with some configuration.
* ZenML is 'taking over' how to store these `Data Artifacts` between steps. While its easy for `int` variables in this toy example, that means ZenML also needs to handle all sorts of complex artifacts like `tf.keras.Model` or `torch.nn.Module`!

Let's see how we decided to solve each of the above:

### Parameterizing with the `BaseStepConfig` class


### Using Materializers to abstract away serialization and deserialization logic

Because reading and writing is such a common pattern, we can introduce another abstraction known as `Materializers` to encapsulate this logic. Each `Materializer` can implement a standard `read` and `write` function, and we can thus separate the writing/reading logic from the step itself.

```python
@step
def ASlightComplexStep(output_artifact: Output[ModelArtifact]):
    m = output_artifact.materializers.keras
    # or m = output_artifact.materializers['keras']
    m.write(model, output_artifact)
```

Each artifact can therefore support as many Materializers as required. Think of them as views of the data the artifacts are pointing to. The advantage here is that one can now theoretically parameterize the `key` of the Materializers (`keras` in this case) and completely separate the business logic from the writing logic.

The disadvantage of this design is that one needs to know all the implemented Materializers and adding more Materializers and combining with artifacts is a bit non-intuitive at first.


## Materializers and their role in the Post Execution Workflow
With `Materializers` above, 

## Stacks and the Ops part MLOps
Stacks are an important concept in ZenML and they have an implicit relationship to pipelines. Stacks define where a pipelines steps are storing data, metadata, and where the pipeline is orchestrated.


## Integration with Git
ZenML repositories build on top of Git repositories. Here is why.

### Versioning custom code

We are not looking to reinvent the wheel, and we're not trying to interfere too much with established workflows. When it comes to versioning of code, that means a solid integration into Git.

In short: ZenML **optionally** uses Git SHAs to resolve your version-pinned pipeline code.

When you add steps to ZenML, you have the ability to specify a specific Git SHA for your code. ZenML ties into your local Git history and will automatically try to resolve the SHA into usable code. Every pipeline configuration will persist the combination of the class used, and the related SHA in the pipeline config.

The format used is: `class@git_sha`, where: \_\_

* _**class**: a fully-qualified python import path of a ZenML-compatible class, e.g. `my_module.my_class.MyClassName`_
* **git\_sha** (optional): a 40-digit string representing the commit git sha at which the class exists

You can, of course, run your code as-is and maintain version control via your own logic and your own automation. This is why the `git_sha` above is optional: If you run a pipeline where the `class` is not committed (i.e. unstaged or staged but not committed), then no `git_sha` is added to the config. In this case, each time the pipeline is run or loaded the `class` is loaded **as is** from the `class` path, directly from the working tree's current state.

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

