---
description: >
  Learn about the different roles you can assign to your team members in ZenML Pro.
---

# Roles in ZenML Pro

In ZenML Pro, you can assign roles to your team members to have better control over who can do what. Roles can be assigned at the organization level and the tenant level.

## Organization Roles

At the organization level, you can assign the following roles to people.

TODO: figma design of the org roles page. dont want to take a screenshot with emails.

- **Org admin**: This role has full control over the organization. They can add
  members, create and update tenants, adjust the billing information and assign roles.
- **Org editor**: This role can manage tenants and members but is not allowed to
  access the subscription information or delete the organization.
- **Org viewer**: This role can view the tenants within the organization with only
  view permissions.

Some points to note:
- In addition to adding organization roles, you might also want to add tenant roles for people who you want to have access to a specific tenant.
- An organization admin can add themselves to a tenant with any tenant role they desire.
- However, an organization editor and viewer cannot add themselves to existing tenants that they are not a part of. They won't be able to view such tenants in the organization either.

You can also send invites to new members with a specific role.

TODO: design of the invite modal.


## Tenant Roles

Once you have added people to your organization, they can start interacting with the tenants in it, respecting the role they have been assigned. Each user needs to also have a tenant role to be able to perform any actions inside a ZenML tenant. You can choose from a selection of predefined roles or create your own custom role.

TODO: figma design of the tenant roles page.

### Predefined Roles

- **Admin**: This role gives the user full control over the tenant. They can create, read, delete and update all resources within the tenant.
- **Editor**: This role gives the user permissions to create, read and share resources but not modify or delete existing ones.
- **Viewer**: This role gives the user read-only access to all resources and information in the tenant.

### Custom Roles

You can also create your own custom roles. This is useful if you want to give a user access to a specific resource but not to others.

To create a custom role, follow these steps:

- In your tenant page, click on the "Settings" tab.
- Click on "Roles" in the left-hand sidebar and select "Add Custom Role".
- Fill in the name and description of the role and choose a base role to inherit permissions from. This helps you get started faster with the base permissions already filled in.
- Once you have created the role, you can now click on it to perform actions like adding memebers and editing permissions.
- Edit the permissions of the role and add specific actions on certain resources as you wish.
- You can then assign this role to a user on the "Members" page.

