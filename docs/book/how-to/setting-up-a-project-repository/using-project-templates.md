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

## Generating project from a project template

First, to use the templates, you need to have ZenML and its `templates` extras installed:

```bash
pip install zenml[templates]
```

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

## Creating your own ZenML template

Creating your own ZenML template is a great way to standardize and share your ML workflows across different projects or teams. ZenML uses [Copier](https://copier.readthedocs.io/en/stable/) to manage its project templates. Copier is a library that allows you to generate projects from templates. It's simple, versatile, and powerful.

Here's a step-by-step guide on how to create your own ZenML template:

1. **Create a new repository for your template.** This will be the place where you store all the code and configuration files for your template.
2. **Define your ML workflows as ZenML steps and pipelines.** You can start by copying the code from one of the existing ZenML templates (like the [starter template](https://github.com/zenml-io/template-starter)) and modifying it to fit your needs.
3. **Create a `copier.yml` file.** This file is used by Copier to define the template's parameters and their default values. You can learn more about this config file [in the copier docs](https://copier.readthedocs.io/en/stable/creating/).
4. **Test your template.** You can use the `copier` command-line tool to generate a new project from your template and check if everything works as expected:

```bash
copier copy https://github.com/your-username/your-template.git your-project
```

Replace `https://github.com/your-username/your-template.git` with the URL of your template repository, and `your-project` with the name of the new project you want to create.

5. **Use your template with ZenML.** Once your template is ready, you can use it with the `zenml init` command:

```bash
zenml init --template https://github.com/your-username/your-template.git
```

Replace `https://github.com/your-username/your-template.git` with the URL of your template repository.

If you want to use a specific version of your template, you can use the `--template-tag` option to specify the git tag of the version you want to use:

```bash
zenml init --template https://github.com/your-username/your-template.git --template-tag v1.0.0
```

Replace `v1.0.0` with the git tag of the version you want to use.

That's it! Now you have your own ZenML project template that you can use to quickly set up new ML projects. Remember to keep your template up-to-date with the latest best practices and changes in your ML workflows.

Our [Production Guide](../../user-guide/production-guide/README.md) documentation is built around the `E2E Batch` project template codes. Most examples will be based on it, so we highly recommend you to install the `e2e_batch` template with `--template-with-defaults` flag before diving deeper into this documentation section, so you can follow this guide along using your own local environment.

```bash
mkdir e2e_batch
cd e2e_batch
zenml init --template e2e_batch --template-with-defaults
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
