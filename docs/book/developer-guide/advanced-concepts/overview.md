---
description: What are materializers, services, step contexts, and step fixtures.
---

# Advanced Concepts

The previous sections on [Steps and Pipelines](../steps-pipelines/steps-and-pipelines.md)
and [Stacks, Profiles, Repositories](../stacks-profiles-repositories/stacks_profiles_repositories.md)
already cover most of the concepts you will need for developing ML workflows
with ZenML.

However, there are a few additional concepts that you might or might not
encounter throughout your journey, about which you can learn more here.

In particular, these concepts might be helpful when developing custom 
components or when trying to understand the inner workings of ZenML in detail.

## List of Advanced Concepts

* [Materializers](materializer.md) define how artifacts are
saved and loaded at the end and beginning of steps. There already exist built-in
materializers for most common data types, but you might need to build a custom
materializer if one of your steps outputs a custom or unsupported class.
* [Services](manage-external-services.md) are long-lived
external processes that persist beyond the execution of your pipeline runs.
Examples are the services related to deployed models, or the UIs of some
visualization tools like TensorBoard.
* [Step Contexts and Step Fixtures](fetching-historic-runs.md)
allow you to access the repository (including the stack information) from
within a pipeline step. This can, for instance, be used to load the best 
performing prior model to compare newly trained models against.
* [Step Environments](environment.md) can be used to get further information 
about the environment where the step is executed, such as the system it is
running on, the Python version, or the name of the current step, pipeline, and
run.
* [Docker Image Management](docker.md) is required for some remote 
orchestrators and step operators to run your pipeline code in an isolated and 
well-defined environment.
