---
description: An overview of when to use which infrastructure for your ML workflows
---

There can be many motivations behind taking your ML application setup to a cloud environment, from neeeding specialized compute 💪 for training jobs to having a 24x7 load-balanced deployment of your trained model, serving user requests 🚀. 
Whatever your reasons may be, we believe that the process of infrastructure setup should be as simple as possible to allow you to focus more on building your ML solution and less on battling irrelevant cloud woes.

This cloud guide aims to list out different scenarios that you may find yourself in and helps you navigate between the available choices. 

## Options for setting up your infrastructure

Subject to your background, you may relate to one of the situations listed below. Read along and find out what works best for you!

### 👷 I'm experienced in operations and prefer having the knowledge of every cloud resource that is being set up, intimately.

We have a step-by-step guide for AWS and GCP that allows you to follow along and create the necessary infrastructure for your ZenML stack. 

The guides have detailed information on every stack component along with other essential things like roles, permissions, connection settings and more. Head over to the page corresponding to your cloud provider to get started!

### 🤷 I have never worked on the infrastructure side of things before and I don't want to invest my time in it. Is there another way?
There certainly is! You can check out our open-source repository [mlops-stacks]() that has a number of different "recipes", each of which can set up a specialized stack with the execution of just two simple commands.

The `README` file in the project lays out exactly what you need to know and what values you can customize for each recipe while creating your setup. It's also the fastest way to get ready for running your ZenML pipelines 🚀

### 🙅 Not really sure that I want to install a new tool in my workflow. Is there a way to achieve a similar ease of setup without the use of Terraform?
We've got you covered, yet again! Within each cloud guide you can find a set of provider-native CLI commands that you can leverage for the same outcome.

You can just copy and paste each command with minimal modifications for customizing your setup and you're set! 😍

### 🙆 I can't really decide between these options. What is the recommended approach?
ZenML recommends the use of the stack recipes inside the `mlops-stacks` repository as the fastest and most reliable way to set up your stack. It has the following advantages:
- Easy and fast deployment with just two commands 🤯.
- Simple and efficient to modify any of the components: You can change properties in a config file and Terraform identifies and applies only the relevant changes 😎.
- Comprehensive clean-up: `terraform destroy` completely deletes any resources that the module had created anywhere in your cloud. Thus, you can be sure that there are no extra bills that you will tragically discover going forward 😉.

More recipes are always coming up! If you feel there's one missing, raise an issue and feel free to create a PR too; we are here for the support.



# WIP: Overview of cloud guide entries; when to use which infrastructure