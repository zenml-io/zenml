---
description: An overview of cloud infrastructure for your ML workflows
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


There are many reasons why you might want to move your ML application setup to a cloud environment, from a need for specialized compute 💪 for training jobs to having requirements for a 24x7 load-balanced deployment of your trained model, serving user requests 🚀. 

With ZenML, there are two kinds of deployments to keep in mind:
- The ZenML Core infrastructure deployment - this pertains to deploying ZenML itself. Once ZenML Server is integrated with the ZenML metadata store, this will hold more relevance so keep an eye out!
- The ZenML Stack infrastructure deployment - this comprises the resources that form a part of your ZenML stack like orchestrators, artifact stores, model deployers and more!

This guide focuses on the stack infrastructure deployment and has three sections, each corresponding to a common scenario.

## Options for setting up your infrastructure

This section aims to list out different scenarios that you may find yourself in (subject to your background) and helps you to navigate between the available choices.

### One Click Deployments with Stack Recipes ⏩

If you've have never worked on the infrastructure side of things before and don't want to invest my time in it, check out [One Click Deployments with Stack Recipes](./stack-recipes.md) that shows how you can use the ZenML CLI to setup specialized stacks with the execution of a single command 🚀.

### Manual Deployments 👷

If you're experienced in operations and prefer to manage every last specific of every cloud resource that is being set up, we have a step-by-step guide for AWS, Azure and GCP grouped under [Manual Deployments](./manual-deployments/) with detailed information on every stack component along with other essential things like roles, permissions, connection settings and more. Head over to the page corresponding to your cloud provider to get started!

### Deployments using Terraform 🙅

If you don't want to use ZenML but still need the speed that comes with stack recipes,
we've still got you covered! Check out [Deployments using Terraform](./deploy-terraform.md) to learn how you can use Terraform to create new stacks using the stack recipes, without having to install ZenML.

## 🙆 I can't really decide between these options. What is the recommended approach?
ZenML recommends you use the stack recipes inside the [mlops-stacks repository](https://github.com/zenml-io/mlops-stacks) as the fastest and most reliable way to set up your stack. It has the following advantages:
- Easy and fast deployment with a single command 🤯.
- Simple and efficient to modify any of the components: You can change properties in a config file and Terraform identifies and applies only the relevant changes 😎.
- Comprehensive clean-up: `zenml stack recipe destroy <RECIPE_NAME>` completely deletes any resources that the module had created anywhere in your cloud. Thus, you can be sure that there are no extra bills that you will tragically discover going forward 😉.

More recipes are always coming to the [mlops-stacks repository](https://github.com/zenml-io/mlops-stacks)! If you feel there's one missing, raise an issue and feel free to create a PR too; we are here for the support.
