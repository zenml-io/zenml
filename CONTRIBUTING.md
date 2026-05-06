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

- [🧑‍💻 Contributing to ZenML](#-contributing-to-zenml)
  - [⚡️ Quicklinks](#-quicklinks)
  - [🧑‍⚖️ Code of Conduct](#-code-of-conduct)
  - [🛫 Getting Started](#-getting-started)
    - [⁉️ Issues](#-issues)
    - [🏷 Pull Requests: When to make one](#-pull-requests-when-to-make-one)
    - [💯 Pull Requests: Workflow to Contribute](#-pull-requests-workflow-to-contribute)
    - [🧱 Pull Requests: Rebase on develop](#-pull-requests-rebase-your-branch-on-develop)
    - [🧐 Linting, formatting, and tests](#-linting-formatting-and-tests)
    - [🚨 Reporting a Vulnerability](#-reporting-a-vulnerability)
  - [Coding Conventions](#coding-conventions)
  - [👷 Creating a new Integration](#-creating-a-new-integration)
  - [🆘 Getting Help](#-getting-help)

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

### Good First Issues for New Contributors

The best way to start is to check the
[`good-first-issue`](https://github.com/issues?q=is%3Aopen+is%3Aissue+archived%3Afalse+user%3Azenml-io+label%3A%22good+first+issue%22)
label on the issue board. The core team creates these issues as necessary
smaller tasks that you can work on to get deeper into ZenML internals. These
should generally require relatively simple changes, probably affecting just one
or two files which we think are ideal for people new to ZenML.

The next step after that would be to look at the
[`good-second-issue`](https://github.com/issues?q=is%3Aopen+is%3Aissue+archived%3Afalse+user%3Azenml-io+label%3A%22good+second+issue%22)
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

### 🏷 Pull Requests: When to make one

Pull Requests (PRs) to ZenML are always welcome and can be a quick way to get your fix or
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

### 💯 Pull Requests: Workflow to Contribute

<p class="callout warning">Please note that development in ZenML happens off of the <b>develop</b> branch, <b>not main</b>, 
which is the default branch on GitHub. Therefore, please pay particular attention to step 5 and step 9 below. </p>

In general, we follow
the ["fork-and-pull" Git workflow](https://github.com/susam/gitpr)

1. Review and sign
   the [Contributor License Agreement](https://cla-assistant.io/zenml-io/zenml) (
   CLA).
2. Fork the repository to your own Github account.
3. Clone the project to your machine.
4. Checkout the **develop** branch <- `git checkout develop`.
5. Create a branch (again, off of the develop branch) locally with a succinct but descriptive name.
6. Commit changes to the branch
7. Follow the `Linting, formatting, and tests` guide to make sure your code adheres to the ZenML coding style (see below).
8. Push changes to your fork.
9. Open a PR in our repository (to the `develop` branch, **NOT** `main`) and
   follow the PR template so that we can efficiently review the changes.

### 🧱 Pull Requests: Rebase Your Branch on Develop

1. When making pull requests to ZenML, you should always make your changes on a branch that is based on `develop`. You can create a new branch based on `develop` by running the following command:
   ```
   git checkout -b <new-branch-name> develop
   ```
2. Fetch the latest changes from the remote `develop` branch:
   ```
   git fetch origin develop
   ```
3. Switch to your branch:
   ```
   git checkout <your-branch-name>
   ```
4. Rebase your branch on `develop`:
   ```
   git rebase origin/develop
   ```
   This will apply your branch's changes on top of the latest changes in `develop`, one commit at a time.
5. Resolve any conflicts that may arise during the rebase. Git will notify you if there are any conflicts that need to be resolved. Use a text editor to manually resolve the conflicts in the affected files.
6. After resolving the conflicts, stage the changes:
   ```
   git add .
   ```
7. Continue the rebase for all of your commits and go to 5) if there are conflicts.
   ```
   git rebase --continue
   ```
8. Push the rebased branch to your remote repository:
   ```
   git push origin --force <your-branch-name>
   ```
9. Open a pull request targeting the `develop` branch. The changes from your rebased branch will now be based on the latest `develop` branch.

### 🧐 Linting, formatting, and tests

To install ZenML from your local checked out files including all core dev-dependencies, run:

```
pip install -e ".[server,dev]"
```

Optionally, you might want to run the following commands to ensure you have all
integrations for `mypy` checks:

```
zenml integration install -y -i feast
pip install click~=8.0.3
mypy --install-types
```

Warning: This might take a while for both (~ 15 minutes each, depending on your machine), however if you have
time, please run it as it will make the
next commands error-free. Note that the `zenml integration install` command
might also fail on account of dependency conflicts so you can just install the
specific integration you're working on and manually run the mypy command for the
files you've been working on.

You can now run the following scripts to automatically format your
code and to check whether the code formatting, linting, docstrings, and
spelling is in order:

```
bash scripts/format.sh
bash scripts/run-ci-checks.sh
```

If you're on Windows you might have to run the formatting script as `bash
scripts/format.sh --no-yamlfix` and run the yamlfix command separately as
`yamlfix .github -v`.

Tests can be run as follows:

```
bash scripts/test-coverage-xml.sh
```

Please note that it is good practice to run the above commands before submitting
any Pull Request: The CI GitHub Action
will run it anyway, so you might as well catch the errors locally!

The CI captain rotation lives in `.github/ci-captains.yml`. The weekly captain
is the first responder for `develop-red` incidents opened by nightly slow CI and
backs up the authors identified in the suspect commit range.

### 🚨 Reporting a Vulnerability

Please refer to [our security / reporting instructions](./SECURITY.md) for
details on reporting vulnerabilities.


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
[Component Guide](https://docs.zenml.io/stack-components/component-guide)
in the docs and add your implementations. 

## 🆘 Getting Help

Join us in the [ZenML Slack Community](https://zenml.io/slack-invite/) to 
interact directly with the core team and community at large. This is a good 
place to ideate, discuss concepts or ask for help.
