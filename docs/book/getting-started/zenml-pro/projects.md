---
description: Learn how to use projects in ZenML Pro.
---

# Projects

Projects in ZenML Pro provide a logical subdivision within workspaces, allowing you to organize and manage your MLOps resources more effectively. Each project acts as an isolated environment within a workspace, with its own set of pipelines, artifacts, models, and access controls.

## Understanding Projects

Projects help you organize your ML work and resources. You can use projects to separate different initiatives, teams, or experiments while sharing common resources across your workspace.

Projects offer several key benefits:

1. **Resource Isolation**: Keep pipelines, artifacts, and models organized and separated by project
2. **Granular Access Control**: Define specific roles and permissions at the project level
3. **Team Organization**: Align projects with specific teams or initiatives within your organization
4. **Resource Management**: Track and manage resources specific to each project independently

## Using Projects with the CLI

Before you can work with projects, you need to be logged into your workspace. If you haven't done this yet, see the [Workspaces](workspaces.md#using-the-cli) documentation for instructions on logging in.

### Setting an active project

After initializing your ZenML repository (`zenml init`), you should set an active project. This is similar to how you set an active stack:

```bash
zenml project set default
```

This command sets the "default" project as your active project. All subsequent ZenML operations will be executed in the context of this project.

{% hint style="warning" %}
Best practice is to set your active project right after running `zenml init`, just like you would set an active stack. This ensures all your resources are properly organized within the project.
{% endhint %}

## Creating and Managing Projects

To create a new project:

{% stepper %}
{% step %}
### Navigate to Projects

From your workspace dashboard, click on the **Projects** tab.

{% endstep %}

{% step %}
### Click "Add a New Project"

In the project creation form, you'll need to provide:

* **Project Name**: A descriptive name for your project
* **Project ID**: A unique identifier that enables you to access your project through both the API and CLI. Use only letters, numbers, and hyphens or underscores (no spaces).
* **Description** (optional): A brief explanation of what your project is about

{% endstep %}

{% step %}
### Configure Project Settings

After creating the project, you can configure additional settings such as:
* Adding team members and assigning roles
* Setting up project-specific configurations
* Configuring integrations
{% endstep %}
{% endstepper %}

## Project-Level Roles

Projects have their own role-based access control (RBAC) system, scoped to the project level. The default project roles include:

1. **Project Admin**
   * Full permissions to any project resource
   * Can manage project members and their roles
   * Can configure project settings
   * Has complete control over all project resources

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
   * Read-only access to all project resources
   * Cannot create or modify any resources

## Managing Project Resources

Projects provide isolation for various MLOps resources:

### Pipelines
* Pipelines created within a project are only visible to project members
* Pipeline runs and their artifacts are scoped to the project
* Pipeline configurations and templates are project-specific

### Artifacts and Models
* Artifacts and models are isolated within their respective projects
* Version control and lineage tracking is project-specific
* Sharing artifacts between projects requires explicit permissions

## Best Practices

1. **Project Structure**
   * Create projects based on logical boundaries (e.g., use cases, teams, or products)
   * Use clear naming conventions for projects
   * Document project purposes and ownership

2. **Access Control**
   * Start with default roles before creating custom ones
   * Regularly audit project access and permissions
   * Use teams for easier member management

3. **Resource Management**
   * Monitor resource usage within projects
   * Set up appropriate quotas and limits
   * Clean up unused resources regularly

4. **Documentation**
   * Maintain project-specific documentation
   * Document custom roles and their purposes
   * Keep track of project dependencies and integrations

## Project Hierarchy

Projects exist within the following hierarchy in ZenML Pro:

1. Organization (top level)
2. Workspaces (contain multiple projects)
3. Projects (contain resources)
4. Resources (pipelines, artifacts, models, etc.)

This hierarchy ensures clear organization and access control at each level while maintaining flexibility in resource management.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>