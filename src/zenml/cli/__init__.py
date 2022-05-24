#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""
ZenML CLI
==================

The ZenML CLI tool is usually downloaded and installed via PyPI and a
``pip install zenml`` command. Please see the Installation & Setup
section above for more information about that process.

How to use the CLI
------------------

Our CLI behaves similarly to many other CLIs for basic features. In
order to find out which version of ZenML you are running, type:

```bash
   zenml version
```
If you ever need more information on exactly what a certain command will
do, use the ``--help`` flag attached to the end of your command string.

For example, to get a sense of all the commands available to you
while using the ``zenml`` command, type:

```bash
   zenml --help
```
If you were instead looking to know more about a specific command, you
can type something like this:

```bash
   zenml metadata-store register --help
```

This will give you information about how to register a metadata store.
(See below for more on that).

If you want to instead understand what the concept behind a group is, you 
can use the `explain` sub-command. For example, to see more details behind 
what a `metadata-store` is, you can type:

```bash
zenml metadata-store explain
```

This will give you an explanation of that concept in more detail.

Beginning a Project
-------------------

In order to start working on your project, initialize a ZenML repository
within your current directory with ZenML’s own config and resource management
tools:

```bash
zenml init
```

This is all you need to begin using all the MLOps goodness that ZenML
provides!

By default, ``zenml init`` will install its own hidden ``.zen`` folder
inside the current directory from which you are running the command.
You can also pass in a directory path manually using the
``--repo_path`` option:

```bash
zenml init --repo_path /path/to/dir
```
If you wish to specify that you do not want analytics to be transmitted
back to ZenML about your usage of the tool, pass in ``False`` to the
``--analytics_opt_in`` option:

```bash
zenml init --analytics_opt_in false
```
If you wish to delete all data relating to your project from the
directory, use the ``zenml clean`` command. This will:

-  delete all pipelines
-  delete all artifacts
-  delete all metadata

*Note that the* ``clean`` *command is not implemented for the current
version.*

Loading and using pre-built examples
------------------------------------

If you don’t have a project of your own that you’re currently working
on, or if you just want to play around a bit and see some functional
code, we’ve got your back! You can use the ZenML CLI tool to download
some pre-built examples.

We know that working examples are a great way to get to know a tool, so
we’ve made some examples for you to use to get started. (This is
something that will grow as we add more).

To list all the examples available to you, type:

```bash
zenml example list
```
If you want more detailed information about a specific example, use the
``info`` subcommand in combination with the name of the example, like
this:

```bash
zenml example info quickstart
```
If you want to pull all the examples into your current working directory
(wherever you are executing the ``zenml`` command from in your
terminal), the CLI will create a ``zenml_examples`` folder for you if it
doesn’t already exist whenever you use the ``pull`` subcommand. The
default is to copy all the examples, like this:

```bash
zenml example pull
```
If you’d only like to pull a single example, add the name of that
example (for example, ``quickstart``) as an argument to the same
command, as follows:

```bash
zenml example pull quickstart
```
If you would like to force-redownload the examples, use the ``--yes``
or ``-y`` flag as in this example:

```bash
zenml example pull --yes
```
This will redownload all the examples afresh, using the same version of
ZenML as you currently have installed. If for some reason you want to
download examples corresponding to a previous release of ZenML, use the
``--version`` or ``-v`` flag to specify, as in the following example:

```bash
zenml example pull --yes --version 0.3.8
```
If you wish to run the example, allowing the ZenML CLI to do the work of setting
up whatever dependencies are required, use the ``run`` subcommand:

```bash
zenml example run quickstart
```

Using integrations
------------------

Integrations are the different pieces of a project stack that enable custom
functionality. This ranges from bigger libraries like
[`kubeflow`](https://www.kubeflow.org/) for orchestration down to smaller
visualization tools like [`facets`](https://pair-code.github.io/facets/). Our
CLI is an easy way to get started with these integrations.

To list all the integrations available to you, type:

```bash
zenml integration list
```

To see the requirements for a specific integration, use the `requirements`
command:

```bash
zenml integration requirements INTEGRATION_NAME
```

If you wish to install the integration, using the requirements listed in the
previous command, `install` allows you to do this for your local environment:

```bash
zenml integration install INTEGRATION_NAME
```

Note that if you don't specify a specific integration to be installed, the
ZenML CLI will install **all** available integrations.

Uninstalling a specific integration is as simple as typing:

```bash
zenml integration uninstall INTEGRATION_NAME
```

Customizing your Metadata Store
-------------------------------

The configuration of each pipeline, step, backend, and produced
artifacts are all tracked within the metadata store. By default, ZenML
initializes your repository with a metadata store kept on your local
machine. If you wish to register a new metadata store, do so with the
``register`` command:

```bash
zenml metadata-store register METADATA_STORE_NAME --flavor=METADATA_STORE_FLAVOR [--OPTIONS]
```
If you wish to list the metadata stores that have already been
registered within your ZenML project / repository, type:

```bash
zenml metadata-store list
```
If you wish to delete a particular metadata store, pass the name of the
metadata store into the CLI with the following command:

```bash
zenml metadata-store delete METADATA_STORE_NAME
```

Customizing your Artifact Store
-------------------------------

The artifact store is where all the inputs and outputs of your pipeline
steps are stored. By default, ZenML initializes your repository with an
artifact store with everything kept on your local machine. If you wish
to register a new artifact store, do so with the ``register`` command:

```bash
zenml artifact-store register ARTIFACT_STORE_NAME --flavor=ARTIFACT_STORE_FLAVOR [--OPTIONS]
```
If you wish to list the artifact stores that have already been
registered within your ZenML project / repository, type:

```bash
zenml artifact-store list
```
If you wish to delete a particular artifact store, pass the name of the
artifact store into the CLI with the following command:

```bash
zenml artifact-store delete ARTIFACT_STORE_NAME
```

Customizing your Orchestrator
-----------------------------

An orchestrator is a special kind of backend that manages the running of
each step of the pipeline. Orchestrators administer the actual pipeline
runs. By default, ZenML initializes your repository with an orchestrator
that runs everything on your local machine.

If you wish to register a new orchestrator, do so with the ``register``
command:

```bash
zenml orchestrator register ORCHESTRATOR_NAME --flavor=ORCHESTRATOR_FLAVOR [--ORCHESTRATOR_OPTIONS]
```
If you wish to list the orchestrators that have already been registered
within your ZenML project / repository, type:

```bash
zenml orchestrator list
```
If you wish to delete a particular orchestrator, pass the name of the
orchestrator into the CLI with the following command:

```bash
zenml orchestrator delete ORCHESTRATOR_NAME
```

Customizing your Container Registry
-----------------------------------

The container registry is where all the images that are used by a
container-based orchestrator are stored. By default, a default ZenML local stack
will not register a container registry. If you wish to register a new container
registry, do so with the `register` command:

```bash
zenml container-registry register REGISTRY_NAME --flavor=REGISTRY_FLAVOR [--REGISTRY_OPTIONS]
```

If you want the name of the current container registry, use the `get` command:

```bash
zenml container-registry get
```

To list all container registries available and registered for use, use the
`list` command:

```bash
zenml container-registry list
```

For details about a particular container registry, use the `describe` command.
By default, (without a specific registry name passed in) it will describe the
active or currently used container registry:

```bash
zenml container-registry describe [REGISTRY_NAME]
```

To delete a container registry (and all of its contents), use the `delete`
command:

```bash
zenml container-registry delete REGISTRY_NAME
```

Customizing your Experiment Tracker
-----------------------------------

Experiment trackers let you track your ML experiments by logging the parameters
and allowing you to compare between different runs. If you want to use an
experiment tracker in one of your stacks, you need to first register it:

```bash
zenml experiment-tracker register EXPERIMENT_TRACKER_NAME \
    --flavor=EXPERIMENT_TRACKER_FLAVOR [--EXPERIMENT_TRACKER_OPTIONS]
```

If you want the name of the current experiment tracker, use the `get` command:

```bash
zenml experiment-tracker get
```

To list all experiment trackers available and registered for use, use the
`list` command:

```bash
zenml experiment-tracker list
```

For details about a particular experiment tracker, use the `describe` command.
By default, (without a specific experiment tracker name passed in) it will
describe the active or currently-used experiment tracker:

```bash
zenml experiment-tracker describe [EXPERIMENT_TRACKER_NAME]
```

To delete an experiment tracker, use the `delete` command:

```bash
zenml experiment-tracker delete EXPERIMENT_TRACKER_NAME
```

Customizing your Step Operator
------------------------------

Step operators allow you to run individual steps in a custom environment
different from the default one used by your active orchestrator. One example
use-case is to run a training step of your pipeline in an environment with GPUs
available. By default, a default ZenML local stack will not register a step
operator. If you wish to register a new step operator, do so with the
`register` command:

```bash
zenml step-operator register STEP_OPERATOR_NAME --type STEP_OPERATOR_FLAVOR [--STEP_OPERATOR_OPTIONS]
```

If you want the name of the current step operator, use the `get` command:

```bash
zenml step-operator get
```

To list all step operators available and registered for use, use the
`list` command:

```bash
zenml step-operator list
```

For details about a particular step operator, use the `describe` command.
By default, (without a specific operator name passed in) it will describe the
active or currently used step operator:

```bash
zenml step-operator describe [STEP_OPERATOR_NAME]
```

To delete a step operator (and all of its contents), use the `delete`
command:

```bash
zenml step-operator delete STEP_OPERATOR_NAME
```

Setting up a Secrets Manager
----------------------------

ZenML offers a way to securely store secrets associated with your project. To
set up a local file-based secrets manager, use the following CLI command:

```bash
zenml secrets-manager register SECRETS_MANAGER_NAME --flavor=local
```

This can then be used as part of your Stack (see below).

Using Secrets
-------------

Secrets are administered by the Secrets Manager. You must first register that
and then register a stack that includes the secrets manager before you can start
to use it. To get a full list of all the possible commands, type `zenml secret
--help`. A ZenML Secret is a collection or grouping of key-value pairs. These
Secret groupings come in different types, and certain types have predefined keys
that should be used. For example, an AWS secret has predefined keys of
`aws_access_key_id` and `aws_secret_access_key` (and an optional
`aws_session_token`). If you do not have a specific secret type you wish to use,
ZenML will use the `arbitrary` type to store your key-value pairs.

To register a secret, use the `register` command and pass the key-value pairs
as command line arguments:

```bash
zenml secret register SECRET_NAME --key1=value1 --key2=value2 --key3=value3 ...
```

Note that the keys and values will be preserved in your `bash_history` file, so
you may prefer to use the interactive `register` command instead:

```shell
zenml secret register SECRET_NAME -i
```

As an alternative to the interactive mode, also useful for values that
are long or contain newline or special characters, you can also use the special
`@` syntax to indicate to ZenML that the value needs to be read from a file:

```bash
zenml secret register SECRET_NAME --schema=aws \
   --aws_access_key_id=1234567890 \
   --aws_secret_access_key=abcdefghij \
   --aws_session_token=@/path/to/token.txt
```


To list all the secrets available, use the `list` command:

```bash
zenml secret list
```

To get the key-value pairs for a particular secret, use the `get` command:

```bash
zenml secret get SECRET_NAME
```

To update a secret, use the `update` command:

```bash
zenml secret update SECRET_NAME --key1=value1 --key2=value2 --key3=value3 ...
```

Note that the keys and values will be preserved in your `bash_history` file, so
you may prefer to use the interactive `update` command instead:

```shell
zenml secret update SECRET_NAME -i
```

Finally, to delete a secret, use the `delete` command:

```bash
zenml secret delete SECRET_NAME
```

Add a Feature Store to your Stack
---------------------------------

ZenML supports connecting to a Redis-backed Feast feature store as a stack
component integration. To set up a feature store, use the following CLI command:

```shell
zenml feature-store register FEATURE_STORE_NAME --flavor=feast
--feast_repo=REPO_PATH --online_host HOST_NAME --online_port ONLINE_PORT_NUMBER
```

Once you have registered your feature store as a stack component, you can use it
in your ZenML Stack.

Interacting with Deployed Models
--------------------------------

If you want to simply see what models have been deployed within your stack, run
the following command:

```bash
zenml served-models list
```

This should give you a list of served models containing their uuid, the name
of the pipeline that produced them including the run id and the step name as
well as the status.
This information should help you identify the different models.

If you want further information about a specific model, simply copy the
UUID and the following command.

```bash
zenml served-models describe <UUID>
```

If you are only interested in the prediction-url of the specific model you can
also run:

```bash
zenml served-models get-url <UUID>
```

Finally, you will also be able to start/stop the services using the following
 two commands:

```bash
zenml served-models start <UUID>
zenml served-models stop <UUID>
```

If you want to completely remove a served model you can also irreversibly delete
 it using:

```bash
zenml served-models delete <UUID>
```

Administering the Stack
-----------------------

The stack is a grouping of your artifact store, your metadata store and
your orchestrator. With the ZenML tool, switching from a local stack to
a distributed cloud environment can be accomplished with just a few CLI
commands.

To register a new stack, you must already have registered the individual
components of the stack using the commands listed above.

Use the ``zenml stack register`` command to register your stack. It
takes four arguments as in the following example:

```bash
zenml stack register STACK_NAME \
       -m METADATA_STORE_NAME \
       -a ARTIFACT_STORE_NAME \
       -o ORCHESTRATOR_NAME
```

Each corresponding argument should be the name you passed in as an
identifier for the artifact store, metadata store or orchestrator when
you originally registered it. (If you want to use your secrets manager, you
should pass its name in with the `-x` option flag.)

If you want to immediately set this newly created stack as your active stack,
simply pass along the `--set` flag.

```bash
zenml stack register STACK_NAME -m METADATA_STORE_NAME ... --set
```

To list the stacks that you have registered within your current ZenML
project, type:

```bash
zenml stack list
```
To delete a stack that you have previously registered, type:

```bash
zenml stack delete STACK_NAME
```
By default, ZenML uses a local stack whereby all pipelines run on your
local computer. If you wish to set a different stack as the current
active stack to be used when running your pipeline, type:

```bash
zenml stack set STACK_NAME
```
This changes a configuration property within your local environment.

To see which stack is currently set as the default active stack, type:

```bash
zenml stack get
```

If you wish to transfer one of your stacks to another profile or even another
machine, you can do so by exporting the stack configuration and then importing
it again.

To export a stack to YAML, run the following command:

```bash
zenml stack export STACK_NAME FILENAME.yaml
```

This will create a FILENAME.yaml containing the config of your stack and all
of its components, which you can then import again like this:

```bash
zenml stack import STACK_NAME FILENAME.yaml
```

If you wish to update a stack that you have already registered, first make sure
you have registered whatever components you want to use, then use the following
command:

```bash
# assuming that you have already registered a new orchestrator
# with NEW_ORCHESTRATOR_NAME
zenml stack update STACK_NAME -o NEW_ORCHESTRATOR_NAME
```

You can update one or many stack components at the same time out of the ones
that ZenML supports. To see the full list of options for updating a stack, use
the following command:

```bash
zenml stack update --help
```

To remove a stack component from a stack, use the following command:

```shell
# assuming you want to remove the secrets-manager and the feature-store
# from your stack
zenml stack remove-component -x -f
```

If you wish to rename your stack, use the following command:

```shell
zenml stack rename STACK_NAME NEW_STACK_NAME
```

If you wish to update a specific stack component, use the following command,
switching out "STACK_COMPONENT" for the component you wish to update (i.e.
'orchestrator' or 'artifact-store' etc):

```shell
zenml STACK_COMPONENT update --some_property=NEW_VALUE
```

Note that you are not permitted to update the stack name or UUID in this way. To
change the name of your stack component, use the following command:

```shell
zenml STACK_COMPONENT rename STACK_COMPONENT_NAME NEW_STACK_COMPONENT_NAME
```

If you wish to remove an attribute (or multiple attributes) from a stack
component, use the following command:

```shell
zenml STACK_COMPONENT remove-attribute STACK_COMPONENT_NAME --ATTRIBUTE_NAME [--OTHER_ATTRIBUTE_NAME]
```

Note that you can only remove optional attributes.

Managing users, teams, projects and roles
-----------------------------------------

When using the ZenML service, you can manage permissions by managing users,
teams, projects and roles using the CLI.
If you want to create a new user or delete an existing one, run either

```bash
zenml user create USER_NAME
```
or
```bash
zenml user delete USER_NAME
```

To see a list of all users, run:
```bash
zenml user list
```

A team is a grouping of many users that allows you to quickly assign and
revoke roles. If you want to create a new team, run:

```bash
zenml team create TEAM_NAME
```
To add one or more users to a team, run:
```bash
zenml team add TEAM_NAME --user USER_NAME [--user USER_NAME ...]
```
Similarly, to remove users from a team run:
```bash
zenml team remove TEAM_NAME --user USER_NAME [--user USER_NAME ...]
```
To delete a team (keep in mind this will revoke any roles assigned to this
team from the team members), run:
```bash
zenml team delete TEAM_NAME
```

To see a list of all teams, run:
```bash
zenml team list
```

A role groups permissions and can be assigned to users or teams. To create or
delete a role, run one of the following commands:
```bash
zenml role create ROLE_NAME
zenml role delete ROLE_NAME
```

To see a list of all roles, run:
```bash
zenml role list
```

If you want to assign or revoke a role from users or teams, you can run

```bash
zenml role assign ROLE_NAME --user USER_NAME [--user USER_NAME ...]
zenml role assign ROLE_NAME --team TEAM_NAME [--team TEAM_NAME ...]
```
or
```bash
zenml role revoke ROLE_NAME --user USER_NAME [--user USER_NAME ...]
zenml role revoke ROLE_NAME --team TEAM_NAME [--team TEAM_NAME ...]
```

You can see a list of all current role assignments by running:

```bash
zenml role assignment list
```
"""

from zenml.cli.base import *  # noqa
from zenml.cli.config import *  # noqa
from zenml.cli.example import *  # noqa
from zenml.cli.feature import *  # noqa
from zenml.cli.integration import *  # noqa
from zenml.cli.pipeline import *  # noqa
from zenml.cli.secret import *  # noqa
from zenml.cli.served_models import *  # noqa
from zenml.cli.server import *  # noqa
from zenml.cli.stack import *  # noqa
from zenml.cli.stack_components import *  # noqa
from zenml.cli.user_management import *  # noqa
from zenml.cli.version import *  # noqa
