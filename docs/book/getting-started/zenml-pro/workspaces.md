---
description: >
  Learn how to use workspaces in ZenML Pro.
---

# Workspaces

Workspaces are individual, isolated deployments of the ZenML server. Each workspace has its own set of users, roles, and resources. Essentially, everything you do in ZenML Pro revolves around a workspace: all of your pipelines, stacks, runs, connectors and so on are scoped to a workspace.

![Image showing the workspace page](../../.gitbook/assets/custom_role_settings_page.png)

The ZenML server that you get through a workspace is a supercharged version of the open-source ZenML server. This means that you get all the features of the open-source version, plus some extra Pro features.

## Create a Workspace in your organization

A workspace is a crucial part of your Organization and holds all of your pipelines, experiments and models, among other things. You need to have a workspace to fully utilize the benefits that ZenML Pro brings. The following is how you can create a workspace yourself:

- Go to your organization page
- Click on the "+ New Workspace" button

![Image showing the create workspace page](../../.gitbook/assets/new_tenant.png)

- Give your workspace a name and click on the "Create Workspace" button

![Image showing the create workspace modal](../../.gitbook/assets/new_tenant_modal.png)

The workspace will then be created and added to your organization. In the meantime, you can already get started with setting up your environment for the onboarding experience.

The image below shows you how the overview page looks like when you are being onboarded. Follow the instructions on the screen to get started.

![Image showing the onboarding experience](../../.gitbook/assets/tenant_onboarding.png)

{% hint style="info" %}
You can also create a workspace through the Cloud API by navigating to https://cloudapi.zenml.io/ and using the `POST /organizations` endpoint to create a workspace.
{% endhint %}

## Organizing your workspaces

Organizing your workspaces effectively is crucial for managing your MLOps infrastructure efficiently. There are primarily two dimensions to consider when structuring your workspaces:

### Organizing workspaces in `staging` and `production`

One common approach is to separate your workspaces based on the development stage of your ML projects. This typically involves creating at least two types of workspaces:

1. **Staging Workspaces**: These are used for development, testing, and experimentation. They provide a safe environment where data scientists and ML engineers can:
   - Develop and test new pipelines
   - Experiment with different models and hyperparameters
   - Validate changes before moving to production

2. **Production Workspaces**: These host your live, customer-facing ML services. They are characterized by:
   - Stricter access controls
   - More rigorous monitoring and alerting
   - Optimized for performance and reliability

This separation allows for a clear distinction between experimental work and production-ready systems, reducing the risk of untested changes affecting live services.

![Staging vs production workspaces](../../.gitbook/assets/staging-production-workspaces.png)

### Organizing workspaces by business logic

Another approach is to create workspaces based on your organization's structure or specific use cases. This method can help in:

1. **Project-based Separation**: Create workspaces for different ML projects or products. For example:
   - Recommendation System Workspace
   - Natural Language Processing Workspace
   - Computer Vision Workspace

2. **Team-based Separation**: Align workspaces with your organizational structure:
   - Data Science Team Workspace
   - ML Engineering Team Workspace
   - Business Intelligence Team Workspace

3. **Data Sensitivity Levels**: Separate workspaces based on data classification:
   - Public Data Workspace
   - Internal Data Workspace
   - Highly Confidential Data Workspace

This organization method offers several benefits:
- Improved resource allocation and cost tracking
- Better alignment with team structures and workflows
- Enhanced data security and compliance management

![Business logic-based workspace organization](../../.gitbook/assets/business-logic-workspaces.png)

Of course, both approaches of organizing your workspaces can be mixed and matched to create a structure that works best for you.

### Best Practices for Workspace Organization

Regardless of the approach you choose, consider these best practices:

1. **Clear Naming Conventions**: Use consistent, descriptive names for your workspaces to easily identify their purpose.
2. **Access Control**: Implement [role-based access control](./roles.md) within each workspace to manage permissions effectively.
3. **Documentation**: Maintain clear documentation about the purpose and contents of each workspace.
4. **Regular Reviews**: Periodically review your workspace structure to ensure it still aligns with your organization's needs.
5. **Scalability**: Design your workspace structure to accommodate future growth and new projects.

By thoughtfully organizing your workspaces, you can create a more manageable, secure, and efficient MLOps environment that scales with your organization's needs.

## Using your workspace

As previously mentioned, a workspace is a supercharged ZenML server that you can use to run your pipelines, carry out experiments and perform all the other actions you expect out of your ZenML server.

Some Pro-only features that you can leverage in your workspace are as follows:

- [Model Control Plane](../../../../docs/book/how-to/model-management-metrics/model-control-plane/register-a-model.md)
- [Artifact Control Plane](../../how-to/data-artifact-management/handle-data-artifacts/README.md)
- [Ability to run pipelines from the Dashboard](../../../../docs/book/how-to/trigger-pipelines/use-templates-rest-api.md), 
- [Create templates out of your pipeline runs](../../../../docs/book/how-to/trigger-pipelines/use-templates-rest-api.md)

and [more](https://zenml.io/pro)!

### Accessing workspace docs

Every workspace has a name which you can use to connect your `zenml` client to your deployed Pro server via the `zenml login`CLI command. The workspace URL can also be used to access the OpenAPI specification for the ZenML Server.
Simply visit `<WORKSPACE_URL>/docs` on your browser to see a full list of methods that you can execute from it, like running a pipeline through the REST API.

![Image showing the workspace swagger docs](../../.gitbook/assets/swagger_docs_zenml.png)

Read more about to access the API [here](../../reference/api-reference.md).<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


