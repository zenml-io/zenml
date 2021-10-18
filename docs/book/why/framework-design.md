---
description: >-
  We discuss some of the fundamental framework decisions we have made and why we
  made them
---

# Framework Design

One of the biggest questions often left unasked when designing a new framework is **WHY**?

- Why did you design this interface this way?
- Why did you choose this abstraction over another seemingly easy way?
- Why did you select this integration and not another?
- and many more..

When designing a framework as broad as ZenML, the team is probably making hundreds of micro-decisions weekly. While all of these are impossible to capture, we have decided to capture the most key decisions here, and hopefully illuminate why we built ZenML this way.

## Pipelines

### Separating Configuration \(Connections\) From Runs

We decided early on that we wanted to clearly define what a Pipeline and a Pipeline Run were. Here is the key:

- Pipelines define the \(data\) **dependencies** between steps.
- Pipeline runs define the **parameters** of each step.

The advantage of this is that the user need only define a pipeline once, but can reuse that pipeline with different parameters. So then I can do the following:

```python
def my_pipeline(
    step_1: Step[SimplestStepEver],
    step_2: Step[AnotherStep]
)
    # connect the two together

run_1 = my_pipeline(
    step_1=SimplestStepEver(param=2)
    step_2=AnotherStep(param=2)

run_1 = my_pipeline(
    step_1=SimplestStepEver(param=3)
    step_2=AnotherStep(param=3)

# compare
```

The above design also lends itself to swapping in and out different step logic if the INTERFACE of the steps remain consistent. For an example of this, see the [Quickstart](../quickstart-guide.md).

### Relation To Stacks

Stacks are an important concept in ZenML and they have an implicit relationship to pipelines. Stacks define where a pipelines steps are storing data, metadata, and where the pipeline is orchestrated.

## Steps

One small step for data scientist..

### Simple Functions

We wanted to make a simple Python function be a ZenML step with one decorator:

```python
@step
def SimplestStepEver(basic_param_1: int, basic_param_2: str) -> int:
    return basic_param_1 + int(basic_param_2)
```

However, what happens if we want to pass persisted **data** \(like a model object\) as a parameter or return value? Let's say a Keras model. One would expect this to work:

```python
# this won't work
@step
def ASlightComplexStep() -> tf.keras.model:
    # create model
    return model
```

But it wont. The reason is that while in the previous example, it is easy enough to store an integer and pass it between steps, ZenML cannot \(and probably **SHOULD** not\) know how to store and pass around a Keras model. See, there are infinite ways in how you might want to store it, depending on your use-case and requirements.

### Passing Data Between Steps

ZenML solves this with the `Artifact` Input/Output paradigm:

```python
@step
def ASlightComplexStep(output_artifact: Output[ModelArtifact]):
    # defines where ZenML wants you to store the model
    output_artifact.uri

    # now you can write the model in a custom function
    write_model(output_artifact)

@step
def AnotherSlightComplexStep(input_artifact: Output[ModelArtifact]):
    # defines where you stored the model in the prev step
    input_artifact.uri

    # now you can write the model in a custom function
    model = read_model(input_artifact)

# connect these together and run
```

By passing an artifact in as an **annotated and typed parameter** of the function rather than as a return type hint, we can **decouple** the writing logic of the model by providing a simple location to the user to write to. Now, one can simply do with the model whatever they'd like.

{% hint style="success" %}
A good mental model to choose between using simple types and Artifact types in a ZenML step is that Artifacts should be used when you want the represented data to be written in a special way to the artifact store. E.g.

- A model written as JSON.
- Data written in flat files like CSV.
- A complex object containing statistics or schema.
  {% endhint %}

### The reason for annotations and type-hints

In Python, this is an annotated parameter with a type hint: `output: Output[ModelArtifact]`. In this case, it tells ZenML that the `output`variable is a `ModelArtifact` and is intended to be the output of this step.

Why is this important?

- When ZenML knows its a `ModelArtifact` it can now recognize you are writing a model and help you with ML-specific tasks like registering it in model registries and comparing multiple models later.
- By specifying an artifact is `Input` or `Output` we can tie steps together with `data dependencies` rather than `task dependencies`. This means that you don't need to say "**Call Step B before Step A**". Instead you can say: "**Step B is to receive a ModelArtifact, and this MAY comes from Step A because Step A outputs a ModelArtifact.**" This is superior because data is more important than tasks in machine learning, and you want to able to decouple task dependencies.
- By telling ZenML its an `Output` artifact, you ensure that you have access to it later with `step.outputs`. This is useful when experimenting with pipeline runs.
- We can type check inputs and outputs and make the pipeline robust.

### Can we make this better? Yes, lets introduce Materializers:

Because reading and writing is such a common pattern, we can introduce another abstraction known as `Materializers` to encapsulate this logic. Each `Materializer` can implement a standard `read` and `write` function, and we can thus separate the writing/reading logic from the step itself.

```python
@step
def ASlightComplexStep(output_artifact: Output[ModelArtifact]):
    m = output_artifact.materializers.keras
    # or m = output_artifact.materializers['keras']
    m.write(model, output_artifact)
```

Each artifact can therefore support as many Materializers as required. Think of them as views of the data the artifacts are pointing to. The advantage here is that one can now theoritically paramaterize the `key` of the Materializers \(`keras` in this case\) and completely separate the business logic from the writing logic.

The disadvantage of this design is that one needs to know all the implemented Materializers and adding more Materializers and combining with artifacts is a bit non-intuitive at first.

#### Rejected Alternative 1: Artifacts own the Materializer:

There are some alternative ways of implementing Materializers. The first is to create Materializers as separate entities that are not coupled with artifacts.

```python
@step
def ASlightComplexStep(output_artifact: Output[ModelArtifact]):
    # defines where ZenML wants you to store the model
    output_artifact.uri

    # materializers control the logic of writing the model
    m = KerasMaterializer()
    m.write(model, output_artifact)

@step
def AnotherSlightComplexStep(input_artifact: Output[ModelArtifact]):
    # defines where you stored the model in the prev step
    m = KerasMaterializer()  # you can change this in the future
    model = m.read(input_artifact)

    # now you can write the model in a custom function
    model = read_model(input_artifact)

# connect these together and run
```

The advantage of this is there is a separation of concerns: The relationship between an Artifact and a Materializer is only implicit, and adding a new Materializer is simple. However, now we have tied the step business logic even further with the step, so to change a Materializer one needs to change the step and cannot simply parameterize it.

#### Rejected Alternative 2: Using special signals to indicate data written

Another way to solve this is to invert the relationship between a artifacts and steps. Rather than the steps being aware of artifacts, one can simply "emit" an event that indicates that a step yields a specific artifat.

```python
@step
def my_asset_solid(param: int):
    df = get_some_data()
    write_model(model)
    yield OutputEvent(
        key="output_artifact"
    )
```

Pros:

- Clean function signatures, with a consistent param only interface.

Cons:

- One cannot link steps together through data dependencies any more as ZenML has no idea what is happening inside the step before its run.
- Couples the writing logic to step.
- The user needs to remember the key and its hard for these to be dynamic.
