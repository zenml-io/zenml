# ☁️ ZenML Pro

The Pro version of ZenML comes with a number of features that expand the
functionality of the Open Source product. Supercharge your MLOps with a fully-managed control plane

## Hierarchy of concepts in ZenML Pro

In ZenML Pro, there is a slightly different entity hierarchy as compared to the open-source ZenML
framework. This document walks you through the key differences and new concepts that are only available for Pro users.

![Image showing the entity hierarchy in ZenML Pro](../../.gitbook/assets/org_hierarchy_pro.png)

The image above shows the hierarchy of concepts in ZenML Pro.

- At the top level is your [Organization](../../../../docs/book/getting-started/zenml-pro/organization.md). An organization is a collection of users and tenants.
- Each [Tenant](../../../../docs/book/getting-started/zenml-pro/tenants.md) is an isolated deployment of ZenML Pro. It contains all the resources for your project or team.
- **Users** are people who have access to your ZenML Pro instance.
- [Roles](../../../../docs/book/getting-started/zenml-pro/roles.md) are used to control what actions users can perform within a tenant or inside an organization.

More details about each of these concepts are available in their linked pages.

### Role-based access control and permissions

Utilizing ZenML Pro provides you with access to a robust control plane that
unifies user management and optimizes your workflows. Efficiently manage access
and permissions through centralized user administration. Create fine-grained
permissions for resources such as stacks, pipelines, models, etc.

See the section on [roles](./roles.md) to learn more.

### A brand-new, modern MLOps experience

![Walkthrough of ZenML Model Control Plane](../../.gitbook/assets/mcp_walkthrough.gif)

We have built the ZenML Pro experience from the ground-up. With ZenML Pro, you get
access to a new dashboard, with a better experience. The new dashboard features
more functionality such as
the [Model Control Plane](../../user-guide/starter-guide/track-ml-models.md)
and [Artifact Control Plane](../../user-guide/starter-guide/manage-artifacts.md).

### Run templates for running your pipelines from the dashboard or the API

ZenML Pro enables you to [create and run templates](../../how-to/trigger-pipelines/README.md#run-templates).
This way, you can use the dashboard or our Client/REST API to run a pipeline with updated configuration
which allows you to iterate quickly with minimal friction. 

### Triggers, CI/CD, Reports and more

Additionally, ZenML Pro users get exclusive access to an array of
cloud-specific features, such as triggers, integrating with your code
repository CI/CD system, generating usage reports and more.

Learn more about ZenML Pro on the [ZenML Website](https://zenml.io/pro).

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
