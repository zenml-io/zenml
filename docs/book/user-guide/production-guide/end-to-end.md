---
description: Put your new knowledge in action with an end to end project
---

# An end-to-end project

In this guide, we have went over some advanced concepts:

- The value of [deploying ZenML](connect-deployed-zenml.md)
- Abstracting infrastructure configuration into [stacks](understand-stacks.md)
- [Deploying a MLOps stack](cloud-stack.md) on a cloud provider of your choice
- [Connecting a git repository](connect-code-repository.md)
- [Scaling compute](scale-compute.md)
- Setting up [pipeline configuration](configure-pipeline.md) in production

We will now combine all of these concepts into an end to end MLOps project powered by ZenML.

## Get started

Start with a fresh virtual environment with no dependencies. Then let's install our dependencies:

```bash
pip install "zenml[templates,server]" notebook
zenml integration install sklearn -y
```

We will then use [ZenML templates](../advanced-guide/best-practices/using-project-templates.md) to help us get the code we need for the project:

```bash
mkdir zenml_starter
cd zenml_starter
zenml init --template e2e_batch --template-with-defaults

# Just in case, we install the requirements again
pip install -r requirements.txt
```

<details>

<summary>Above doesn't work? Here is an alternative</summary>

The e2e template is also available as a [ZenML example](https://github.com/zenml-io/zenml/tree/main/examples/e2e). You can clone it:

```bash
git clone git@github.com:zenml-io/zenml.git
cd examples/e2e
pip install -r requirements.txt
zenml init
```

</details>

## What you'll learn

The e2e project is a comprehensive project template to cover major use cases of ZenML: a collection of steps and pipelines and, to top it all off, a simple but useful CLI. It showcases the core ZenML concepts for supervised ML with batch predictions:

- Designing [ZenML pipeline steps](https://docs.zenml.io/user-guide/starter-guide/create-an-ml-pipeline)
- Using [step parameterization](https://docs.zenml.io/user-guide/starter-guide/create-an-ml-pipeline#parametrizing-a-step)
 and [step caching](https://docs.zenml.io/user-guide/starter-guide/cache-previous-executions#caching-at-a-step-level)
to design flexible and reusable steps
- Using [custom data types for your artifacts and writing materializers for them](https://docs.zenml.io/user-guide/advanced-guide/artifact-management/handle-custom-data-types)
- Constructing and running a [ZenML pipeline](https://docs.zenml.io/user-guide/starter-guide/create-an-ml-pipeline)
- Accessing ZenML pipeline run artifacts in [the post-execution phase](https://docs.zenml.io/user-guide/starter-guide/fetch-runs-after-execution)
after a pipeline run has concluded
- Best practices for implementing and running reproducible and reliable ML pipelines with ZenML

Now trying sharing the [ZenML e2e template](https://github.com/zenml-io/template-e2e-batch) with your colleagues and see how they react!

## Conclusion and next steps

The production guide has now hopefully landed you with an end to end MLOps project, powered by a ZenML server connected to your cloud infrastructure. You are now ready to dive deep into writing your own pipelines and stacks. If you are looking to learn more advanced concepts, the [Advanced Guide](../advanced-guide/) is for you. Until then, we wish you the best of luck chasing your MLOps dreams!

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>