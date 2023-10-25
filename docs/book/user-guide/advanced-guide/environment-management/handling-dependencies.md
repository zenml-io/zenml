---
description: How to handle issues with conflicting dependencies
---

# Dependency Resolution and ZenML

This page documents a some of the common issues that arise when using ZenML with
other libraries.

**Last Updated**: October 17, 2023

When using ZenML with other libraries, you may encounter issues with conflicting
dependencies. ZenML aims to be stack- and integration-agnostic, allowing you to
run your pipelines using the tools that make sense for your problems. With this
flexibility comes the possibility of dependency conflicts.

ZenML allows you to install dependencies required by integrations through the
`zenml integration install ...` command. This is a convenient way to install
dependencies for a specific integration, but it can also lead to dependency
conflicts if you are using other libraries in your environment. An easy way to
see if the ZenML requirements are still met (after installing any extra
dependencies required by your work) by running `zenml integration list` and
checking that your desired integrations still bear the green tick symbol
denoting that all requirements are met.

## Suggestions for Resolving Dependency Conflicts

### Use a tool like `pip-compile` for reproducibility

Consider using a tool like `pip-compile` (available through [the `pip-tools`
package](https://pip-tools.readthedocs.io/)) to compile your dependencies into a
static `requirements.txt` file that can be used across environments.

For a practical example and explanation of using `pip-compile` to address
exactly this need, see [our 'gitflow' repository and
workflow](https://github.com/zenml-io/zenml-gitflow#-software-requirements-management)
to learn more.

### Use `pip check` to discover dependency conflicts

Running [`pip check`](https://pip.pypa.io/en/stable/cli/pip_check/) will verify
that your environment's dependencies are compatible with one another. If not,
you will see a list of the conflicts. This may or may not be a problem or
something that will prevent you from moving forward with your specific use case,
but it is certainly worth being aware of whether this is the case.

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
  page](../../../stacks-and-components/component-guide/annotators/label-studio.md#how-to-deploy-it)
  for the Label Studio integration which currently breaks ZenML's CLI.
- `click`: ZenML currently requires `click~=8.0.3` for its CLI. This is on
  account of another dependency of ZenML. Using versions of `click` in your own
  project that are greater than 8.0.3 may cause unanticipated behaviors.

### Manually bypassing ZenML's integration installation

It is possible to skip ZenML's integration installation process and install
dependencies manually. This is not recommended, but it is possible and can be
run at your own risk.

{% hint style="info" %} Note that the `zenml integration install ...` command
runs a `pip install ...` under the hood as part of its implementation, taking
the dependencies listed in the integration object and installing them. For
example, `zenml integration install gcp` will run `pip install "kfp==1.8.16"
"gcsfs" "google-cloud-secret-manager" ...` and so on, since they are [specified
in the integration
definition](https://github.com/zenml-io/zenml/blob/ec2283473e5e0c5a2f1b7868875539a83e617f8c/src/zenml/integrations/gcp/__init__.py#L45).
{% endhint %}

To do this, you will need to install the dependencies for the integration you
want to use manually. You can find the dependencies for the integrations by
running `zenml integration list` and looking at the `REQUIRED_PACKAGES` column.
You can then amend and tweak those requirements as you see fit. Note that if you
are using a remote orchestrator, you would then have to place the updated
versions for the dependencies in a `DockerSettings` object (described in detail
[here](https://docs.zenml.io/advanced-guide/pipelines/containerization#how-to-install-additional-pip-dependencies-or-apt-packages))
which will then make sure everything is working as you need.
