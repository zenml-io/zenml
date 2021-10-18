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

## Pipelines

### Separating Configuration (Connections) From Runs

We decided early on that we wanted to clearly define what a Pipeline and a Pipeline Run were. Here is the key:

* Pipelines define the (data) **dependencies** between steps.
* Pipeline runs define the **parameters** of each step.

The advantage of this is that the user need only define a pipeline once, but can reuse that pipeline with different parameters. So then I can do the following:

```python
def my_pipeline(
    step_1,
    step_2,
)
    step_2(step_1())  # step 1 data goes to step 2

run_1 = my_pipeline(
    step_1=simple_step(param=2)
    step_2=another_step(param=2)

run_2 = my_pipeline(
    step_1=simple_step(param=3)
    step_2=yet_another_step(param=2)

# compare
```

The above design also lends itself to swapping in and out different step logic if the INTERFACE of the steps remain consistent. For an example of this, see the [Quickstart](quickstart-guide.md).

### Relation To Stacks

Stacks are an important concept in ZenML, and they have an implicit relationship to pipelines. Stacks define where a pipelines steps are storing data, metadata, and where the pipeline is orchestrated.

## Steps

Reasoning for why steps are like what they are coming soon..
