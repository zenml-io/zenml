---
description: An overview of when to use which infrastructure for your ML workflows
---

There can be many motivations behind taking your ML application setup to a cloud environment, from neeeding specialized compute 💪 for training jobs to having a 24x7 load-balanced deployment of your trained model serving user requests 🚀. 
Whatever your reasons may be, we believe that the process of infrastructure setup should be as simple as possible to allow you to focus more on building your ML solution and less on battling irrelevant cloud woes.

This cloud guide aims to list out different scenarios that you may find yourself in and helps you navigate between the available choices. 

## Three options for setting up your infrastrcuture



We know that the process to set up an MLOps stack can be daunting. There are many components (ever increasing) and each have their own requirements. 


### I'm experienced in operations and prefer having the knowledge of every resource that is being set up intimately.

- We have a step-by-step guide for AWS and GCP that allows you to follow along and create the necessary infrastructure for your ZenML stack. 

### I have never worked on the infrastructure side of things before and I don't want to invest my time in it. Is there another way?
- There certainly is! You can check out our open-source repository [mlops-stacks]() that has a number of different "recipes" each of which can set up a specialized stack with the execution of just two simple commands.

### Not really sure that I want to install a new tool in my workflow. Is there a way to achieve a similar ease of setup without the use of Terraform?
- We've got you covered, yet again! Within each cloud guide you can find a set of provider-native CLI commands that you can leverage for the same outcome.

I can't really decide between these options. What is the recommended approach?
ZenML recommends the use of the stack recipes inside the mlops-stacks repository as the fastest and most reliable way to set up your stack. It has the following advantages:
- Easy and fast deployment with just two commands.
- Simple and efficient to modify any of the components: You can change properties in a config file and Terraform identifies and applies only the relevant changes.
- Comprehensive clean-up: `terraform destroy` completely deletes any resources that the module had created anywhere in your cloud. Thus, you can be sure that there's no extra bills that you will tragically discover going forward.

More recipes are always coming up! If you feel there's one missing, raise an issue and feel free to create a PR too, we are here for the support :).



# WIP: Overview of cloud guide entries; when to use which infrastructure