<div align="center">
    <img src="https://zenml.io/assets/social/github.svg">
</div>

# What is ZenML?

**ZenML** is an extensible, open-source MLOps framework to create production-ready machine learning pipelines. It has a simple, flexible syntax, is cloud and tool agnostic, and has interfaces/abstractions that are catered towards ML workflows.

At its core, ZenML pipelines execute ML-specific workflows from sourcing data to splitting, preprocessing, training, all the way to the evaluation of results and even serving. There are many built-in batteries as things progress in ML development. ZenML is not here to replace the great tools that solve these individual problems. Rather, it integrates natively with many popular ML tooling, and gives standard abstraction to write your workflows.

🎉 **Version 0.5.4 out now!** [Check out the release notes here](https://blog.zenml.io/zero-five-four-release/).

![Before and after ZenML](docs/readme/sam-side-by-side-full-text.png)

# Why use ZenML?

We built ZenML because we could not find an easy framework that translates the patterns observed in the research phase with Jupyter notebooks into a production-ready ML environment.
ZenML follows the paradigm of [`Pipelines As Experiments` (PaE)](https://docs.zenml.io/why-zenml), meaning ZenML pipelines are designed to be written early on the development lifecycle, where the users can explore their
pipelines as they develop towards production.

By using ZenML at the early stages of development, you get the following features:

- **Reproducibility** of training and inference workflows.
- Managing ML **metadata**, including versioning data, code, and models.
- Getting an **overview** of your ML development, with a reliable link between training and deployment.
- Maintaining **comparability** between ML models.
- **Scaling** ML training/inference to large datasets.
- Retaining code **quality** alongside development velocity.
- **Reusing** code/data and reducing waste.
- Keeping up with the **ML tooling landscape** with standard abstractions and interfaces.

[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/zenml)](https://pypi.org/project/zenml/)
[![PyPI Status](https://pepy.tech/badge/zenml)](https://pepy.tech/project/zenml)
![GitHub](https://img.shields.io/github/license/zenml-io/zenml)
[![Codecov](https://codecov.io/gh/zenml-io/zenml/branch/main/graph/badge.svg)](https://codecov.io/gh/zenml-io/zenml)
[![Interrogate](docs/interrogate.svg)](https://interrogate.readthedocs.io/en/latest/)
![Main Workflow Tests](https://github.com/zenml-io/zenml/actions/workflows/main.yml/badge.svg)

<div align="center">

<p align="center">
<a href="https://zenml.io">Website</a> •
<a href="https://docs.zenml.io">Docs</a> •
<a href="https://zenml.io/roadmap">Roadmap</a> •
<a href="https://zenml.io/discussion">Vote For Features</a> •
<a href="https://zenml.io/slack-invite/">Join Slack</a>
<a href="https://zenml.io/newsletter/">Newsletter</a>
</p>

</div>

<div align="center"> Join our
<a href="https://zenml.io/slack-invite" target="_blank">
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

# 📖 Learn More

| ZenML Resources |   |
| ------------- | - |
| 🧘‍♀️ **[ZenML 101]** | New to ZenML? Here's everything you need to know! |
| ⚛️ **[Core Concepts]** | Some key terms and concepts we use. |
| 🗃 **[Low Level API Guide]** | Build production ML pipelines from the simple step interface. |
| 🚀 **[New in v1.5.4]** | New features, bug fixes. |
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
[New in v1.5.4]: https://blog.zenml.io/zero-five-four-release/
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

- Integrate with your favourite tools (Airflow & Kubeflow)
- Use caching across pipelines
- Distribute processing to the cloud
- Introspect your pipeline results
- Visualize the steps of your pipeline
- Visualize statistics
- Configure pipeline runs with YAML code

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

ZenML is managed by a [core team](https://zenml.io/team) of developers that are responsible for making key decisions and incorporating feedback from the community. The team oversee's feedback via various channels, but you can directly influence the roadmap as follows:

- Vote on your most wanted feature on the [Discussion board](https://zenml.io/discussion).
- Create a [Feature Request](https://github.com/zenml-io/zenml/issues/new/choose) in the [GitHub board](https://github.com/zenml-io/zenml/issues).
- Start a thread in the [Slack channel](https://zenml.io/slack-invite).

## 🚧 What we're working on

The current release is bare bones (as it is a complete rewrite).
We are missing some basic features which used to be part of ZenML 0.3.8 (the previous release):

- Standard interfaces for `TrainingPipeline`.
- Individual step interfaces like `PreprocessorStep`, `TrainerStep`, `DeployerStep` etc. need to be rewritten from within the new paradigm. They should
  be included in the non-RC version of this release.
- A proper production setup with an orchestrator like Airflow.
- A post-execution workflow to analyze and inspect pipeline runs.
- The concept of `Backends` will evolve into a simple mechanism of transitioning individual steps into different runners.
- Support for `KubernetesOrchestrator`, `KubeflowOrchestrator`, `GCPOrchestrator` and `AWSOrchestrator` are also planned.
- Dependency management including Docker support is planned.

However, bare with us: Adding those features back in should be relatively faster as we now have a solid foundation to build on. Look out for the next email!

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

We would love to receive your contributions! Check our [Contributing Guide](CONTRIBUTING.md) for more details on how best to contribute.

<br>

![Repobeats analytics image](https://repobeats.axiom.co/api/embed/635c57b743efe649cadceba6a2e6a956663f96dd.svg "Repobeats analytics image")

# 🆘 Where to get help

# 📜 License

ZenML is distributed under the terms of the Apache License Version 2.0. A complete version of the license is available in the [LICENSE.md](LICENSE.md) in this repository. Any contribution made to this project will be licensed under the Apache License Version 2.0.

# 🙏🏻 Acknowledgements

ZenML is built on the shoulders of giants: we leverage, and would like to give credit to, existing open-source libraries like [`tfx`](https://github.com/tensorflow/tfx/). The goal of our framework is neither to replace these libraries, nor to diminish their usage. ZenML is simply an opinionated, higher-level interface with the focus being purely on ease-of-use and coherent intuitive design. You can read more about why we actually started building ZenML on our [blog](https://blog.zenml.io/why-zenml/).