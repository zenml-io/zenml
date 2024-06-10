---
description: Put your new knowledge in action with an end-to-end project
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# An end-to-end project

That was awesome! We learned so many advanced MLOps production concepts:

* The value of [deploying ZenML](deploying-zenml.md)
* Abstracting infrastructure configuration into [stacks](understand-stacks.md)
* [Connecting remote storage](remote-storage.md)
* [Orchestrating on the cloud](cloud-orchestration.md)
* [Configuring the pipeline to scale compute](configure-pipeline.md)
* [Connecting a git repository](connect-code-repository.md)

We will now combine all of these concepts into an end-to-end MLOps project powered by ZenML.

## Get started

Start with a fresh virtual environment with no dependencies. Then let's install our dependencies:

```bash
pip install "zenml[templates,server]" notebook
zenml integration install sklearn -y
```

We will then use [ZenML templates](../../how-to/setting-up-a-project-repository/using-project-templates.md) to help us get the code we need for the project:

```bash
mkdir zenml_batch_e2e
cd zenml_batch_e2e
zenml init --template e2e_batch --template-with-defaults

# Just in case, we install the requirements again
pip install -r requirements.txt
```

<details>

<summary>Above doesn't work? Here is an alternative</summary>

The e2e template is also available as a [ZenML example](https://github.com/zenml-io/zenml/tree/main/examples/e2e). You can clone it:

```bash
git clone --depth 1 git@github.com:zenml-io/zenml.git
cd zenml/examples/e2e
pip install -r requirements.txt
zenml init
```

</details>

## What you'll learn

The e2e project is a comprehensive project template to cover major use cases of ZenML: a collection of steps and pipelines and, to top it all off, a simple but useful CLI. It showcases the core ZenML concepts for supervised ML with batch predictions. It builds on top of the [starter project](../starter-guide/starter-project.md) with more advanced concepts.

As you progress through the e2e batch template, try running the pipelines on a [remote cloud stack](cloud-orchestration.md) on a tracked [git repository](connect-code-repository.md) to practice some of the concepts we have learned in this guide.

At the end, don't forget to share the [ZenML e2e template](https://github.com/zenml-io/template-e2e-batch) with your colleagues and see how they react!

## Conclusion and next steps

The production guide has now hopefully landed you with an end-to-end MLOps project, powered by a ZenML server connected to your cloud infrastructure. You are now ready to dive deep into writing your own pipelines and stacks. If you are looking to learn more advanced concepts, the [how-to section](../../how-to/build-pipelines/README.md) is for you. Until then, we wish you the best of luck chasing your MLOps dreams!

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
