---
description: Learn how to use workspaces in ZenML Pro.
---

# Workspaces

{% hint style="info" %}
**Note**: Workspaces were previously called "Tenants" in earlier versions of ZenML Pro. We've updated the terminology to better reflect their role in organizing MLOps resources.
{% endhint %}

Workspaces are individual, isolated deployments of the ZenML server. Each workspace has its own set of users, roles, projects, and resources. Essentially, everything you do in ZenML Pro revolves around a workspace: all of your projects, pipelines, stacks, runs, connectors and so on are scoped to a workspace.



![Image showing the workspace page](<.gitbook/assets/Workspace - Home.png>)

The ZenML server that you get through a workspace is a supercharged version of the open-source ZenML server. This means that you get all the features of the open-source version, plus some extra Pro features.

## Connecting to Your Workspace

### Using the CLI

To use a workspace, you first need to log in using the ZenML CLI. The basic command is:

```bash
zenml login <WORKSPACE_NAME>
```

If you're using a self-hosted version of ZenML Pro, you'll need to specify the API URL:

```bash
zenml login <WORKSPACE_NAME> --pro-api-url <URL_OF_STAGING>
```

{% hint style="info" %}
The `--pro-api-url` parameter is only required for self-hosted deployments. If you're using the SaaS version of ZenML Pro, you can omit this parameter.
{% endhint %}

After logging in, you can initialize your ZenML repository and start working with your workspace resources:

```bash
# Initialize a new ZenML repository
zenml init

# Set up your active project (recommended)
zenml project set default

# Set up your active stack
zenml stack set default
```

### Using the Dashboard

You can also access your workspace through the web dashboard, which provides a graphical interface for managing all your MLOps resources.

## Create a Workspace in your organization

A workspace is a crucial part of your Organization and serves as a container for your projects, which in turn hold your pipelines, experiments and models, among other things. You need to have a workspace to fully utilize the benefits that ZenML Pro brings. The following is how you can create a workspace yourself:

{% stepper %}
{% step %}
### Go to your organization page

![Image showing the create workspace page](<.gitbook/assets/Organization - Home.png>)


{% endstep %}

{% step %}
### Click on the "New Workspace" button

<figure><img src=".gitbook/assets/image (1).png" alt=""><figcaption><p>Image showing the "New Workspace" button</p></figcaption></figure>
{% endstep %}

{% step %}
### Add a name and id

Give your workspace a name, an id, and click on the "**Create Workspace**" button.

{% hint style="warning" %}
**Important**: The workspace ID must be globally unique across all ZenML instances and cannot be changed after creation. Choose carefully as this permanent identifier will be used in all future API calls and references.
{% endhint %}

<figure><img src=".gitbook/assets/New Workspace.png" alt="" width="375"><figcaption></figcaption></figure>


{% endstep %}

{% step %}
### Your workspace is ready!

The workspace will then be created and added to your organization. In the meantime, you can already get started with setting up your environment for the onboarding experience.

The image below shows you how the overview page looks like when you are being onboarded. Follow the instructions on the screen to get started.

![Image showing the onboarding experience](../../.gitbook/assets/tenant_onboarding.png)

{% hint style="info" %}
You can also create a workspace through the Cloud API by navigating to https://cloudapi.zenml.io/ and using the `POST /organizations` endpoint to create a workspace.
{% endhint %}
{% endstep %}
{% endstepper %}

## Organizing your workspaces

Organizing your workspaces effectively is crucial for managing your MLOps infrastructure efficiently. There are primarily two dimensions to consider when structuring your workspaces:

### Organizing workspaces in `staging` and `production`

One common approach is to separate your workspaces based on the development stage of your ML projects. This typically involves creating at least two types of workspaces:

1. **Staging Workspaces**: These are used for development, testing, and experimentation. They provide a safe environment where data scientists and ML engineers can:
   * Develop and test new pipelines
   * Experiment with different models and hyperparameters
   * Validate changes before moving to production
2. **Production Workspaces**: These host your live, customer-facing ML services. They are characterized by:
   * Stricter access controls
   * More rigorous monitoring and alerting
   * Optimized for performance and reliability

This separation allows for a clear distinction between experimental work and production-ready systems, reducing the risk of untested changes affecting live services.

![Staging vs production workspaces](../../.gitbook/assets/staging-production-workspaces.png)

### Organizing workspaces by business logic

Another approach is to create workspaces based on your organization's structure or specific use cases. This method can help in:

1. **Department-based Separation**: Create workspaces for different departments or business units:
   * Data Science Department Workspace
   * Research Department Workspace
   * Production Department Workspace
2. **Team-based Separation**: Align workspaces with your organizational structure:
   * ML Engineering Team Workspace
   * Research Team Workspace
   * Operations Team Workspace
3. **Data Classification**: Separate workspaces based on data sensitivity:
   * Public Data Workspace
   * Internal Data Workspace
   * Highly Confidential Data Workspace

This organization method offers several benefits:

* Improved resource allocation and cost tracking
* Better alignment with team structures and workflows
* Enhanced data security and compliance management

![Business logic-based workspace organization](../../.gitbook/assets/business-logic-workspaces.png)

Of course, both approaches of organizing your workspaces can be mixed and matched to create a structure that works best for you.

### Best Practices for Workspace Organization

Regardless of the approach you choose, consider these best practices:

1. **Clear Naming Conventions**: Use consistent, descriptive names for your workspaces to easily identify their purpose.
2. **Access Control**: Implement [role-based access control](roles.md) within each workspace to manage permissions effectively.
3. **Project Organization**: Structure [projects](projects.md) within workspaces to provide additional resource isolation and access control.
4. **Documentation**: Maintain clear documentation about the purpose and contents of each workspace and its projects.
5. **Regular Reviews**: Periodically review your workspace structure to ensure it still aligns with your organization's needs.
6. **Scalability**: Design your workspace structure to accommodate future growth and new projects.

By thoughtfully organizing your workspaces and their projects, you can create a more manageable, secure, and efficient MLOps environment that scales with your organization's needs.

## Using your workspace

As previously mentioned, a workspace is a supercharged ZenML server that you can use to manage projects, run pipelines, carry out experiments and perform all the other actions you expect out of your ZenML server.

Some Pro-only features that you can leverage in your workspace are as follows:

* [Projects for Resource Organization](projects.md)
* [Model Control Plane](https://docs.zenml.io/how-to/model-management-metrics/model-control-plane/register-a-model)
* [Artifact Control Plane](https://docs.zenml.io/how-to/data-artifact-management/handle-data-artifacts)
* [Ability to run pipelines from the Dashboard](https://docs.zenml.io/how-to/trigger-pipelines/use-templates-rest-api),
* [Create templates out of your pipeline runs](https://docs.zenml.io/how-to/trigger-pipelines/use-templates-rest-api)

and [more](https://zenml.io/pro)!

### Accessing workspace docs

Every workspace (formerly known as tenant) has a name which you can use to connect your `zenml` client to your deployed Pro server via the `zenml login` CLI command.

{% hint style="info" %}
In the API documentation and some error messages, you might still see references to "tenant" instead of "workspace". These terms refer to the same concept and will be updated in future releases.
{% endhint %}

![Image showing the workspace swagger docs](../../.gitbook/assets/swagger_docs_zenml.png)

Read more about to access the API [here](https://docs.zenml.io/api-reference).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
