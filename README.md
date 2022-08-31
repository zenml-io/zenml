<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->

[![PyPi][pypi-shield]][pypi-url]
[![PyPi][pypiversion-shield]][pypi-url]
[![PyPi][downloads-shield]][downloads-url]
[![Contributors][contributors-shield]][contributors-url]
[![License][license-shield]][license-url]
[![Build][build-shield]][build-url]
[![Interrogate][interrogate-shield]][interrogate-url]
<!-- [![CodeCov][codecov-shield]][codecov-url] -->

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[pypi-shield]: https://img.shields.io/pypi/pyversions/zenml?style=for-the-badge
[pypi-url]: https://pypi.org/project/zenml/
[pypiversion-shield]: https://img.shields.io/pypi/v/zenml?style=for-the-badge

[downloads-shield]: https://img.shields.io/pypi/dm/zenml?style=for-the-badge
[downloads-url]: https://pypi.org/project/zenml/
[codecov-shield]: https://img.shields.io/codecov/c/gh/zenml-io/zenml?style=for-the-badge
[codecov-url]: https://codecov.io/gh/zenml-io/zenml
[contributors-shield]: https://img.shields.io/github/contributors/zenml-io/zenml?style=for-the-badge
[contributors-url]: https://github.com/othneildrew/Best-README-Template/graphs/contributors
[license-shield]: https://img.shields.io/github/license/zenml-io/zenml?style=for-the-badge
[license-url]: https://github.com/zenml-io/zenml/blob/main/LICENSE
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://www.linkedin.com/company/zenml/
[twitter-shield]: https://img.shields.io/twitter/follow/zenml_io?style=for-the-badge
[twitter-url]: https://twitter.com/zenml_io
[slack-shield]: https://img.shields.io/badge/-Slack-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[slack-url]: https://zenml.io/slack-invite
[build-shield]: https://img.shields.io/github/workflow/status/zenml-io/zenml/Build,%20Lint,%20Unit%20&%20Integration%20Test/develop?logo=github&style=for-the-badge
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
    A simple yet powerful open-source framework that scales your MLOps stack with your needs.
    <br />
    <a href="https://docs.zenml.io/"><strong>Explore the docs »</strong></a>
    <br />
    <div align="center">
      Join our <a href="https://zenml.io/slack-invite" target="_blank">
      <img width="25" src="https://cdn3.iconfinder.com/data/icons/logos-and-brands-adobe/512/306_Slack-512.png" alt="Slack"/>
    <b>Slack Community</b> </a> and be part of the ZenML family.
    </div>
    <br />
    <a href="https://zenml.io/features">Features</a>
    ·
    <a href="https://zenml.io/roadmap">Roadmap</a>
    ·
    <a href="https://github.com/zenml-io/zenml/issues">Report Bug</a>
    ·
    <a href="https://zenml.io/discussion">Vote New Features</a>
    ·
    <a href="https://blog.zenml.io/">Read Blog</a>
    ·
    <a href="#-meet-the-team">Meet the Team</a>
    <br />
    🎉 Version 0.13.0 is out. Check out the release notes
    <a href="https://github.com/zenml-io/zenml/releases">here</a>.
    <br />
    <br />
    <a href="https://www.linkedin.com/company/zenml/">
    <img src="https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555" alt="Logo">
    </a>
    <a href="https://twitter.com/zenml_io">
    <img src="https://img.shields.io/badge/-Twitter-black.svg?style=for-the-badge&logo=twitter&colorB=555" alt="Logo">
    </a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>🏁 Table of Contents</summary>
  <ol>
    <li>
      <a href="#-why-zenml">Why ZenML?</a>
    </li>
    <li>
    <a href="#-what-is-zenml">What is ZenML?</a>
    </li>
    <li>
      <a href="#-getting-started">Getting Started</a>
      <ul>
        <li><a href="#-installation">Installation</a></li>
        <li><a href="#-first-run">First run</a></li>
        <li><a href="#-zenbytes">ZenBytes</a></li>
        <li><a href="#-zenfiles">ZenFiles</a></li>
      </ul>
    </li>
    <li><a href="#-collaborate-with-your-team">Collaborate with your team</a></li>
    <li><a href="#-learn-more">Learn More</a></li>
    <li><a href="#-roadmap">Roadmap</a></li>
    <li><a href="#-contributing-and-community">Contributing and Community</a></li>
    <li><a href="#-meet-the-team">Meet the Team</a></li>
    <li><a href="#-getting-help">Getting Help</a></li>
    <li><a href="#-license">License</a></li>
  </ol>
</details>

<br />

# 🤖 Why ZenML?

🤹 Are you an ML engineer or data scientist shipping models to production and juggling a plethora of tools? 

🤷‍♂️ Do you struggle with versioning data, code, and models in your projects? 

👀 Have you had trouble replicating production pipelines and monitoring models in production?

✅ If you answered yes to any of the above, ZenML is here to help with all that and more...

Everyone loves to train ML models, but few talks about shipping them into production, and even fewer can do it well.
At ZenML, we believe the journey from model development to production doesn't need to be long and painful.

![The long journey from experimentation to production.](docs/book/assets/1-pipeline-hard-reproduce.png)


With ZenML, you can concentrate on what you do best - developing ML models and not worry about infrastructure or deployment tools.

If you come from unstructured notebooks or scripts with lots of manual processes, ZenML will make the path to production easier and faster for you and your team.
Using ZenML allows you to own the entire pipeline - from experimentation to production.

This is why we built ZenML. Read more [here](https://blog.zenml.io/why-zenml/).




# 💡 What is ZenML?

<div align="center">
    <img src="docs/book/assets/tailor.gif">
</div>


ZenML is an extensible, open-source MLOps framework for creating portable, production-ready MLOps pipelines. It's built for Data Scientists, ML Engineers, and MLOps Developers to collaborate as they develop to production. 

ZenML offers a simple and flexible syntax, is cloud- and tool-agnostic, and has interfaces/abstractions catered toward ML workflows. 
With ZenML you'll have all your favorite tools in one place so you can tailor a workflow that caters to your specific needs.

![ZenML unifies all your tools in one place.](docs/book/assets/sam-side-by-side-full-text.png)

Read more on all tools you can readily use in the [integrations](https://zenml.io/integrations) section. Can't find your tool? You can always [write your own integration](https://docs.zenml.io/developer-guide/advanced-usage/custom-flavors) to use it with ZenML.

# 🤸 Getting Started

## 💾 Installation
**Option 1** - Install ZenML via [PyPI](https://pypi.org/project/zenml/):

```bash
pip install zenml
```
> **Note** - ZenML supports Python 3.7, 3.8, and 3.9.

**Option 2** - If you’re feeling adventurous, try out the bleeding-edge installation:

```bash
pip install git+https://github.com/zenml-io/zenml.git@develop --upgrade
```

> **Warning** - Fire dragons ahead. Proceed at your own risk!

**Option 3** - Install via a Docker image hosted publicly on
[DockerHub](https://hub.docker.com/r/zenmldocker/zenml):

```shell
docker run -it zenmldocker/zenml /bin/bash
```

> **Warning** 
> #### Known installation issues for M1 Mac users
>
> If you have an M1 Mac machine and encounter an installation error, 
> try setting up `brew` and `pyenv` with Rosetta 2 and then install ZenML. The issue arises because some dependencies 
> aren’t fully compatible with the vanilla ARM64 Architecture. The following links may be helpful (Thank you @Reid Falconer) :
>
>- [Pyenv with Apple Silicon](http://sixty-north.com/blog/pyenv-apple-silicon.html)
>- [Install Python Under Rosetta 2](https://medium.com/thinknum/how-to-install-python-under-rosetta-2-f98c0865e012)


## 🏇 First run

If you're here for the first time, we recommend running:

```shell
zenml go
```

This spins up a Jupyter notebook that walks you through various functionalities of ZenML at a high level.

By the end, you'll get a glimpse of how to use ZenML to:

+ Train, evaluate, deploy, and embed a model in an inference pipeline.
+ Automatically track and version data, models, and other artifacts.
+ Track model hyperparameters and metrics with experiment tracking tools.
+ Measure and visualize train-test skew, training-serving skew, and data drift.

## 👨‍🍳 Open Source MLOps Stack Recipes

ZenML boasts a ton of [integrations](https://zenml.io/integrations) into popular MLOps tools. The [ZenML Stack](https://docs.zenml.io/developer-guide/stacks-profiles-repositories) concept ensures that these tools work nicely together, therefore bringing structure and standardization into the MLOps workflow.

However, ZenML assumes that the stack infrastructure for these tools is already provisioned. If you do not have deployed infrastructure, and want to quickly spin up combinations of tools on the cloud, the [MLOps stack sister repository](https://github.com/zenml-io/mlops-stacks) contains a series of Terraform-based recipes to provision such stacks. These recipes can be used directly with ZenML:

```bash
pip install zenml[stacks]

zenml stack recipe deploy <NAME_OF_STACK_RECIPE> --import
```

The above command not only provisions the given tools, but also automatically creates a ZenML stack with the configuration of the deployed recipe!

## 🍰 ZenBytes
New to MLOps? Get up to speed by visiting the [ZenBytes](https://github.com/zenml-io/zenbytes) repo.

>ZenBytes is a series of short practical MLOps lessons taught using ZenML. 
>It covers many of the [core concepts](https://docs.zenml.io/getting-started/core-concepts) widely used in ZenML and MLOps in general.

## 📜 ZenFiles
Already comfortable with ZenML and wish to elevate your pipeline into production mode? Check out [ZenFiles](https://github.com/zenml-io/zenfiles).

>ZenFiles is a collection of production-grade ML use-cases powered by ZenML. They are fully fleshed out, end-to-end projects that showcase ZenML's capabilities. They can also serve as a template from which to start similar projects.

# 👭 Collaborate with your team

ZenML is built to support teams working together. 
The underlying infrastructure on which your ML workflows run can be shared, as can the data, assets, and artifacts in your workflow. 

In ZenML, a Stack represents a set of configurations for your MLOps tools and infrastructure. You can quickly share your ZenML stack with anyone by exporting the stack:

```
zenml stack export <STACK_NAME> <FILENAME.yaml>
```

Similarly, you can import a stack by running:
```
zenml stack import <STACK_NAME> <FILENAME.yaml>
```

Learn more on importing/exporting stacks [here](https://docs.zenml.io/collaborate/stack-export-import).


The [ZenML Profiles](https://docs.zenml.io/collaborate/zenml-store) offer an easy way to manage and switch between your stacks. All your stacks, components, and other classes of ZenML objects can be stored in a central location and shared across multiple users, teams, and automated systems such as CI/CD processes.

With the [ZenServer](https://docs.zenml.io/collaborate/zenml-server) 
you can deploy ZenML as a centralized service and connect entire teams and organizations to an easy-to-manage collaboration platform that provides a unified view of the MLOps processes, tools, and technologies that support your entire AI/ML project lifecycle.

Read more about using ZenML for collaboration [here](https://docs.zenml.io/collaborate/collaborate-with-zenml).

# 📖 Learn More

| ZenML Resources | Description |
| ------------- | - |
| 🧘‍♀️ **[ZenML 101]** | New to ZenML? Here's everything you need to know! |
| ⚛️ **[Core Concepts]** | Some key terms and concepts we use. |
| 🚀 **[Our latest release]** | New features, bug fixes. |
| 🗳 **[Vote for Features]** | Pick what we work on next! |
| 📓 **[Docs]** | Full documentation for creating your own ZenML pipelines. |
| 📒 **[API Reference]** | Detailed reference on ZenML's API. |
| 🍰 **[ZenBytes]** | A guided and in-depth tutorial on MLOps and ZenML. |
| 🗂️️ **[ZenFiles]** | End-to-end projects using ZenML. |
| 👨‍🍳 **[MLOps Stacks]** | Terraform based infrastructure recipes for pre-made ZenML stacks. |
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
[Our latest release]: https://github.com/zenml-io/zenml/releases
[Vote for Features]: https://zenml.io/discussion
[Docs]: https://docs.zenml.io/
[API Reference]: https://apidocs.zenml.io/
[ZenBytes]: https://github.com/zenml-io/zenbytes
[ZenFiles]: https://github.com/zenml-io/zenfiles
[MLOps Stacks]: https://github.com/zenml-io/mlops-stacks
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
  board](https://zenml.io/discussion).
- Start a thread in our [Slack channel](https://zenml.io/slack-invite).
- [Create an issue](https://github.com/zenml-io/zenml/issues/new/choose) on our Github repo.



# 🙌 Contributing and Community

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

![Meet the Team](./docs/book/assets/meet_the_team.jpeg)

Have a question that's too hard to express on our Slack? Is it just too much effort to say everything on a 
long GitHub issue? Or are you just curious about what ZenML has been up to in the past week? Well, register now for the ZenML Office (Half) Hour to get your answers and more!
It's free and open to everyone.

Every week, part of the ZenML [core team](https://zenml.io/company#CompanyTeam) will pop in for 30 minutes to interact directly with the community. Sometimes we'll be presenting a feature. Other times we just take questions and have fun. Join us if you are curious about ZenML, or just want to talk shop about MLOps.



We will host the gathering every Wednesday 8:30AM PT (5:30PM CET). 
Register now through [this link](https://www.eventbrite.com/e/zenml-meet-the-community-tickets-354426688767), 
or subscribe to the [public events calendar](https://calendar.google.com/calendar/u/0/r?cid=Y19iaDJ0Zm44ZzdodXBlbnBzaWplY3UwMmNjZ0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t) to get notified 
before every community gathering.

# 🆘 Getting Help

The first point of call should be [our Slack group](https://zenml.io/slack-invite/).
Ask your questions about bugs or specific use cases, and someone from the [core team](https://zenml.io/company#CompanyTeam) will respond.
Or, if you prefer, [open an issue](https://github.com/zenml-io/zenml/issues/new/choose) on our GitHub repo.


# 📜 License

ZenML is distributed under the terms of the Apache License Version 2.0. 
A complete version of the license is available in the [LICENSE](LICENSE) file in
this repository. Any contribution made to this project will be licensed under
the Apache License Version 2.0.
