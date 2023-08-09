---
description: Rocketstart your ZenML journey!
---

# ZenML project templates

What would you need to get a quick understanding of the ZenML framework and start building your ML pipelines? The answer is one of ZenML projects templates to cover major use cases of ZenML: a collection of steps and pipelines and, to top it all off, a simple but useful CLI. This is exactly what the ZenML templates are all about!

## List of ZenML Project Templates

<table><thead><tr><th width="202.33333333333331" align="center">Project Template</th><th width="169" align="center">Tags</th><th align="center">Description</th></tr></thead><tbody><tr><td align="center"><a href="https://github.com/zenml-io/template-e2e-batch">End-to-End Tabular Training with Batch Predictions</a></td><td align="center">etl hp-tuning model-promotion drift-detection batch-prediction scikit-learn</td><td align="center">This project template is a good starting point for anyone starting with ZenML. It consists of two pipelines with the following high-level steps: load, split and preprocess data; run HP tuning; train and evaluate model performance; promote model to production; detect data drift; run batch inference.</td></tr></tbody></table>

{% hint style="info" %}
Do you have a personal project powered by ZenML that you would like to see here? At ZenML, we are looking for design partnerships and collaboration to help us better understand the real-world scenarios in which MLOps is being used and to build the best possible experience for our users. If you are interested in sharing all or parts of your project with us in the form of a ZenML project template, please [join our Slack](https://zenml.io/slack-invite/) and leave us a message!
{% endhint %}

## Generating project from a project template

First, to use the templates, you need to have Zenml and its `templates` extras installed:

```bash
pip install zenml[templates]
```

Now you can generate a project from one of the existing templates by using the `--template` flag with the `zenml init` command:

```bash
zenml init --template <name_of_template>
```

Running command above will result in input prompts being shown to you. If you would like to rely on default values for the ZenML project template - you can add `--template-with-defaults` to the same command, like this:

```bash
zenml init --template <name_of_template> --template-with-defaults
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
