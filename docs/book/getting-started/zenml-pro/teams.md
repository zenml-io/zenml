---
icons: users
description: >-
  Learn about Teams in ZenML Pro and how they can be used to manage groups of
  users across your organization and workspaces.
icon: people-group
---

# Teams

ZenML Pro introduces the concept of Teams to help you manage groups of users efficiently. A team is a collection of users that acts as a single entity within your organization and workspaces. This guide will help you understand how teams work, how to create and manage them, and how to use them effectively in your MLOps workflows.

## Understanding Teams

Teams in ZenML Pro offer several key benefits:

1. **Group Management**: Easily manage permissions for multiple users at once.
2. **Organizational Structure**: Reflect your company's structure or project teams in ZenML.
3. **Simplified Access Control**: Assign roles to entire teams rather than individual users.

## Creating and Managing Teams

Teams are created at the organization level and can be assigned roles within workspaces, similar to individual users.

To create a team:

{% stepper %}
{% step %}
**Go to the Organization Settings**

Select **Settings** at the foot of the rail, then open the **Organization** pages.

<figure><img src=".gitbook/assets/image (2).png" alt="Organization settings"><figcaption></figcaption></figure>
{% endstep %}

{% step %}
**Open Teams**

Open **Settings**, then **Teams** under **Organization**.

![Teams settings with the Add Team button](.gitbook/assets/create_team.png)
{% endstep %}

{% step %}
**Add a New Team**

Select **Add Team**.

<figure><img src=".gitbook/assets/image (3).png" alt="Teams list"><figcaption></figcaption></figure>

When creating a team, you'll need to provide:

* Team Name
* Description (optional)
{% endstep %}
{% endstepper %}

## Adding Users to Teams

To add users to an existing team:

{% stepper %}
{% step %}
Open **Settings**, then **Teams** under **Organization**
{% endstep %}

{% step %}
Select the team you want to modify
{% endstep %}

{% step %}
Select **Add members**
{% endstep %}

{% step %}
Choose users from your organization to add to the team

![Add Team Members](.gitbook/assets/add_team_members.png)
{% endstep %}
{% endstepper %}

## Assigning Teams to Workspaces

Teams can be assigned to workspaces just like individual users. To add a team to a workspace:

{% stepper %}
{% step %}
Open **Settings**, then **Access** under **Organization**
{% endstep %}

{% step %}
Pick the workspace in the **Workspace** picker.
{% endstep %}

{% step %}
Select **Add people**
{% endstep %}

{% step %}
Choose the team and assign a role

![Assign Team to Workspace](.gitbook/assets/assign_team_to_tenant.png)
{% endstep %}
{% endstepper %}

## Team Roles and Permissions

When you assign a role to a team within a workspace, all members of that team inherit the permissions associated with that role. This can be a system role (Workspace Admin, Workspace Developer, Workspace Contributor, Workspace Viewer) or a custom role you've created.

For example, if you assign the Workspace Developer role to a team on a workspace, all members of that team are Workspace Developers on that workspace.

![Team Roles](.gitbook/assets/team_roles.png)

## Best Practices for Using Teams

1. **Reflect Your Organization**: Create teams that mirror your company's structure or project groups.
2. **Combine with Custom Roles**: Use custom roles with teams for fine-grained access control.
3. **Regular Audits**: Periodically review team memberships and their assigned roles.
4. **Document Team Purposes**: Maintain clear documentation about each team's purpose and associated projects or workspaces.

By leveraging Teams in ZenML Pro, you can streamline user management, simplify access control, and better organize your MLOps workflows across your organization and workspaces.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
