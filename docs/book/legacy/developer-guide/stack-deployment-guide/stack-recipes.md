---
description: Introduction to Stack recipes which help you deploy a full MLOps stack in minutes!
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


When we first created ZenML as an extensible MLOps framework for creating portable, production-ready MLOps pipelines, we saw many of our users having to deal with the pain of deploying infrastructure from scratch to run these pipelines. 

The expertise of setting up these often-complex stacks up shouldn't be a pre-requisite to running your ML pipelines. We created stack recipes as a way to allow you to quickly get started with a full-fledged MLOps stack with the execution of just a couple of simple commands. Read on to learn what a recipe is, how you can deploy it and the steps needed to create your own!

## Stack Recipes 🍱

A Stack Recipe is a collection of carefully-crafted Terraform modules and resources which when executed creates a range of stack components that can be used to run your pipelines. Each recipe is designed to offer a great deal of flexibility in configuring the resources while preserving the ease of application through the use of sensible defaults.

Check out the full list of available recipes at the [mlops-stacks repository](https://github.com/zenml-io/mlops-stacks#-list-of-recipes).

## Deploying a recipe 🚀

{% hint style="info" %}
To use the stack recipe CLI commands, you will have to install some optional dependencies with `zenml`. 
Run `pip install "zenml[stacks]"` to get started! 
{% endhint %}

Detailed steps are available in the README of the respective recipe but here's what a simple flow could look like:

1. 📃 List the available recipes in the repository.

    ```
    zenml stack recipe list
    ```

2. Pull the recipe that you wish to deploy, to your local system.

    ```
    zenml stack recipe pull <STACK_RECIPE_NAME>
    ``` 

3. 🎨 Customize your deployment by editing the default values in the `locals.tf` file. This file holds all the configurable parameters for each of the stack components.

4. 🔐 Add your secret information like keys and passwords into the `values.tfvars.json` file which is not committed and only exists locally.

5. 🚀 Deploy the recipe with this simple command.

    ```
    zenml stack recipe deploy <STACK_RECIPE_NAME>
    ```

    If you want to allow ZenML to automatically import the created resources as a ZenML stack, pass the `--import` flag to the command above. 
    By default, the imported stack will have the same name as the stack recipe and you can provide your own with the `--stack-name` option.


6. You'll notice that a ZenML stack configuration file gets created after the previous command executes 🤯! This YAML file can be imported as a ZenML stack manually by running the following command.

    ```
    zenml stack import <STACK_NAME> -f <PATH_TO_THE_CREATED_STACK_CONFIG_YAML>
    ```

## Deleting resources

1. 🗑️ Once you're done running your pipelines, there's only a single command you need to execute that will take care of cleaning up all the resources that you had created on your cloud. 

    ```
    zenml stack recipe destroy <STACK_RECIPE_NAME>
    ```

2. (Optional) 🧹 You can also remove all the downloaded recipe files from the `pull` execution by using the `clean` command.

    ```
    zenml stack recipe clean
    ```

Check out the [API docs](https://apidocs.zenml.io/) to learn more about each of these commands and the options that are available.


## Integration with the ZenML CLI 🙏

The ZenML CLI offers a set of commands to make it easy for you to list, pull and deploy recipes from anywhere!

In addition to the underlying `terraform` functionality, these commands also offer the following:

- ability to list all the available recipes conveniently before you choose to deploy any one of them.
- checks to ensure that you have all the binaries/tools installed for running a recipe.
- extensive logs and error messages that guide you in case any of the recipes fails or misbehaves.
- option to automatically import a ZenML stack, out of the components created after deploying a stack recipe.

More features that are planned 👇: 
- ability to run the recipe commands in background. This is helpful as some recipes might take up to 20 minutes to get fully deployed.
- checking your credentials to make sure you have the right permissions for deploying all the stack components.
- any feature you'd want to see next? Submit a request on our [hellonext board](https://zenml.hellonext.co/roadmap).


## Creating your own recipe 🧑‍🍳

The number of recipes available right now is finite and there can be combinations of stack components that are not yet covered by any of the existing recipes. If you wish, you can contribute a recipe for any combination that you'd like to see. 

The [`CONTRIBUTING.md`](https://github.com/zenml-io/mlops-stacks/blob/main/CONTRIBUTING.md) file on the repository lists the principles that each recipe follows and gives details about the steps you should take when designing your own recipe. Feel free to also reach out to the ZenML community on [Slack](https://zenml.slack.com/ssb/redirect) 👋 if you need help with any part of the process!  

