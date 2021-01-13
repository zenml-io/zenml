---
description: Version code with git
---

# Integration with Git

## Versioning custom code

We are not looking to reinvent the wheel, and we're not trying to interfere too much with established workflows. When it comes to versioning of code, that means a solid integration into Git.

In short: ZenML **optionally** uses Git SHAs to resolve your version-pinned pipeline code. 

When you create pipeline steps with ZenML, you have the ability to specify a specific Git SHA for your code. ZenML ties into your local Git history and will automatically try to resolve the SHA into useable code. Every pipeline configuration will declaratively persist the combination of the class used for a step and the related SHA in the form of `step_class@SHA`

You can, of course, run your code as-is and maintain version control via your own logic and your own automation. However, when starting a new set of experiments, such a structure is often only a distant ticket in the backlog or a vague idea for a future revision. We aim to provide a no-hassle integration into tried-and-true methods to version code, that can easily transition across environments.

## Versioning built-in methods

Since ZenML comes with a lot of batteries included, and as ZenML is undergoing rapid development, we're providing a way to version built-in methods, too.

Specifying the version of a built-in method will be persisted in the pipeline config as `stepclass@zenml_0.1.0`

## Under the hood

When running a version-pinned piece of code, ZenML loads all SHA-pinned steps from your git history into memory. This is done via an - immediately reversed - in-memory checkout of the specified SHA.

