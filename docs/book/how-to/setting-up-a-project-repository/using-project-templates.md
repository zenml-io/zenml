---
description: Rocketstart your ZenML journey!
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Project templates

What would you need to get a quick understanding of the ZenML framework and start building your ML pipelines? The answer is one of ZenML project templates to cover major use cases of ZenML: a collection of steps and pipelines and, to top it all off, a simple but useful CLI. This is exactly what the ZenML templates are all about!

## List of available project templates

<table data-full-width="true"><thead><tr><th width="281.33333333333337">Project Template [Short name]</th><th width="200">Tags</th><th>Description</th></tr></thead><tbody><tr><td><a href="https://github.com/zenml-io/template-starter">Starter template</a> [<code>starter</code>]</td><td><code>basic</code> <code>scikit-learn</code></td><td>All the basic ML ingredients you need to get you started with ZenML: parameterized steps, a model training pipeline, a flexible configuration and a simple CLI. All created around a representative and versatile model training use-case implemented with the scikit-learn library.</td></tr><tr><td><a href="https://github.com/zenml-io/template-e2e-batch">E2E Training with Batch Predictions</a> [<code>e2e_batch</code>]</td><td><code>etl</code> <code>hp-tuning</code> <code>model-promotion</code> <code>drift-detection</code> <code>batch-prediction</code> <code>scikit-learn</code></td><td>This project template is a good starting point for anyone starting with ZenML. It consists of two pipelines with the following high-level steps: load, split, and preprocess data; run HP tuning; train and evaluate model performance; promote model to production; detect data drift; run batch inference.</td></tr><tr><td><a href="https://github.com/zenml-io/template-nlp">NLP Training Pipeline</a> [<code>nlp</code>]</td><td><code>nlp</code> <code>hp-tuning</code> <code>model-promotion</code> <code>training</code> <code>pytorch</code> <code>gradio</code> <code>huggingface</code></td><td>This project template is a simple NLP training pipeline that walks through tokenization, training, HP tuning, evaluation and deployment for a BERT or GPT-2 based model and testing locally it with gradio</td></tr></tbody></table>

{% hint style="info" %}
Do you have a personal project powered by ZenML that you would like to see here? At ZenML, we are looking for design partnerships and collaboration to help us better understand the real-world scenarios in which MLOps is being used and to build the best possible experience for our users. If you are interested in sharing all or parts of your project with us in the form of a ZenML project template, please [join our Slack](https://zenml.io/slack/) and leave us a message!
{% endhint %}

## Using a project template

First, to use the templates, you need to have ZenML and its `templates` extras installed:

```bash
pip install zenml[templates]
```

{% hint style="warning" %}
Note that these templates are not the same thing as the templates used for
triggering a pipeline (from the dashboard or via the Python SDK). Those are
known as 'Run Templates' and you can read more about them <a
href="https://docs.zenml.io/how-to/trigger-pipelines">here</a>.
{% endhint %}

Now, you can generate a project from one of the existing templates by using the `--template` flag with the `zenml init` command:

```bash
zenml init --template <short_name_of_template>
# example: zenml init --template e2e_batch
```

Running the command above will result in input prompts being shown to you. If you would like to rely on default values for the ZenML project template - you can add `--template-with-defaults` to the same command, like this:

```bash
zenml init --template <short_name_of_template> --template-with-defaults
# example: zenml init --template e2e_batch --template-with-defaults
```

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
