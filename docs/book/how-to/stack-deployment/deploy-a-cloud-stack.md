---
description: Deploy a cloud stack easily
---

# Deploy a cloud stack with a single click

In ZenML, the [stack]() is a fundamental concept that represents the 
configuration of your infrastructure. In a normal workflow, creating a stack
requires you to first deploy the necessary pieces of infrastructure and then 
define them as stack components in ZenML with proper authentication.

Especially in a remote setting, this process can sometimes be challenging and 
time-consuming, and it may create a multi-faceted problem. This is why we 
implemented a feature, that allows you to **deploy the necessary pieces of 
infrastructure on your selected cloud provider and get you started on remote 
stack with a single click**.

{% hint style="info" %}
If you have the required infrastructure pieces already deployed on your cloud, 
you can also use the stack wizard to seamlessly register your stack.
{% endhint %}

## How to use 1-click deployment tool?

To use the 1-click deployment tool, you can either use the dashboard or 
the CLI:

{% tabs %}
{% tab title="Dashboard" %}

In order to create a remote stack over the dashboard go to the stacks page 
on the dashboard and click "+ New Stack".

![The new stacks page](../../.gitbook/assets/register_stack_button.png)

Since we will be deploying it from scratch, select "New Infrastructure" on the
next page:

![Options for registering a stack](../../.gitbook/assets/register_stack_page.png)

{% hint style="warning" %}
Currently, the 1-click deployment only works on AWS. We are working on 
bringing support to GCP and Azure as well. Stay in touch for further updates.
{% endhint %}

![Choosing a cloud provider](../../.gitbook/assets/deploy_stack_selection.png)

### AWS

If you choose `aws` as your provider, you will see a page where you will have 
to select a region and a name for your new stack:

![Configuring the new stack](../../.gitbook/assets/deploy_stack_aws.png)

Once the configuration is finished, you will see a deployment page:

![Deploying the new stack](../../.gitbook/assets/deploy_stack_aws_2.png)

During this process, you  will be redirected you to a Cloud Formation page 
on AWS. 

![Cloudformation page](../../.gitbook/assets/deploy_stack_aws_cloudformation_intro.png)


You will have to log in to your AWS account, review and confirm the 
pre-filled configuration and create the stack.

![Finalizing the new stack](../../.gitbook/assets/deploy_stack_aws_cloudformation.png)

{% endtab %}
{% tab title="CLI" %}

In order to create a remote stack over the CLI you can use the following 
command:

```shell
zenml stack deploy -p aws
```

{% hint style="warning" %}
Currently, the 1-click deployment only works on AWS. We are working on 
bringing support to GCP and Azure as well. Stay in touch for further updates.
{% endhint %}

### AWS 

If you choose `aws` as your provider, this command will redirect you to a 
Cloud Formation page on AWS: 

![Cloudformation page](../../.gitbook/assets/deploy_stack_aws_cloudformation_intro.png)

You will have to log in to your AWS account, review and confirm the 
pre-filled configuration and create the stack.

![Finalizing the new stack](../../.gitbook/assets/deploy_stack_aws_cloudformation.png)

{% endtab %}
{% endtabs %}

## What will be deployed?

Here is an overview of the infrastructure that the 1-click deployment will
prepare for you:

{% tabs %}
{% tab title="AWS" %}
- An IAM user and IAM role with the minimum necessary permissions to access 
the resources listed below.
- An AWS access key used to give access to ZenML to connect to the above 
resources through a ZenML service connector.
- A ZenML Sagemaker Orchestrator which is preconfigured.
- An S3 bucket that will be used as a ZenML Artifact Store.
- An ECR container registry that will be used as a ZenML Container Registry.
{% endtab %}
{% tab title="GCP" %}
We are working on bringing the support for the 1-click deployment feature 
to GCP! Stay in touch for further updates.
{% endtab %}
{% tab title="Azure" %}
We are working on bringing the support for the 1-click deployment feature 
to Azure! Stay in touch for further updates.
{% endtab %}
{% endtabs %}

There you have it! With a single click, you just deployed a cloud stack 
and, you can start running your pipelines on a remote setting.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
