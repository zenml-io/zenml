# Tenants

Tenants are individual, isolated deployments of the ZenML server. Each tenant has its own set of users, roles, and resources. Essentially, everything you do in ZenML Pro revolves around a tenant: all of your pipelines, stacks, runs, connectors, etc. are scoped to a tenant.

![Image showing the tenant page](../../.gitbook/assets/custom_role_settings_page.png)

The ZenML server that you get through a tenant is a supercharged version of the open-source ZenML server. This means that you get all the features of the open-source version, plus some extra Pro features.

## Organizing your tenants
You can also restrict what your team members can access within a tenant by using roles. Read more about roles [here](../../../../docs/book/getting-started/zenml-pro/roles.md).

You can choose to define and organize tenants in any way you wish, depending on your needs. One example could be creating different tenants for different projects or teams in your organization.
The diagram below shows this use case, where folks working on the recommender systems, LLMs and fraud detection each have a separate tenant.

![Image showing the tenants for different teams](../../.gitbook/assets/zenml_pro_tenants_teams1.png)

This helps you better manager project resources. You can imagine that 
- certain teams might be based in a different region and have requirements for deployments within that region.
- some teams may have external contributors and you don't want them to have any knowledge of other internal tenants and projects.

...and so on.

One other example could be separating tenants based on the type of data they handle. The diagram below shows how C1 and C2 type data (highly confidential) are handled differently.

![Image showing the tenants for different types of data](../../.gitbook/assets/zenml_pro_c1_c2.png)

## Using your tenant

As said already, a tenant is a supercharged ZenML server that you can use to run your pipelines, carry out experiments and perform all the other actions you expect out of your ZenML server.

Some Pro-only features that you can leverage in your tenant are as follows:
- the [Model Control Plane](../../../../docs/book/how-to/use-the-model-control-plane/register-a-model.md)
- Artifact Control Plane
- [ability to run pipelines from the Dashboard](../../../../docs/book/how-to/trigger-pipelines/use-templates-rest-api.md), 
- [create templates out of your pipeline runs](../../../../docs/book/how-to/trigger-pipelines/use-templates-rest-api.md)

and more!

### Accessing tenant docs

Every tenant has a connection URL that you can use to connect your `zenml` client to your deployed Pro server. This URL can also be used to access the OpenAPI specification for the ZenML Server.
Simply visit `<URL>/docs` on your browser to see a full list of methods that you can execute from it, like running a pipeline through the REST API.

![Image showing the tenant swagger docs](../../.gitbook/assets/swagger_docs_zenml.png)