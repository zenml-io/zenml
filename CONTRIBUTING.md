# 🧑‍💻 Contributing to ZenML

A big welcome and thank you for considering contributing to ZenML! It’s people
like you that make it a reality for users
in our community.

Reading and following these guidelines will help us make the contribution
process easy and effective for everyone
involved. It also communicates that you agree to respect the developers' time
management and develop these open-source projects. In return, we will reciprocate that respect by reading your
issue, assessing changes, and helping
you finalize your pull requests.

## ⚡️ Quicklinks

* [Code of Conduct](#code-of-conduct)
* [Getting Started](#getting-started)
    * [Issues](#issues)
    * [Pull Requests](#pull-requests)
* [Getting Help](#getting-help)

## 🧑‍⚖️ Code of Conduct

We take our open-source community seriously and hold ourselves and other
contributors to high standards of communication.
By participating and contributing to this project, you agree to uphold
our [Code of Conduct](https://github.com/zenml-io/zenml/blob/master/CODE-OF-CONDUCT.md)
.

## 🛫 Getting Started

Contributions are made to this repo via Issues and Pull Requests (PRs). A few
general guidelines that cover both:

- To report security vulnerabilities, please get in touch
  at [support@zenml.io](mailto:support@zenml.io), monitored by
  our security team.
- Search for existing Issues and PRs before creating your own.
- We work hard to make sure issues are handled on time, but it could take a
  while to investigate the root cause depending on the impact.

A friendly ping in the comment thread to the submitter or a contributor can help
draw attention if your issue is blocking.

The best way to start is to check the
[`good-first-issue`](https://github.com/zenml-io/zenml/labels/good%20first%20issue)
label on the issue board. The core team creates these issues as necessary
smaller tasks that you can work on to get deeper into ZenML internals. These
should generally require relatively simple changes, probably affecting just one
or two files which we think are ideal for people new to ZenML.

The next step after that would be to look at the
[`good-second-issue`](https://github.com/zenml-io/zenml/labels/good%20second%20issue)
label on the issue board. These are a bit more complex, might involve more
files, but should still be well-defined and achievable to people relatively new
to ZenML.

### ⁉️ Issues

Issues should be used to report problems with the library, request a new
feature, or to discuss potential changes before
a PR is created. When you create a new Issue, a template will be loaded that
will guide you through collecting and
providing the information we need to investigate.

If you find an Issue that addresses your problem, please add your own
reproduction information to the
existing issue rather than creating a new one. Adding
a [reaction](https://github.blog/2016-03-10-add-reactions-to-pull-requests-issues-and-comments/)
can also help by
indicating to our maintainers that a particular issue is affecting more than
just the reporter.

### 🏷 Pull Requests

PRs to ZenML are always welcome and can be a quick way to get your fix or
improvement slated for the next release. In
general, PRs should:

- Only fix/add the functionality in question **OR** address widespread
  whitespace/style issues, not both.
- Add unit or integration tests for fixed or changed functionality (if a test
  suite already exists).
- Address a single concern in the least number of changed lines as possible.
- Include documentation in the repo or in your Pull Request.
- Be accompanied by a filled-out Pull Request template (loaded automatically when
  a PR is created).

For changes that address core functionality or would require breaking changes (e.g. a major release), it's best to open
an Issue to discuss your proposal first. This is not required but can save time
creating and reviewing changes.

In general, we follow
the ["fork-and-pull" Git workflow](https://github.com/susam/gitpr)

1. Review and sign
   the [Contributor License Agreement](https://cla-assistant.io/zenml-io/zenml) (
   CLA).
2. Fork the repository to your own Github account
3. Clone the project to your machine
4. Create a branch locally with a succinct but descriptive name
5. Commit changes to the branch
6. Following any formatting and testing guidelines specific to this repo
7. Push changes to your fork
8. Open a PR in our repository (to the `develop` branch, **NOT** `main`) and
   follow the PR template so that we can efficiently review the changes.

### 🧐 Linting, formatting, and tests

ZenML is mainly developed using [Poetry](https://python-poetry.org/) as the
dependency management system. In order to
install all core dev-dependencies, do:

```
poetry install
```

Optionally, you might want to run the following commands to ensure you have all
integrations for `mypy` checks:

```
zenml integration install -f
mypy --install-types
```

Warning: This might take a while for both (~ 15 mins each, depending on your machine), however if you have
time, please run it as it will make the
next commands error-free.

It is easy to run the following scripts via Poetry to ensure code formatting and
linting is in order:

```
poetry run bash scripts/format.sh
poetry run bash scripts/lint.sh
poetry run bash scripts/check-spelling.sh
```

Tests can be run as follows:

```
poetry run bash scripts/test-coverage-xml.sh
```

Please note that it is good practice to run the above commands before submitting
any Pull Request: The CI GitHub Action
will run it anyway, so you might as well catch the errors locally!

### 🚨 Reporting a Vulnerability

If you think you have found a vulnerability, and even if you are not sure about it,
please report it right away by sending an
email to: support@zenml.com. Please try to be as explicit as possible,
describing all the steps and example code to
reproduce the security issue.

We will review it thoroughly and get back to you.

Please refrain from publicly discussing a potential security vulnerability as
this could potentially put our users at
risk! It's better to discuss privately and give us a chance to find a solution
first, to limit the potential impact
as much as possible.


## Coding Conventions

The code within the repository is structured in the following way - 
the most relevant places for contributors are highlighted with a `<-` arrow:

```
├── .github           -- Definition of the GH action workflows
├── docker            -- Dockerfiles used to build ZenML docker images
├── docs              <- The ZenML docs, CLI docs and API docs live here
│   ├── book          <- In case you make user facing changes, update docs here
│   └── mkdocs        -- Some configurations for the API/CLI docs
├── examples          <- When adding an integration, add an example here
├── scripts           -- Scripts used by Github Actions or for local linting/testing
├── src/zenml         <- The heart of ZenML
│   ├── <stack_component>   <- Each stack component has its own directory 
│   ├── cli                 <- Change and improve the CLI here
│   ├── config              -- The ZenML config methods live here
│   ├── integrations        <- Add new integrations here
│   ├── io                  -- File operation implementations
│   ├── materializers       <- Materializers responsible for reading/writing artifacts
│   ├── pipelines           <- The base pipeline and its decorator
│   ├── post_execution      <- Code for accessing past pipeline runs
│   ├── services            -- Code responsible for managing services
│   ├── stack               <- Stack, Stack Components and the flavor registry
│   ├── steps               <- Steps and their decorators are defined here
│   ├── utils               <- Collection on useful utils
│   ├── zen_server          -- Code for running the Zen Server
│   └── zen_stores          -- Code for storing stacks in multiple settings
└── test              <- Don't forget to write unit tests for your code
```

## 👷 Creating a new Integration

In case you want to create an entirely new integration that you would like to 
see supported by ZenML there are a few steps that you should follow:

1. Create the actual integration. Check out the 
[Integrations README](src/zenml/integrations/README.md)
for detailed step-by-step instructions.
2. Create an example of how to use the integration. Check out the 
[Examples README](examples/README.md) 
to find out what to do.
3. All integrations deserve to be documented. Make sure to pay a visit to the
[Integrations Page](docs/book/advanced-guide/integrations/integrations.md)
in the docs and add the integration. 

## 🆘 Getting Help

Join us in the [ZenML Slack Community](https://zenml.io/slack-invite/) to 
interact directly with the core team and community at large. This is a good 
place to ideate, discuss concepts or ask for help.
