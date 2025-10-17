---
icon: code
description: Setting your team up for success with a well-architected ZenML project.
---

# Setting up a Well-Architected ZenML Project

Welcome to the guide on setting up a well-architected ZenML project. This section will provide you with a comprehensive overview of best practices, strategies, and considerations for structuring your ZenML projects to ensure scalability, maintainability, and collaboration within your team.

## The Importance of a Well-Architected Project

A well-architected ZenML project is crucial for the success of your machine learning operations (MLOps). It provides a solid foundation for your team to develop, deploy, and maintain ML models efficiently. By following best practices and leveraging ZenML's features, you can create a robust and flexible MLOps pipeline that scales with your needs.

## Key Components of a Well-Architected ZenML Project

### Repository Structure

A clean and organized repository structure is essential for any ZenML project. This includes:

- Proper folder organization for pipelines, steps, and configurations
- Clear separation of concerns between different components
- Consistent naming conventions

Learn more about setting up your repository in the [Set up repository guide](https://docs.zenml.io/user-guides/production-guide/connect-code-repository).

### Version Control and Collaboration

Integrating your ZenML project with version control systems like Git is crucial for team collaboration and code management. This allows for:

- Makes creating pipeline builds faster, as you can leverage the same image and [have ZenML download code from your repository](https://docs.zenml.io/how-to/customize-docker-builds/how-to-reuse-builds#use-code-repositories-to-speed-up-docker-build-times).
- Easy tracking of changes
- Collaboration among team members

Discover how to connect your Git repository in the [Set up a repository guide](https://docs.zenml.io/user-guides/production-guide/connect-code-repository).

### Stacks, Pipelines, Models, and Artifacts

Understanding the relationship between stacks, models, and pipelines is key to designing an efficient ZenML project:

- Stacks: Define your infrastructure and tool configurations
- Models: Represent your machine learning models and their metadata
- Pipelines: Encapsulate your ML workflows
- Artifacts: Track your data and model outputs

Learn about organizing these components in the [Organizing Stacks, Pipelines, Models, and Artifacts guide](https://docs.zenml.io/user-guides/best-practices/organizing-pipelines-and-models).

### Access Management and Roles

Proper access management ensures that team members have the right permissions and responsibilities:

- Define roles such as data scientists, MLOps engineers, and infrastructure managers
- Set up [service connectors](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management) and manage authorizations
- Establish processes for pipeline maintenance and server upgrades
- Leverage [Teams in ZenML Pro](https://docs.zenml.io/pro/core-concepts/teams) to assign roles and permissions to a group of users, to mimic your real-world team roles.

Explore access management strategies in the [Access Management and Roles guide](https://docs.zenml.io/pro/core-concepts/roles).

### Shared Components and Libraries

Leverage shared components and libraries to promote code reuse and standardization across your team:

- Custom flavors, steps, and materializers
- Shared private wheels for internal distribution
- Handling authentication for specific libraries

Find out more about sharing code in the [Shared Libraries and Logic for Teams guide](https://docs.zenml.io/user-guides/best-practices/shared-components-for-teams).

### Project Templates

Utilize project templates to kickstart your ZenML projects and ensure consistency:

- Use pre-made templates for common use cases
- Create custom templates tailored to your team's needs

Learn about using and creating project templates in the [Project Templates guide](../../how-to/templates/templates.md).

### Migration and Maintenance

As your project evolves, you may need to migrate existing codebases or upgrade your ZenML server:

- Strategies for migrating legacy code to newer ZenML versions
- Best practices for upgrading ZenML servers

Discover migration strategies and maintenance best practices in the [Migration and Maintenance guide](https://docs.zenml.io/how-to/manage-zenml-server/best-practices-upgrading-zenml#upgrading-your-code).

## Set up your repository

While it doesn't matter how you structure your ZenML project, here is a recommended project structure the core team often uses:

```markdown
.
├── .dockerignore
├── Dockerfile
├── steps
│   ├── loader_step
│   │   ├── .dockerignore (optional)
│   │   ├── Dockerfile (optional)
│   │   ├── loader_step.py
│   │   └── requirements.txt (optional)
│   └── training_step
│       └── ...
├── pipelines
│   ├── training_pipeline
│   │   ├── .dockerignore (optional)
│   │   ├── config.yaml (optional)
│   │   ├── Dockerfile (optional)
│   │   ├── training_pipeline.py
│   │   └── requirements.txt (optional)
│   └── deployment_pipeline
│       └── ...
├── notebooks
│   └── *.ipynb
├── requirements.txt
├── .zen
└── run.py
```

All ZenML [Project templates](https://docs.zenml.io/user-guides/best-practices/project-templates) are modeled around this basic structure. The `steps` and `pipelines` folders contain the steps and pipelines defined in your project. If your project is simpler you can also just keep your steps at the top level of the `steps` folder without the need so structure them in subfolders.

{% hint style="info" %}
It might also make sense to register your repository as a code repository. These enable ZenML to keep track of the code version that you use for your pipeline runs. Additionally, running a pipeline that is tracked in [a registered code repository](https://docs.zenml.io/user-guides/production-guide/connect-code-repository) can speed up the Docker image building for containerized stack components by eliminating the need to rebuild Docker images each time you change one of your source code files. Learn more about these in [connecting your Git repository](https://docs.zenml.io/concepts/code-repositories).
{% endhint %}

#### Steps

Keep your steps in separate Python files. This allows you to optionally keep their utils, dependencies, and Dockerfiles separate.

#### Logging

ZenML records the root python logging handler's output into the artifact store as a side-effect of running a step. Therefore, when writing steps, use the `logging` module to record logs, to ensure that these logs then show up in the ZenML dashboard.

```python
# Use ZenML handler
from zenml.logger import get_logger

logger = get_logger(__name__)
...

@step
def training_data_loader():
    # This will show up in the dashboard
    logger.info("My logs")
```

#### Pipelines

Just like steps, keep your pipelines in separate Python files. This allows you to optionally keep their utils, dependencies, and Dockerfiles separate.

It is recommended that you separate the pipeline execution from the pipeline definition so that importing the pipeline does not immediately run it.

{% hint style="warning" %}
Do not give pipelines or pipeline instances the name "pipeline". Doing this will overwrite the imported `pipeline` and decorator and lead to failures at later stages if more pipelines are decorated there.
{% endhint %}

{% hint style="info" %}
Pipeline names are their unique identifiers, so using the same name for different pipelines will create a mixed history where two runs of a pipeline are two very different entities.
{% endhint %}

#### .dockerignore

Containerized orchestrators and step operators load your complete project files into a Docker image for execution. To speed up the process and reduce Docker image sizes, exclude all unnecessary files (like data, virtual environments, git repos, etc.) within the `.dockerignore`.

#### Dockerfile (optional)

By default, ZenML uses the official [zenml Docker image](https://hub.docker.com/r/zenmldocker/zenml) as a base for all pipeline and step builds. You can use your own `Dockerfile` to overwrite this behavior. Learn more [here](https://docs.zenml.io//how-to/customize-docker-builds).

#### Notebooks

Collect all your notebooks in one place.

#### .zen

By running `zenml init` at the root of your project, you define the [source root](https://docs.zenml.io/concepts/steps_and_pipelines/sources#source-root) for your project.
- When running Jupyter notebooks, it is required that you have a `.zen` directory initialized in one of the parent directories of your notebook.
- When running regular Python scripts, it is still **highly** recommended that you have a `.zen` directory initialized in the root of your project. If that is not the case, ZenML will look for a `.zen` directory in the parent directories, which might cause issues if one is found (The import paths will not be relative to the source root anymore for example). If no `.zen` directory is found, the parent directory of the Python file that you're executing will be used as the implicit source root.

{% hint style="warning" %}
All of your import paths should be relative to the source root.
{% endhint %}

#### run.py

Putting your pipeline runners in the root of the repository ensures that all imports that are defined relative to the project root resolve for the pipeline runner. In case there is no `.zen` defined this also defines the implicit source's root.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
