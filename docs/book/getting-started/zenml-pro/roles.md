---
description: >-
  Learn about the different roles and permissions you can assign to your team
  members in ZenML Pro.
icon: lock
---

# Roles & Permissions

ZenML Pro offers a robust role-based access control (RBAC) system to manage permissions across your organization, workspaces, and projects. This guide will help you understand the different roles available at each level, how to assign them, and how to create custom roles tailored to your team's needs.

Please note that roles can be assigned to both individual users and [teams](teams.md).

## Resource Ownership and Permissions

ZenML Pro implements a resource ownership model where users have full CRUDS (Create, Read, Update, Delete, Share) permissions on resources they create. This applies across all levels of the system:

* Users can always manage resources they've created themselves
* The specific level of access to resources created by others depends on the user's role
* This ownership model ensures that creators maintain control over their resources while still enabling collaboration

## Resource Sharing and Implicit Membership

ZenML Pro allows for flexible resource sharing across the platform:

* Users can share resources (like stacks) with other users who aren't yet members of a workspace
* When a resource is shared with a non-member user:
  * That user automatically gains limited access to the workspace (implicit membership)
  * They can see the workspace in their dashboard and access the shared resource
  * However, they don't appear in the standard members list for the workspace
* If a user with shared resources is later added as a full member of a workspace and then removed, they will lose access to all resources, including those explicitly shared with them

## Organization-Level Roles

At the organization level, ZenML Pro provides the following predefined roles:

1. **Organization Admin**
   * Full permissions to any organization resource
   * Can manage all aspects of the organization
   * Can create and manage workspaces
   * Can manage billing and team members
   * Can see and access all workspaces and projects
2. **Organization Manager**
   * Permissions to create and view resources in the organization
   * Can manage most organization settings
   * Cannot access billing information
   * Does not automatically get access to all workspaces (needs explicit workspace role assignment)
3. **Organization Viewer**
   * Permissions to view resources in the organization
   * Can connect to a workspace and view default stack and components.
   * Read-only access to organization resources
   * Can see all workspaces in the organization, but cannot access their contents without explicit roles
4. **Billing Admin**
   * Permissions to manage the organization's billing information
   * Can view and modify billing settings
   * Does not automatically get access to workspaces
5. **Organization Member**
   * Minimal permissions in the organization
   * Basic access to organization resources
   * Can only see workspaces they've been explicitly granted access to
   * Recommended role for users who should only have access to specific workspaces

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

![Screenshot showing the invite modal](.gitbook/assets/add_org_members.png)
{% endstep %}
{% endstepper %}

Some points to note:

* In addition to adding organization roles, you might also want to add workspace or project roles for people who you want to have access to specific resources.
* However, organization viewers and members cannot add themselves to existing workspaces that they are not a part of.
* Currently, you cannot create custom organization roles.

### Organization Role Inheritance

Understanding how roles inherit access across organization, workspace, and project levels is important for proper permission management:

* **Organization Admin**: Automatically has admin-level access to all workspaces and projects
* **Organization Viewer**: Can see all workspaces in the organization list but cannot access their contents without explicit roles. They can also connect to the workspace, which means they can also view things like the default stacks and components.
* **Organization Member**: Can only see workspaces they've been explicitly granted access to
* **Organization Manager/Billing Admin**: Do not automatically get access to workspaces

If you want to limit users to seeing only specific workspaces, assign them the "Organization Member" role and then explicitly grant them access to only the workspaces they need.

## Workspace-Level Roles

Workspace roles determine a user's permissions within a specific ZenML workspace. The following predefined roles are available:

1. **Workspace Admin**
   * Full permissions to any workspace resource
   * Can manage workspace settings and members
   * Can create and manage projects
   * Has complete control over all workspace resources
   * Has full CRUDS (Create, Read, Update, Delete, Share) permissions on all stacks in the workspace
2. **Workspace Developer**
   * Permissions to create and view resources in the workspace and all projects
   * Can work with pipelines, artifacts, and models
   * Cannot modify workspace settings
   * Can create new stacks and has full CRUDS permissions on their own stacks
   * Has Read and Update permissions for all other stacks in the workspace
   * Has access to all projects in the workspace
3. **Workspace Contributor**
   * Permissions to create resources in the workspace, but not access or create projects
   * Can add new resources to the workspace
   * Limited access to project resources
   * Can create new stacks and has full CRUDS permissions on their own stacks
   * Has no permissions on stacks created by others (cannot see them)
   * Does not have access to projects unless explicitly granted
4. **Workspace Viewer**
   * Permissions to view resources in the workspace and all projects
   * Read-only access to workspace resources
   * Can only view/read stacks in the workspace
   * Has read-only access to all projects in the workspace (due to backward compatibility)
5. **Stack Admin**
   * Permissions to manage stacks, components and service connectors
   * Specialized role for infrastructure management
   * Has full CRUDS permissions on ALL stacks in the workspace
   * Does not inherently grant access to projects

### Workspace Role Inheritance

Understanding how workspace roles affect access to projects and stacks is important for proper permission configuration:

* **Workspace Admin**: Has full access to all projects and stacks in the workspace
* **Workspace Developer**: Has access to all projects in the workspace but limited permissions on stacks created by others
* **Workspace Viewer**: Has read-only access to all projects in the workspace (for backward compatibility) but can only view stacks
* **Workspace Contributor**: Can only work with stacks they create and has no inherent access to projects
* **Stack Admin**: Has full access to all stacks but no inherent access to projects

If you want to give users access to specific stacks but not projects, consider using the Workspace Contributor or Stack Admin roles. If you want users to have access to projects, use Workspace Developer or Workspace Viewer roles, or assign project-specific roles.

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

Note that project-level roles do not grant any permissions to stacks, as stacks are managed at the workspace level.

## Custom Roles

ZenML Pro allows you to create custom roles with fine-grained permissions to meet your specific team requirements:

* **Organization Level**: Currently, you cannot create custom organization roles via the ZenML Pro dashboard. However, this is possible via the [ZenML Pro API](https://cloudapi.zenml.io/).
* **Workspace Level**: You can create custom workspace roles via the Workspace Settings page. This allows you to define specific combinations of permissions tailored to your team's workflow.
* **Project Level**: Custom project roles can be created through the Project Settings page, enabling precise control over project-specific permissions.

### When to Use Custom Roles

Custom roles are particularly useful in the following scenarios:

* When predefined roles are either too permissive or too restrictive for your use case
* When you need to separate responsibilities more precisely within your team
* For implementing principle of least privilege by granting only the exact permissions needed
* When you have specialized team members who need access to specific resources without full admin privileges
* For creating role-based workflows that match your organization's processes

For example, you might create a custom "Pipeline Operator" role that can run and monitor pipelines but cannot create or modify them, or a "Model Reviewer" role that can access model artifacts and evaluation results but cannot modify pipeline configurations.

## Team-Based Role Assignments

In addition to assigning roles to individual users, ZenML Pro allows you to assign roles to [teams](teams.md). A team is a collection of users that acts as a single entity, making permission management more efficient.

### How Team Roles Work

When you assign a role to a team:

* All members of that team inherit the permissions associated with that role
* Changes to team membership automatically update permissions for all affected users
* Users can have different permissions from multiple teams they belong to
* Team roles can be assigned at all levels: organization, workspace, and project
* Individual user roles and team roles are cumulative - users get the highest permission level from either source

For more information on creating and managing teams, see the [Teams](teams.md) documentation.

## Best Practices

1. **Least Privilege**: Assign the minimum necessary permissions to each role.
2. **Regular Audits**: Periodically review and update role assignments and permissions.
3. **Role Hierarchy**: Consider the relationship between organization, workspace, and project roles when assigning permissions.
4. **Team-Based Access**: Use teams to manage access control more efficiently across all levels.
5. **Documentation**: Maintain clear documentation about role assignments and their purposes.
6. **Regular Reviews**: Periodically audit role assignments to ensure they align with current needs.
7. **Organization Member Role**: Use the Organization Member role for users who should only see specific workspaces.

By leveraging ZenML Pro's comprehensive role-based access control, you can ensure that your team members have the right level of access to resources while maintaining security and enabling collaboration across your MLOps projects.
