---
description: >-
  Learn about the different roles and permissions you can assign to your team
  members in ZenML Pro.
---

# Roles & Permissions

ZenML Pro offers a robust role-based access control (RBAC) system to manage permissions across your organization, workspaces, and projects. This guide will help you understand the different roles available at each level, how to assign them, and how to create custom roles tailored to your team's needs.

Please note that roles can be assigned to both individual users and [teams](teams.md).

## Organization-Level Roles

At the organization level, ZenML Pro provides the following predefined roles:

1. **Organization Admin**
   * Full permissions to any organization resource
   * Can manage all aspects of the organization
   * Can create and manage workspaces
   * Can manage billing and team members

2. **Organization Manager**
   * Permissions to create and view resources in the organization
   * Can manage most organization settings
   * Cannot access billing information

3. **Organization Viewer**
   * Permissions to view resources in the organization
   * Read-only access to organization resources

4. **Billing Admin**
   * Permissions to manage the organization's billing information
   * Can view and modify billing settings

5. **Organization Member**
   * Minimal permissions in the organization
   * Basic access to organization resources

To assign organization roles:

{% stepper %}
{% step %}
Navigate to the **Organization** **Settings** page


{% endstep %}

{% step %}
Click on the **Members** tab. Here you can update roles for existing members.


{% endstep %}

{% step %}
Use the **Add members** button to add new members

![Screenshot showing the invite modal](../../.gitbook/assets/add_org_members.png)
{% endstep %}
{% endstepper %}

Some points to note:

* In addition to adding organization roles, you might also want to add workspace or project roles for people who you want to have access to specific resources.
* However, organization viewers and members cannot add themselves to existing workspaces that they are not a part of.
* Currently, you cannot create custom organization roles via the ZenML Pro dashboard. However, this is possible via the [ZenML Pro API](https://cloudapi.zenml.io/).

## Workspace-Level Roles

Workspace roles determine a user's permissions within a specific ZenML workspace. The following predefined roles are available:

1. **Workspace Admin**
   * Full permissions to any workspace resource
   * Can manage workspace settings and members
   * Can create and manage projects
   * Has complete control over all workspace resources

2. **Workspace Developer**
   * Permissions to create and view resources in the workspace and all projects
   * Can work with pipelines, artifacts, and models
   * Cannot modify workspace settings

3. **Workspace Contributor**
   * Permissions to create resources in the workspace, but not access or create projects
   * Can add new resources to the workspace
   * Limited access to project resources

4. **Workspace Viewer**
   * Permissions to view resources in the workspace and all projects
   * Read-only access to workspace resources

5. **Stack Admin**
   * Permissions to manage stacks, components and service connectors
   * Specialized role for infrastructure management

## Project-Level Roles

Projects have their own set of roles that provide fine-grained control over project-specific resources. These roles are scoped to the project level:

1. **Project Admin**
   * Full permissions to any project resource
   * Can manage project members and their roles
   * Can configure project settings
   * Has complete control over project resources

2. **Project Developer**
   * Permissions to create and view resources in the project
   * Can work with pipelines, artifacts, and models
   * Cannot modify project settings or member roles

3. **Project Contributor**
   * Permissions to create resources in the project
   * Can add new pipelines, artifacts, and models
   * Cannot modify existing resources or settings

4. **Project Viewer**
   * Permissions to view resources in the project
   * Read-only access to project resources
   * Cannot create or modify any resources

## Managing Roles

To manage roles at any level:

{% stepper %}
{% step %}
Navigate to the appropriate settings page (Organization, Workspace, or Project)
{% endstep %}

{% step %}
Select the **Members** tab
{% endstep %}

{% step %}
Use **Add Member** or modify existing member roles
{% endstep %}
{% endstepper %}

## Best Practices

1. **Least Privilege**: Assign the minimum necessary permissions to each role.
2. **Regular Audits**: Periodically review and update role assignments and permissions.
3. **Role Hierarchy**: Consider the relationship between organization, workspace, and project roles when assigning permissions.
4. **Team-Based Access**: Use teams to manage access control more efficiently across all levels.
5. **Documentation**: Maintain clear documentation about role assignments and their purposes.
6. **Regular Reviews**: Periodically audit role assignments to ensure they align with current needs.

By leveraging ZenML Pro's comprehensive role-based access control, you can ensure that your team members have the right level of access to resources while maintaining security and enabling collaboration across your MLOps projects.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
