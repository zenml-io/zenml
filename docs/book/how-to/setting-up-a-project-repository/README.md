---
description: Setting your team up for success with a well-architected ZenML project.
---

# 😸 Setting up a Well-Architected ZenML Project

Welcome to the guide on setting up a well-architected ZenML project. This section will provide you with a comprehensive overview of best practices, strategies, and considerations for structuring your ZenML projects to ensure scalability, maintainability, and collaboration within your team.

## The Importance of a Well-Architected Project

A well-architected ZenML project is crucial for the success of your machine learning operations (MLOps). It provides a solid foundation for your team to develop, deploy, and maintain ML models efficiently. By following best practices and leveraging ZenML's features, you can create a robust and flexible MLOps pipeline that scales with your needs.

## Key Components of a Well-Architected ZenML Project

### Repository Structure

A clean and organized repository structure is essential for any ZenML project. This includes:

- Proper folder organization for pipelines, steps, and configurations
- Clear separation of concerns between different components
- Consistent naming conventions

Learn more about setting up your repository in the [Set up repository guide](./best-practices.md).

### Version Control and Collaboration

Integrating your ZenML project with version control systems like Git is crucial for team collaboration and code management. This allows for:

- Makes creating pipeline builds faster, as you can leverage the same image and [have ZenML download code from your repository](../../how-to/customize-docker-builds/how-to-reuse-builds.md#use-code-repositories-to-speed-up-docker-build-times).
- Easy tracking of changes
- Collaboration among team members

Discover how to connect your Git repository in the [Set up a repository guide](./best-practices.md).

### Stacks, Pipelines, Models, and Artifacts

Understanding the relationship between stacks, models, and pipelines is key to designing an efficient ZenML project:
- Stacks: Define your infrastructure and tool configurations
- Models: Represent your machine learning models and their metadata
- Pipelines: Encapsulate your ML workflows
- Artifacts: Track your data and model outputs
Learn about organizing these components in the [Organizing Stacks, Pipelines, Models, and Artifacts guide](./stacks-pipelines-models.md).

### Access Management and Roles

Proper access management ensures that team members have the right permissions and responsibilities:

- Define roles such as data scientists, MLOps engineers, and infrastructure managers
- Set up service connectors and manage authorizations
- Establish processes for pipeline maintenance and server upgrades
- Leverage [Teams in ZenML Pro](../../getting-started/zenml-pro/teams.md) to assign roles and permissions to a group of users, to mimic your real-world team roles.

Explore access management strategies in the [Access Management and Roles guide](./access-management-and-roles.md).

### Shared Components and Libraries

Leverage shared components and libraries to promote code reuse and standardization across your team:

- Custom flavors, steps, and materializers
- Shared private wheels for internal distribution
- Handling authentication for specific libraries

Find out more about sharing code in the [Shared Libraries and Logic for Teams guide](./shared_components_for_teams.md).

### Project Templates

Utilize project templates to kickstart your ZenML projects and ensure consistency:

- Use pre-made templates for common use cases
- Create custom templates tailored to your team's needs

Learn about using and creating project templates in the [Project Templates guide](./project-templates.md).

### Migration and Maintenance

As your project evolves, you may need to migrate existing codebases or upgrade your ZenML server:

- Strategies for migrating legacy code to newer ZenML versions
- Best practices for upgrading ZenML servers

Discover migration strategies and maintenance best practices in the [Migration and Maintenance guide](../../how-to/manage-the-zenml-server/best-practices-upgrading-zenml.md#upgrading-your-code).

## Getting Started

To begin building your well-architected ZenML project, start by exploring the guides in this section. Each guide provides in-depth information on specific aspects of project setup and management.

Remember, a well-architected project is an ongoing process. Regularly review and refine your project structure, processes, and practices to ensure they continue to meet your team's evolving needs.

By following these guidelines and leveraging ZenML's powerful features, you'll be well on your way to creating a robust, scalable, and collaborative MLOps environment.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
