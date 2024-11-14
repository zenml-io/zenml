---
description: Recommended repository structure and best practices.
---

# Set up your repository

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

All ZenML [Project
templates](using-project-templates.md#generating-project-from-a-project-template)
are modeled around this basic structure. The `steps` and `pipelines` folders
contain the steps and pipelines defined in your project. If your project is
simpler you can also just keep your steps at the top level of the `steps` folder
without the need so structure them in subfolders.

{% hint style="info" %}
It might also make sense to register your repository as a code repository. These
enable ZenML to keep track of the code version that you use for your pipeline
runs. Additionally, running a pipeline that is tracked in [a registered code repository](./connect-your-git-repository.md) can speed up the Docker image building for containerized stack
components by eliminating the need to rebuild Docker images each time you change
one of your source code files. Learn more about these in [connecting your Git repository](https://docs.zenml.io/how-to/setting-up-a-project-repository/connect-your-git-repository).
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

By default, ZenML uses the official [zenml Docker image](https://hub.docker.com/r/zenmldocker/zenml) as a base for all pipeline and step builds. You can use your own `Dockerfile` to overwrite this behavior. Learn more [here](../../infrastructure-deployment/customize-docker-builds/README.md).

#### Notebooks

Collect all your notebooks in one place.

#### .zen

By running `zenml init` at the root of your project, you define the project scope for ZenML. In ZenML terms, this will be called your "source's root". This will be used to resolve import paths and store configurations.

Although this is optional, it is recommended that you do this for all of your
projects. This is especially important if you are using Jupyter noteeboks in
your project as these require you to have initialized a `.zen` file.

{% hint style="warning" %}
All of your import paths should be relative to the source's root.
{% endhint %}

#### run.py

Putting your pipeline runners in the root of the repository ensures that all imports that are defined relative to the project root resolve for the pipeline runner. In case there is no `.zen` defined this also defines the implicit source's root.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
