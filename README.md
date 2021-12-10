<div align="center">
    <img src="https://zenml.io/assets/social/github.svg">
</div>

# 👀 What is ZenML?

**ZenML** is an extensible, open-source MLOps framework to create production-ready machine learning pipelines. Built for data scientists, it has a simple, flexible syntax, is cloud- and tool-agnostic, and has interfaces/abstractions that are catered towards ML workflows.

At its core, **ZenML pipelines execute ML-specific workflows** from sourcing data to splitting, preprocessing, training, all the way to the evaluation of results and even serving. There are many built-in batteries to support common ML development tasks. ZenML is not here to replace the great tools that solve these individual problems. Rather, it **integrates natively with popular ML tooling** and gives standard abstraction to write your workflows.

🎉 **Version 0.5.4 out now!** [Check out the release notes here](https://blog.zenml.io/zero-five-four-release/).

[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/zenml)](https://pypi.org/project/zenml/)
[![PyPI Status](https://pepy.tech/badge/zenml)](https://pepy.tech/project/zenml)
![GitHub](https://img.shields.io/github/license/zenml-io/zenml)
[![Codecov](https://codecov.io/gh/zenml-io/zenml/branch/main/graph/badge.svg)](https://codecov.io/gh/zenml-io/zenml)
[![Interrogate](docs/interrogate.svg)](https://interrogate.readthedocs.io/en/latest/)
![Main Workflow Tests](https://github.com/zenml-io/zenml/actions/workflows/main.yml/badge.svg)

<div align="center">
Join our <a href="https://zenml.io/slack-invite" target="_blank">
    <img width="25" src="https://cdn3.iconfinder.com/data/icons/logos-and-brands-adobe/512/306_Slack-512.png" alt="Slack"/>
<b>Slack Community</b> </a> and become part of the ZenML family
</div>
<div align="center"> Give us a 
    <img width="25" src="https://cdn.iconscout.com/icon/free/png-256/github-153-675523.png" alt="Slack"/>
<b>GitHub star</b> to show your love
</div>
<div align="center"> 
    <b>NEW: </b> <a href="https://zenml.io/discussion" target="_blank"><img width="25" src="https://cdn1.iconfinder.com/data/icons/social-17/48/like-512.png" alt="Vote"/><b> Vote</b></a> on the next ZenML features 
</div>

<br>

![Before and after ZenML](docs/readme/sam-side-by-side-full-text.png)

# 🤖 Why use ZenML?

We built ZenML because we could not find an easy framework that translates the patterns observed in the research phase with Jupyter notebooks into a production-ready ML environment. ZenML follows the paradigm of [`Pipelines As Experiments` (PaE)](https://docs.zenml.io/why-zenml), meaning ZenML pipelines are designed to be written early on the development lifecycle, where data scientists can explore their pipelines as they develop towards production.

By using ZenML in the early stages of your project, you get the following features:

- **Reproducibility** of training and inference workflows.
- Managing ML **metadata**, including versioning data, code, and models.
- Getting an **overview** of your ML development, with a reliable link between training and deployment.
- Maintaining **comparability** between ML models.
- **Scaling** ML training/inference to large datasets.
- Retaining code **quality** alongside development velocity.
- **Reusing** code/data and reducing waste.
- Keeping up with the **ML tooling landscape** with standard abstractions and interfaces.

# 📖 Learn More

| ZenML Resources |   |
| ------------- | - |
| 🧘‍♀️ **[ZenML 101]** | New to ZenML? Here's everything you need to know! |
| ⚛️ **[Core Concepts]** | Some key terms and concepts we use. |
| 🗃 **[Low Level API Guide]** | Build production ML pipelines from the simple step interface. |
| 🚀 **[New in v0.5.4]** | New features, bug fixes. |
| 🗳 **[Vote for Features]** | Pick what we work on next! |
| 📓 **[Docs]** | Full documentation for creating your own ZenML pipelines. |
| 📒 **[API Reference]** | The detailed reference for ZenML's API. |
| ⚽️ **[Examples]** | Learn best through examples where ZenML is used? We've got you covered. |
| 📬 **[Blog]** | Use cases of ZenML and technical deep dives on how we built it. |
| 🔈 **[Podcast]** | Conversations with leaders in ML, released every 2 weeks. |
| 📣 **[Newsletter]** | We build ZenML in public. Subscribe to learn how we work. |
| 💬 **[Join Slack]** | Need help with your specific use case? Say hi on Slack! |
| 🗺 **[Roadmap]** | See where ZenML is working to build new features. |
| 🙋‍♀️ **[Contribute]** | How to contribute to the ZenML project and code base. |

[ZenML 101]: https://docs.zenml.io/
[Core Concepts]: https://docs.zenml.io/core-concepts
[Low Level API Guide]: https://docs.zenml.io/guides/low-level-api
[New in v0.5.4]: https://blog.zenml.io/zero-five-four-release/
[Vote for Features]: https://zenml.io/discussion
[Docs]: https://docs.zenml.io/
[API Reference]: https://apidocs.zenml.io/
[Examples]: https://github.com/zenml-io/zenml/tree/main/examples
[Blog]: https://blog.zenml.io/
[Podcast]: https://podcast.zenml.io/
[Newsletter]: https://zenml.io/newsletter/
[Join Slack]: https://zenml.io/slack-invite/
[Roadmap]: https://zenml.io/roadmap
[Contribute]: https://github.com/zenml-io/zenml/blob/main/CONTRIBUTING.md

# 🎮 Features

### 1. 🗃 Use Caching across (Pipelines As) Experiments

ZenML makes sure for every pipeline you can trust that:

- Code is versioned
- Data is versioned
- Models are versioned
- Configurations are versioned

You can utilize caching to help iterate quickly through ML experiments. (Read [our blogpost](https://blog.zenml.io/caching-ml-pipelines/) to learn more!)

### 2. ♻️ Leverage Powerful Integrations

Once code is organized into a ZenML pipeline, you can supercharge your ML development with powerful integrations on multiple [MLOps stacks](https://docs.zenml.io/core-concepts).

We currently support [Airflow](https://airflow.apache.org/) and [Kubeflow](https://www.kubeflow.org/) as third-party orchestrators for your ML pipeline code. ZenML steps can be built from any of the other tools you usually use in your ML workflows, from [`scikit-learn`](https://scikit-learn.org/stable/) to [`PyTorch`](https://pytorch.org/) or [`TensorFlow`](https://www.tensorflow.org/).

### 3. ☁️ Distribute Processing to the Cloud

Switching from local experiments to cloud-based pipelines doesn't need to be complex. ZenML supports running pipelines on Kubernetes clusters in the cloud through our [Kubeflow](https://www.kubeflow.org/) integration. Switching from your local stack to a cloud stack is easy to do with our CLI tool.

### 4. 🧩 Visualize the Steps of your Pipeline

It’s not uncommon for pipelines to be made up of many steps, and those steps can interact and intersect with one another in often complex patterns. We’ve built a way for you to inspect what’s going on with your ZenML pipeline:

![Here's what the pipeline lineage tracking visualizer looks like](https://blog.zenml.io/assets/posts/release_0_5_4/zenml_lineage.gif)

### 5. 📊 Visualize Statistics

Now you can use awesome third-party libraries to visualize ZenML steps and artifacts. We support the facets visualization for statistics out of the box, to find data drift between your training and test sets.

We use the built-in FacetStatisticsVisualizer using the [Facets Overview](https://pypi.org/project/facets-overview/) integration.

![Here’s what the statistics visualizer looks like](https://blog.zenml.io/assets/posts/release_0_5_3/stats.gif)

### 6. 🧐 Introspect your Pipeline Results

Once you've run your experiment, you need a way of seeing what was produced and how it was produced. We offer a flexible interface to support [post-execution workflows](https://docs.zenml.io/guides/post-execution-workflow). This allows you to access any of the artifacts produced by pipeline steps as well as any associated metadata.

### 7. 🛠 Configure Pipeline Runs with YAML Code

Not everyone wants to keep their configuration of pipeline runs in the same place as the active code defining steps. You can define the particular customization of runs with YAML code if that's your jam!

# 🤸 Getting Started

## 💾 Install ZenML

*Requirements*: ZenML supports Python 3.6, 3.7 and 3.8.

ZenML is available for easy installation into your environment via PyPI:

```bash
pip install zenml
```

Alternatively, if you’re feeling brave, feel free to install the bleeding edge:
**NOTE:** Do so on your own risk, no guarantees given!

```bash
pip install git+https://github.com/zenml-io/zenml.git@main --upgrade
```

## 🚅 Quickstart

The quickest way to get started is to create a simple pipeline.

#### Step 1: Initialize a ZenML repo from within a git repo

```bash
git init
zenml init
```

#### Step 2: Assemble, run, and evaluate your pipeline locally

```python
import numpy as np
import tensorflow as tf

from zenml.pipelines import pipeline
from zenml.steps import step
from zenml.steps.step_output import Output


@step
def importer() -> Output(
    X_train=np.ndarray, y_train=np.ndarray, X_test=np.ndarray, y_test=np.ndarray
):
    """Download the MNIST data store it as numpy arrays."""
    (X_train, y_train), (X_test, y_test) = tf.keras.datasets.mnist.load_data()
    return X_train, y_train, X_test, y_test


@step
def trainer(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> tf.keras.Model:
    """A simple Keras Model to train on the data."""
    model = tf.keras.Sequential()
    model.add(tf.keras.layers.Flatten(input_shape=(28, 28)))
    model.add(tf.keras.layers.Dense(10))

    model.compile(
        optimizer=tf.keras.optimizers.Adam(0.001),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=["accuracy"],
    )

    model.fit(X_train, y_train)

    # write model
    return model


@step
def evaluator(
    X_test: np.ndarray,
    y_test: np.ndarray,
    model: tf.keras.Model,
) -> float:
    """Calculate the accuracy on the test set"""
    test_acc = model.evaluate(X_test, y_test, verbose=2)
    return test_acc


@pipeline
def mnist_pipeline(
    importer,
    trainer,
    evaluator,
):
    """Links all the steps together in a pipeline"""
    X_train, y_train, X_test, y_test = importer()
    model = trainer(X_train=X_train, y_train=y_train)
    evaluator(X_test=X_test, y_test=y_test, model=model)

pipeline = mnist_pipeline(
    importer=importer(),
    trainer=trainer(),
    evaluator=evaluator(),
)
pipeline.run()
```

# 🗺 Roadmap

ZenML is being built in public. The [roadmap](https://zenml.io/roadmap) is a regularly updated source of truth for the ZenML community to understand where the product is going in the short, medium, and long term.

ZenML is managed by a [core team](https://zenml.io/team) of developers that are responsible for making key decisions and incorporating feedback from the community. The team oversees feedback via various channels, and you can directly influence the roadmap as follows:

- Vote on your most wanted feature on our [Discussion board](https://zenml.io/discussion).
- Create a [Feature Request](https://github.com/zenml-io/zenml/issues/new/choose) in the [GitHub board](https://github.com/zenml-io/zenml/issues).
- Start a thread in our [Slack channel](https://zenml.io/slack-invite).

## 🚧 What we're working on

We recently rewrote the entire code base, and are now incrementally adding back in some of the features we previously supported. Get a full overview of what's coming by checking out the Roadmap, but in the short term we're currently working hard to support:

- Standard interfaces aka our higher-level API.
- Individual step interfaces like `PreprocessorStep`, `TrainerStep`, `DeployerStep` etc. need to be rewritten from within the new paradigm.
- A proper production setup with Kubeflow running in the cloud.
- A simple way to switch between your local environment and the cloud.

# ❓ FAQ

**Q: Why did you build ZenML?**

We built it because we scratched our own itch while deploying multiple ML models in production for the last 4 years. Our team struggled to find a simple yet production-ready solution whilst developing large-scale ML pipelines, and built a solution for it that we are now proud to share with all of you!

**Q: Can I integrate my own, custom processing backend?**

Absolutely. We have a clever design for [our integration interfaces](https://github.com/zenml-io/zenml/tree/main/src/zenml/integrations), so you can simply add your own!

**Q: I would like a more convenient way to collaborate with my team!**

Fear not, we’re building a [ZenML Cloud](https://zenml.io/cloud/) offering. Workloads will still be running under your control, and we don’t get access to your actual data, but we’ll be your centralized pipeline registry and metadata store. And we’ll throw in a nice UI, too. Sign up for [our newsletter](https://zenml.io/newsletter/) to stay in the loop!

**Q: I would like to contribute to the repo.**

Great to hear! Please check out [our contribution guidelines](https://github.com/zenml-io/zenml/blob/main/CONTRIBUTING.md), or simply hop on over to our Slack and chat us up :).

**Q: My question is not answered yet!**

Then connect with us using Slack - simply [join us via this invite](https://zenml.io/slack-invite/).

# 🙋‍♀️ Contributing & Community

We would love to develop ZenML together with our community! Check our [Contributing Guide](CONTRIBUTING.md) for more details on how best to contribute.

<br>

![Repobeats analytics image](https://repobeats.axiom.co/api/embed/635c57b743efe649cadceba6a2e6a956663f96dd.svg "Repobeats analytics image")

# 🆘 Where to get help

First point of call should be [our Slack group](https://zenml.io/slack-invite/). Ask your questions about bugs or specific use cases and someone from the core team will respond.

# 📜 License

ZenML is distributed under the terms of the Apache License Version 2.0. A complete version of the license is available in the [LICENSE.md](LICENSE.md) in this repository. Any contribution made to this project will be licensed under the Apache License Version 2.0.

# 🙏🏻 Acknowledgements

ZenML is built on the shoulders of giants: we leverage, and would like to give credit to, existing open-source libraries like [`tfx`](https://github.com/tensorflow/tfx/). The goal of our framework is neither to replace these libraries, nor to diminish their usage. ZenML is simply an opinionated, higher-level interface with the focus being purely on ease-of-use and coherent intuitive design. You can read more about why we actually started building ZenML on our [blog](https://blog.zenml.io/why-zenml/).