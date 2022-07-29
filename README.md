<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->

[![PyPi][pypi-shield]][pypi-url]
[![PyPi][downloads-shield]][downloads-url]
[![Stargazers][stars-shield]][stars-url]
[![Forks][forks-shield]][forks-url]
[![Issues][issues-shield]][issues-url]
[![Contributors][contributors-shield]][contributors-url]
[![License][license-shield]][license-url]
[![CodeCov][codecov-shield]][codecov-url]
[![Build][build-shield]][build-url]
[![Interrogate][interrogate-shield]][interrogate-url]

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[pypi-shield]: https://img.shields.io/pypi/pyversions/zenml?style=for-the-badge
[pypi-url]: https://pypi.org/project/zenml/
[downloads-shield]: https://img.shields.io/pypi/dm/zenml?style=for-the-badge
[downloads-url]: https://pypi.org/project/zenml/
[codecov-shield]: https://img.shields.io/codecov/c/gh/zenml-io/zenml?style=for-the-badge
[codecov-url]: https://codecov.io/gh/zenml-io/zenml
[contributors-shield]: https://img.shields.io/github/contributors/zenml-io/zenml?style=for-the-badge
[contributors-url]: https://github.com/othneildrew/Best-README-Template/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/zenml-io/zenml?style=for-the-badge
[forks-url]: https://github.com/zenml-io/zenml/network/members
[stars-shield]: https://img.shields.io/github/stars/zenml-io/zenml?style=for-the-badge
[stars-url]: https://github.com/zenml-io/zenml/stargazers
[issues-shield]: https://img.shields.io/github/issues/zenml-io/zenml?style=for-the-badge
[issues-url]: https://github.com/zenml-io/zenml/issues
[license-shield]: https://img.shields.io/github/license/zenml-io/zenml?style=for-the-badge
[license-url]: https://github.com/zenml-io/zenml/blob/main/LICENSE
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://www.linkedin.com/company/zenml/
[twitter-shield]: https://img.shields.io/twitter/follow/zenml_io?style=for-the-badge
[twitter-url]: https://twitter.com/zenml_io
[slack-shield]: https://img.shields.io/badge/-Slack-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[slack-url]: https://zenml.io/slack-invite
[build-shield]: https://img.shields.io/github/workflow/status/zenml-io/zenml/Build,%20Lint,%20Unit%20&%20Integration%20Test?logo=github&style=for-the-badge
[build-url]: https://github.com/zenml-io/zenml/actions/workflows/ci.yml
[interrogate-shield]: https://img.shields.io/badge/Interrogate-100%25-brightgreen?style=for-the-badge&logo=interrogate
[interrogate-url]: https://interrogate.readthedocs.io/en/latest/

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://zenml.io">
    <img src="docs/book/assets/zenml_logo.png" alt="Logo" width="400">
  </a>

  <h3 align="center">Build portable, production-ready MLOps pipelines.</h3>

  <p align="center">
    An open-source framework.
    <br />
    <a href="https://docs.zenml.io/"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/zenml-io/zenml/issues">Report Bug</a>
    ·
    <a href="https://zenml.io/discussion">Vote Feature</a>
    ·
    <a href="https://blog.zenml.io/">Read Blog</a>
    <br />
    🎉 Version 0.11.0 is out. Check out the release notes
    <a href="https://www.linkedin.com/company/zenml/">here</a>.
    <br />
    <br />
    <a href="https://www.linkedin.com/company/zenml/">
    <img src="https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555" alt="Logo">
    </a>
    <a href="https://twitter.com/zenml_io">
    <img src="https://img.shields.io/badge/-Twitter-black.svg?style=for-the-badge&logo=twitter&colorB=555" alt="Logo">
    </a>
    <a href="https://zenml.io/slack-invite">
    <img src="https://img.shields.io/badge/-Slack-black.svg?style=for-the-badge&logo=slack&colorB=555" alt="Logo">
    </a>

    
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#🤖-why-zenml">Why ZenML?</a>
    </li>
    <li>
    <a href="#💡-what-is-zenml">What is ZenML?</a>
    </li>
    <li>
    <a href="#🎮-features">Features</a>
    </li>
    <li>
      <a href="#🤸-getting-started">Getting Started</a>
      <ul>
        <li><a href="#💾-installation">Installation</a></li>
        <li><a href="#🚅-quickstart">Quickstart</a></li>
      </ul>
    </li>
    <li><a href="#🪜-get-a-guided-tour-with-zenml-go">Get a guided tour with zenml go</a></li>
    <li><a href="#🍰-zenbytes">ZenBytes</a></li>
    <li><a href="#🗂️-zenfiles">ZenFiles</a></li>
    <li><a href="#👭-collaborate-with-your-team">Collaborate with your team</a></li>
    <li><a href="#📖-learn-more">Learn More</a></li>
    <li><a href="#🗺-roadmap">Roadmap</a></li>
    <li><a href="#🙋‍♀️-contributing-and-community">Contributing & Community</a></li>
    <li><a href="#👩‍👩‍👧‍👦-meet-the-team">Meet the Team</a></li>
    <li><a href="#🆘-where-to-get-help">Where to get help</a></li>
    <li><a href="#📜-license">License</a></li>
  </ol>
</details>

<br />

# 🤖 Why ZenML?

🤹 Are you an ML engineer or data scientist shipping models to production and juggling a plethora of tools? 

🤷‍♂️ Do you struggle with versioning data, code, and models in your projects? 

👀 Have you had trouble replicating production pipelines and monitoring models in production?

✅ If you answered yes to any, ZenML is here to help with all that, and more.

Everyone loves to train ML models, but few talks about shipping them into production, and even fewer can do it well.
At ZenML, we believe the journey from model development to production doesn't need to be long and painful.

![The long journey from experimentation to production.](docs/book/assets/1-pipeline-hard-reproduce.png)


With ZenML, you as a data scientist can concentrate on what you do best - developing ML models, and not worry about infrastructure or deployment tools.

If you come from unstructured notebooks or scripts with lots of manual processes, ZenML will make the path to production easier and faster for you and your team.
Using ZenML allows data scientists like you to own the entire pipeline - from experimentation to production.

This is why we built ZenML. Read more [here](https://blog.zenml.io/why-zenml/).




# 💡 What is ZenML?

<div align="center">
    <img src="docs/book/assets/tailor.gif">
</div>


ZenML is an extensible, open-source MLOps framework for creating portable, production-ready MLOps pipelines. It's built for Data Scientists, ML Engineers, and MLOps Developers to collaborate as they develop to production. 

ZenML offers simple, flexible syntax, is cloud- and tool-agnostic, and has interfaces/abstractions that are catered toward ML workflows. 
With ZenML you'll have all your favorite tools in one place so you can tailor a workflow that caters to your specific needs.

![ZenML unifies all your tools in one place.](docs/book/assets/sam-side-by-side-full-text.png)

Read more on all tools you can readily use in the [integrations](https://zenml.io/integrations) section. Can't find your tool? You can always [write your own integration](https://docs.zenml.io/developer-guide/advanced-usage/custom-flavors) to use it with ZenML.


# 🎮 Features
ZenML is actively under development.
Here are 9 most prominent features as of the current release. 

Read more about features [here](https://zenml.io/features).


<a href="https://zenml.io/features">
    <img src="docs/book/assets/features.png" alt="features">
</a>

# 🤸 Getting Started

## 💾 Installation

> **Note** - ZenML supports Python 3.7, 3.8, and 3.9.

ZenML is available for easy installation into your environment via [PyPI](https://pypi.org/project/zenml/):

```bash
pip install zenml
```

Alternatively, if you’re feeling adventurous, try out the bleeding edge installation:
> **Warning** - Proceed at your own risk, no guarantees are given!
```bash
pip install git+https://github.com/zenml-io/zenml.git@develop --upgrade
```


ZenML is also available as a Docker image hosted publicly on
[DockerHub](https://hub.docker.com/r/zenmldocker/zenml). Use the following
command to get started in a bash environment:

```shell
docker run -it zenmldocker/zenml /bin/bash
```


> **Warning** 
> #### Known installation issues for M1 Mac users
>
> If you have a M1 Mac machine and you are encountering an error > while trying to install ZenML, 
>please try to setup `brew` and `pyenv` with Rosetta 2 and then install ZenML. The issue arises because some of the dependencies 
>aren’t fully compatible with the vanilla ARM64 Architecture. The following links may be helpful (Thank you @Reid Falconer) :
>
>- [Pyenv with Apple Silicon](http://sixty-north.com/blog/pyenv-apple-silicon.html)
>- [Install Python Under Rosetta 2](https://medium.com/thinknum/how-to-install-python-under-rosetta-2-f98c0865e012)

## 🚅 Quickstart

Let's start by creating a simple pipeline that does the following - 
1. Loads the [digits dataset](https://archive.ics.uci.edu/ml/datasets/Optical+Recognition+of+Handwritten+Digits).
2. Trains a scikit-learn classifier to classify the images from the dataset.
3. Evaluates the classifier accuracy on a test set.

### Step 1: Initialize a ZenML repo
In your terminal run

```bash
zenml init
```

This creates a `.zen` folder in your current directory to store the necessary `zenml` configurations.

### Step 2: Installing the Scikit-learn integration
We will be using a classifier model from [Scikit-learn](https://scikit-learn.org/stable/), so let's install the `sklearn` integration.

```bash
zenml integration install sklearn -y
```

### Step 3: Defining steps and running the pipeline.
In ZenML, steps and pipelines are defined using Python decorators.
Put a `@step` or `@pipeline` decorator above a function to define a `step` or `pipeline`.

```python
import numpy as np
from sklearn.base import ClassifierMixin

from zenml.integrations.sklearn.helpers.digits import get_digits, get_digits_model
from zenml.pipelines import pipeline
from zenml.steps import step, Output

# Steps definition
@step
def importer() -> Output(
    X_train=np.ndarray, X_test=np.ndarray, y_train=np.ndarray, y_test=np.ndarray
):
    """Loads the digits array as normal numpy arrays."""
    X_train, X_test, y_train, y_test = get_digits()
    return X_train, X_test, y_train, y_test


@step
def trainer(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train a simple sklearn classifier for the digits dataset."""
    model = get_digits_model()
    model.fit(X_train, y_train)
    return model


@step
def evaluator(
    X_test: np.ndarray,
    y_test: np.ndarray,
    model: ClassifierMixin,
) -> float:
    """Calculate the accuracy on the test set"""
    test_acc = model.score(X_test, y_test)
    print(f"Test accuracy: {test_acc}")
    return test_acc

# Pipeline definition
@pipeline
def mnist_pipeline(
    importer,
    trainer,
    evaluator,
):
    """Links all the steps together in a pipeline"""
    X_train, X_test, y_train, y_test = importer()
    model = trainer(X_train=X_train, y_train=y_train)
    evaluator(X_test=X_test, y_test=y_test, model=model)


pipeline = mnist_pipeline(
    importer=importer(), # Step 1
    trainer=trainer(), # Step 2
    evaluator=evaluator(), # Step 3
)

# Run the pipeline locally.
pipeline.run()
```

This runs the pipeline locally on your machine following the steps defined in the pipeline.
You can scale this up to run on a full-fledged cloud platform by [switching stacks](https://docs.zenml.io/getting-started/core-concepts) with minimal (or no) code changes!

# 🪜 Get a guided tour with `zenml go`

For a more in-depth introduction to ZenML, taught through Jupyter
notebooks, install `zenml` via pip as described above and type:

```shell
zenml go
```

This will spin up a Jupyter notebook that showcases the above example plus more
on how to use and extend ZenML.

# 🍰 ZenBytes

ZenBytes is a series of short practical MLOps lessons through ZenML and its various integrations. 
It is intended for people looking to learn about MLOps generally, and also for ML practitioners who want to get started with ZenML.

After you've run and understood the example in [Quickstart](#🚅-quickstart), your next port of call is probably either the [fully-fleshed-out quickstart
example](https://github.com/zenml-io/zenml/tree/main/examples/quickstart) and
then to look at [the ZenBytes repository](https://github.com/zenml-io/zenbytes)
and notebooks.

# 🗂️ ZenFiles

ZenFiles are production-grade ML use-cases powered by ZenML. They are fully
fleshed out, end-to-end, projects that showcase ZenML's capabilities. They can
also serve as a template from which to start similar projects.

The ZenFiles project is fully maintained and can be viewed as a sister
repository of ZenML. Check it out [here](https://github.com/zenml-io/zenfiles).

# 👭 Collaborate with your team

ZenML is built to support teams working together. The underlying infrastructure
on which your ML workflows run can be shared, as can the data, assets and
artifacts that you need to enable your work. ZenML Profiles offer an easy way to
manage and switch between your stacks. The ZenML Server handles all the
interaction and sharing and you can host it wherever you'd like.

```
# Make sure to install ZenML with all necessary requirements for the ZenServer
pip install zenml[server]
zenml server up
```

Read more about collaboration in ZenML [here](https://docs.zenml.io/collaborate/collaborate-with-zenml).

# 📖 Learn More

| ZenML Resources | Description |
| ------------- | - |
| 🧘‍♀️ **[ZenML 101]** | New to ZenML? Here's everything you need to know! |
| ⚛️ **[Core Concepts]** | Some key terms and concepts we use. |
| 🗃 **[API Guide]** | Build production ML pipelines using class-based or functional API. |
| 🚀 **[New in v0.11.0]** | New features, bug fixes. |
| 🗳 **[Vote for Features]** | Pick what we work on next! |
| 📓 **[Docs]** | Full documentation for creating your own ZenML pipelines. |
| 📒 **[API Reference]** | The detailed reference for ZenML's API. |
| 🍰 **[ZenBytes]** | A guided and in-depth tutorial on MLOps and ZenML. |
| 🗂️️ **[ZenFiles]** | End-to-end projects using ZenML. |
| ⚽️ **[Examples]** | Learn best through examples where ZenML is used? We've got you covered. |
| 📬 **[Blog]** | Use cases of ZenML and technical deep dives on how we built it. |
| 🔈 **[Podcast]** | Conversations with leaders in ML, released every 2 weeks. |
| 📣 **[Newsletter]** | We build ZenML in public. Subscribe to learn how we work. |
| 💬 **[Join Slack]** | Need help with your specific use case? Say hi on Slack! |
| 🗺 **[Roadmap]** | See where ZenML is working to build new features. |
| 🙋‍♀️ **[Contribute]** | How to contribute to the ZenML project and code base. |

[ZenML 101]: https://docs.zenml.io/
[Core Concepts]: https://docs.zenml.io/getting-started/core-concepts
[API Guide]: https://docs.zenml.io/v/docs/developer-guide/steps-and-pipelines/functional-vs-class-based-api
[New in v0.11.0]: https://github.com/zenml-io/zenml/releases
[Vote for Features]: https://zenml.io/discussion
[Docs]: https://docs.zenml.io/
[API Reference]: https://apidocs.zenml.io/
[ZenBytes]: https://github.com/zenml-io/zenbytes
[ZenFiles]: https://github.com/zenml-io/zenfiles
[Examples]: https://github.com/zenml-io/zenml/tree/main/examples
[Blog]: https://blog.zenml.io/
[Podcast]: https://podcast.zenml.io/
[Newsletter]: https://zenml.io/newsletter/
[Join Slack]: https://zenml.io/slack-invite/
[Roadmap]: https://zenml.io/roadmap
[Contribute]: https://github.com/zenml-io/zenml/blob/main/CONTRIBUTING.md


# 🗺 Roadmap

ZenML is being built in public. The [roadmap](https://zenml.io/roadmap) is a
regularly updated source of truth for the ZenML community to understand where
the product is going in the short, medium, and long term.

ZenML is managed by a [core team](https://zenml.io/company#CompanyTeam) of developers that are
responsible for making key decisions and incorporating feedback from the
community. The team oversees feedback via various channels, and you can directly
influence the roadmap as follows:

- Vote on your most wanted feature on our [Discussion
  board](https://zenml.io/discussion). You can also request for new features here.
- Start a thread in our [Slack channel](https://zenml.io/slack-invite).


# 🙋‍♀️ Contributing and Community

We would love to develop ZenML together with our community! Best way to get
started is to select any issue from the [`good-first-issue`
label](https://github.com/zenml-io/zenml/labels/good%20first%20issue). If you
would like to contribute, please review our [Contributing
Guide](CONTRIBUTING.md) for all relevant details.

<br>

![Repobeats analytics
image](https://repobeats.axiom.co/api/embed/635c57b743efe649cadceba6a2e6a956663f96dd.svg
"Repobeats analytics image")


# 👩‍👩‍👧‍👦 Meet the Team

Have a question that's too hard to express on our Slack? Is it just too much effort to say everything on a 
long GitHub issue? Or are you just curious what ZenML has been up to in the past week? Well, register now for the ZenML Office 
(Half) Hour to get your answers and more!
It's free and open to everyone.

Every week, part of the ZenML core team will pop in for 30 minutes to interact directly with the community. Sometimes we'll be presenting a feature, other times just taking questions, and having fun. Join us if you are curious about ZenML, or just want to talk shop about MLOps.

We will host the gathering every Wednesday 8:30AM PT (5:30PM CET). 
Register now through [this link](https://www.eventbrite.com/e/zenml-meet-the-community-tickets-354426688767), 
or subscribe to the [public events calendar](https://calendar.google.com/calendar/u/0/r?cid=Y19iaDJ0Zm44ZzdodXBlbnBzaWplY3UwMmNjZ0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t) to get notified 
before every community gathering.

# 🆘 Where to get help

First point of call should be [our Slack group](https://zenml.io/slack-invite/).
Ask your questions about bugs or specific use cases and someone from the core
team will respond.

# 📜 License

ZenML is distributed under the terms of the Apache License Version 2.0. 
A complete version of the license is available in the [LICENSE](LICENSE) file in
this repository. Any contribution made to this project will be licensed under
the Apache License Version 2.0.
