---
description: How to include ZenML in the CI/CD/CT workflows
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Productionalize with CI/CD/CT

In many production settings, it is undesirable to have all developers accessing and running on the production environments. Therefore, it is best to "gate" certain pipelines running on production stacks. This can be achieved through the concept of Continuous Integration and Continuous Deployment (CI/CD).

CI/CD represents an approach to continuously integrate new code, data, and features into existing pipelines, validate the quality through automated testing, and then automatically deploy improved and tested ML pipelines into production. Practically, this means that the running of the pipeline on a certain stack should be done not on a local developer machine, but rather than in a CI job, using services like [Jenkins](https://www.jenkins.io/), [GitHub Actions](https://github.com/features/actions), [Circle CI](https://circleci.com/), and more.

## The Git Workflow

Here is what such a CI/CD system could look like:

<div>

<img src="../../assets/diagrams/Remote_with_git_ops.png" alt="">

 

<figure><img src="../../.gitbook/assets/Remote_with_git_ops.png" alt=""><figcaption><p>How to use ZenML with CI/CD frameworks</p></figcaption></figure>

</div>

You can find a practical example that uses the visualized flow [here](https://github.com/zenml-io/zenml-gitflow). In particular, take a look at the [workflow file here](https://github.com/zenml-io/zenml-gitflow/blob/main/.github/workflows/production.yaml).

In essence, this is what happens:

1\) User writes and pushes code to their code repository

2\) The CI/CD Framework of the code repository starts a worker

3\) Within this worker zenml and other requirements will be installed

4 - 6) The worker connects to the ZenML server and triggers a pipeline run

7 - 11) The pipeline is now executed on the stack of choice

## Best Practices

* Create a [dedicated user](user-management.md) for the CI/CD workflow.
* Always make sure to call `zenml connect` in your worker during setup with the above user. Make sure the credentials are secrets in your workflow.
* Create a `staging` stack when merging to a `develop` branch, and trigger the `production` workflow only when merging to the `main` branch.
* Understand how [containerization](../../user-guide/advanced-guide/containerize-your-pipeline.md) works in ZenML, and leverage advantages such as build-caching and code repository.
