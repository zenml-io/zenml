---
description: Resources to learn how to use ZenML practically.
---

# 🧩 Examples

## ZenML In Code

## ZenML Examples: Productionalized ML in action

ZenML Examples are small scale production-grade ML use-cases powered by ZenML. They are fully fleshed out, end-to-end, projects that showcase ZenML's capabilities. They can also serve as a template from which to start similar projects.

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th><th data-hidden data-card-cover data-type="files"></th></tr></thead><tbody><tr><td><strong>Build a LLM-powered Community Slack Bot</strong></td><td></td><td><a href="build-a-llm-powered-community-slack-bot.md">build-a-llm-powered-community-slack-bot.md</a></td><td><a href="../../.gitbook/assets/llm.png">llm.png</a></td></tr><tr><td><strong>Summarize news articles with NLP</strong></td><td></td><td><a href="summarize-news-articles-with-nlp.md">summarize-news-articles-with-nlp.md</a></td><td><a href="../../.gitbook/assets/summarize.jpeg">summarize.jpeg</a></td></tr><tr><td><strong>Automated hyper-parameter tuning with CI/CD</strong></td><td></td><td></td><td></td></tr></tbody></table>

### ZenBytes: Learn MLOps with ZenML

[ZenBytes](https://github.com/zenml-io/zenbytes) is a series of short practical MLOps lessons through ZenML and its various integrations. It is intended for people looking to learn about MLOps generally, and also for ML practitioners who want to get started with ZenML.

After you've run and understood the example above, your next port of call is probably either the [fully-fleshed-out quickstart example](https://github.com/zenml-io/zenml/tree/main/examples/quickstart) and then to look at [the ZenBytes repository](https://github.com/zenml-io/zenbytes) and notebooks.

[Click here to go to ZenBytes](https://github.com/zenml-io/zenbytes)

ZenBytes shares a close link to the [Practical MLOps](../advanced-guide/practical/practical-mlops.md) section of the docs.

### ZenML Project Templates: Generate your own ZenML projects

Use one of our ZenML Project Templates to generate ready-to-use scaffolding for your own projects, with everything you need to get started: ZenML steps, pipelines, stack configurations and other useful resources.

[Click here to go to ZenML Project Templates](https://github.com/zenml-io/zenml-project-templates)

### YouTube Tutorials

If you're a visual learner, then the [official ZenML YouTube channel](https://www.youtube.com/c/ZenML) is the place to go. It features tutorials, community meetups, and various other announcements regarding the product.

### Blog

The [ZenML Blog](https://blog.zenml.io/) is regularly updated with in-depth tutorials. Filtering with the [zenml tag](https://blog.zenml.io/tag/zenml/) is the best way to find relevant tutorials and can be read at your leisure.

### Slack

If you're missing a starting point, join the [Slack community](https://zenml.io/slack-invite) and let us know!











* [ ] Let's see how we handle this page once the future of `zenml example run` is more certain

One of the best ways to learn ZenML is [through examples](https://github.com/zenml-io/zenml/tree/main/examples). ZenML has a [growing list of examples](https://github.com/zenml-io/zenml/tree/main/examples) showcasing many features and integrations.

There is no need to clone the ZenML repository to get access to examples quickly. Use the series of commands that begin with `zenml example` to download and even run examples.

Get the full list of available examples:

```bash
zenml example list
```

Pick an example to download into your current working directory:

```bash
zenml example pull quickstart
# at this point a `zenml_examples` dir will be created with the example(s) inside it.
# this dir will be located in your current working directory.
```

Some of our examples can even be run directly from the CLI. When ready to run the example, type the following command. If there are any dependencies needed to be downloaded for the example to run, the CLI will prompt you to install them.

```bash
zenml example run mlflow-tracking
```

Learn more about all of the ways you can interact with the examples and use them over on [our blogpost about this feature here](https://blog.zenml.io/examples-cli/).

