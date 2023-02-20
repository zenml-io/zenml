---
description: How to handle issues with conflicting dependencies
---

# Dependency Resolution and ZenML

This page documents a some of the common issues that arise when using ZenML with other libraries.

**Last Updated**: February 20, 2023

When using ZenML with other libraries, you may encounter issues with conflicting
dependencies. ZenML aims to be stack- and integration-agnostic, allowing you to
run your pipelines using the tools that make sense for your problems. With this
flexibility comes the possibility of dependency conflicts.

## Suggestions for Resolving Dependency Conflicts

### Use a tool like `pip-compile` for reproduciblity

Consider using a tool like `pip-compile` (available through [the `pip-tools`
package](https://pip-tools.readthedocs.io/)) to compile your dependencies into a
static `requirements.txt` file that can be used across environments.

### Well-known dependency resolution issues

Some of ZenML's integrations come with strict dependency and package version
requirements. We try to keep these dependency requirements ranges as wide as
possible for the integrations developed by ZenML, but it is not always possible
to make this work completely smoothly. Here are some of the known issues:

- `label_studio`: the packages required for this integration are not compatible
  with quite a few of our other integrations. At a minimum, you will get
  warnings when installing `label_studio` via `zenml integration install ...`.
  We have found these warnings to be mostly harmless. You might find you need to
  separate your installations of Label Studio and any other integrations you
  need for your environment / pipeline, however. Note [the warning on our own
  documentation
  page](https://docs.zenml.io/component-gallery/annotators/label-studio#how-to-deploy-it)
  for the Label Studio integration which currently breaks ZenML's CLI.
- `click`: ZenML currently requires `click~=8.0.3` for its CLI. This is on
  account of another dependency of ZenML. Using versions of `click` in your own
  project that are greater than 8.0.3 may cause unanticipated behaviors.
