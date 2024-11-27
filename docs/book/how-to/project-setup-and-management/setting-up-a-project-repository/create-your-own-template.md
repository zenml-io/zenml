---
description: How to create your own ZenML template.
---

# Create your own ZenML template

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

Our [Production Guide](../../../user-guide/production-guide/README.md) documentation is built around the `E2E Batch` project template codes. Most examples will be based on it, so we highly recommend you to install the `e2e_batch` template with `--template-with-defaults` flag before diving deeper into this documentation section, so you can follow this guide along using your own local environment.

```bash
mkdir e2e_batch
cd e2e_batch
zenml init --template e2e_batch --template-with-defaults
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
