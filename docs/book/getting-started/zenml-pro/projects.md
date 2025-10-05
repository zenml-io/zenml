---
description: Managing projects in ZenML
icon: clipboard-list
---

# Projects

Projects in ZenML Pro provide a logical subdivision within workspaces, allowing you to organize and manage your MLOps resources more effectively. Each project acts as an isolated environment within a workspace, with its own set of pipelines, artifacts, models, and access controls. This isolation is particularly valuable when working with both traditional ML models and AI agent systems, allowing teams to separate different types of experiments and workflows.

## Understanding Projects

Projects help you organize your ML work and resources. You can use projects to separate different initiatives, teams, or experiments while sharing common resources across your workspace. This includes separating traditional ML experiments from AI agent development work.

Projects offer several key benefits:

1. **Resource Isolation**: Keep pipelines, artifacts, and models organized and separated by project
2. **Granular Access Control**: Define specific roles and permissions at the project level
3. **Team Organization**: Align projects with specific teams or initiatives within your organization
4. **Resource Management**: Track and manage resources specific to each project independently
5. **Experiment Separation**: Isolate different types of AI development work (ML vs agents vs multi-modal systems)

## Using Projects with the CLI

Before you can work with projects, you need to be logged into your workspace. If you haven't done this yet, see the [Workspaces](workspaces.md#using-the-cli) documentation for instructions on logging in.

### Creating a project

To create a new project using the CLI, run the following command:

```bash
zenml project register <NAME>
```

### Setting an active project

After initializing your ZenML repository (`zenml init`), you should set an active project. This is similar to how you set an active stack:

```bash
zenml project set default
```

This command sets the "default" project as your active project. All subsequent ZenML operations will be executed in the context of this project.

{% hint style="warning" %}
Best practice is to set your active project right after running `zenml init`, just like you would set an active stack. This ensures all your resources are properly organized within the project.
{% endhint %}

You can also set the project to be used by your client via an environment variable:

```bash
export ZENML_ACTIVE_PROJECT_ID=<PROJECT_ID>
```

### Setting a default project

The default project is something that each user can configure. This project will be automatically set as the active project when you connect your local Python client to a ZenML Pro workspace.

You can set your default project either when creating a new project or when activating it:

```bash
# Set default project during registration
zenml project register <NAME> --set-default

# Set default project during activation
zenml project set <NAME> --default
```

## Creating and Managing Projects

To create a new project:

{% stepper %}
{% step %}
#### Navigate to Projects

From your workspace dashboard, click on the **Projects** tab.
{% endstep %}

{% step %}
#### Click "Add a New Project"

In the project creation form, you'll need to provide:

* **Project Name**: A descriptive name for your project
* **Project ID**: A unique identifier that enables you to access your project through both the API and CLI. Use only letters, numbers, and hyphens or underscores (no spaces).
* **Description** (optional): A brief explanation of what your project is about
{% endstep %}

{% step %}
#### Configure Project Settings

After creating the project, you can configure additional settings such as:

* Adding team members and assigning roles
* Setting up project-specific configurations
* Configuring integrations
{% endstep %}
{% endstepper %}

## Managing Project Resources

Projects provide isolation for various MLOps resources:

### Pipelines

* Pipelines created within a project are only visible to project members
* Pipeline runs and their artifacts are scoped to the project
* Pipeline configurations and snapshots are project-specific

### Artifacts and Models

* Artifacts and models are isolated within their respective projects
* Version control and lineage tracking is project-specific
* Sharing artifacts between projects requires explicit permissions

## Best Practices

1. **Project Structure**
   * Create projects based on logical boundaries (e.g., use cases, teams, or products)
   * Use clear naming conventions for projects
   * Document project purposes and ownership
   * Separate traditional ML and agent development where needed
2. **Access Control**
   * Start with default roles before creating custom ones
   * Regularly audit project access and permissions
   * Use teams for easier member management
   * Implement stricter controls for production agent systems
3. **Resource Management**
   * Monitor resource usage within projects
   * Set up appropriate quotas and limits
   * Clean up unused resources regularly
   * Track LLM API costs per project for agent development
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
