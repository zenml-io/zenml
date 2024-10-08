# Organizations

ZenML Pro arranges various aspects of your work experience around the concept
of an **Organization**. This is the top-most level structure within the ZenML Cloud environment.
Generally, an organization contains a group of users and one or more [tenants](../../../../docs/book/getting-started/zenml-pro/tenants.md).

## Create a Tenant in your organization

A tenant is a crucial part of your Organization and holds all of your pipelines, experiments and models, among other things. You need to have a tenant to fully utilize the benefits that ZenML Pro brings. The following is how you can create a tenant yourself:

- Go to your organization page
- Click on the "+ New Tenant" button
    ![Image showing the create tenant page](../../.gitbook/assets/new_tenant.png)
- Give your tenant a name and click on the "Create Tenant" button
    ![Image showing the create tenant modal](../../.gitbook/assets/new_tenant_modal.png)

The tenant will be created in some time and added to your organization. In the meantime, you can already get started with setting up your environment for the onboarding experience.

The image below shows you how the overview page looks like when you are being onboarded. Follow the instructions on the screen to get started.

![Image showing the onboarding experience](../../.gitbook/assets/tenant_onboarding.png)

{% hint style="info" %}
You can also create a tenant through the Cloud API by navigating to https://cloudapi.zenml.io/ and using the `POST /organizations` endpoint to create a tenant.
{% endhint %}

## Inviting Team Members to Your Organization

Inviting users to your organization to work on the organization's tenants is
easy. Simply click `Add Member` in the Organization settings, and give them an
initial Role. The User will be sent an invitation email. If a user is part of an
organization, they can utilize their login on all tenants they have authority to
access.

![Image showing invite flow](../../.gitbook/assets/add_org_members.png)


## Manage Organization settings like billing and roles

The billing information for your tenants is managed on the organization level, among other settings like the members in your organization and the roles they have. You can access the organization settings by clicking on your profile picture in the top right corner and selecting "Settings".

![Image showing the organization settings page](../../.gitbook/assets/org_settings.png)


## Other operations involving organizations

There are a lot of other operations involving Organizations that you can perform directly through the API. You can find more information about the API by visiting https://cloudapi.zenml.io/.

![Image showing the swagger docs](../../.gitbook/assets/cloudapi_swagger.png)