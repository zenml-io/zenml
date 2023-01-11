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
"""ZenML CLI.

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
   zenml artifact-store register --help
```

This will give you information about how to register an artifact store.
(See below for more on that).

If you want to instead understand what the concept behind a group is, you 
can use the `explain` sub-command. For example, to see more details behind 
what a `artifact-store` is, you can type:

```bash
zenml artifact-store explain
```

This will give you an explanation of that concept in more detail.

Beginning a Project
-------------------

In order to start working on your project, initialize a ZenML repository
within your current directory with ZenML's own config and resource management
tools:

```bash
zenml init
```

This is all you need to begin using all the MLOps goodness that ZenML
provides!

By default, ``zenml init`` will install its own hidden ``.zen`` folder
inside the current directory from which you are running the command.
You can also pass in a directory path manually using the
``--path`` option:

```bash
zenml init --path /path/to/dir

If you wish to delete all data relating to your project from the
directory, use the ``zenml clean`` command. This will:

-  delete all pipelines and pipeline runs
-  delete all artifacts
-  delete all metadata

Loading and using pre-built examples
------------------------------------

If you don't have a project of your own that you're currently working
on, or if you just want to play around a bit and see some functional
code, we've got your back! You can use the ZenML CLI tool to download
some pre-built examples.

We know that working examples are a great way to get to know a tool, so
we've made some examples for you to use to get started. (This is
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
doesn't already exist whenever you use the ``pull`` subcommand. The
default is to copy all the examples, like this:

```bash
zenml example pull
```

If you'd only like to pull a single example, add the name of that
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

If you wish to update/share

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
zenml step-operator register STEP_OPERATOR_NAME --flavor STEP_OPERATOR_FLAVOR [--STEP_OPERATOR_OPTIONS]
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
zenml secrets-manager secret register SECRET_NAME --key1=value1 --key2=value2 --key3=value3 ...
```

Note that the keys and values will be preserved in your `bash_history` file, so
you may prefer to use the interactive `register` command instead:

```shell
zenml secrets-manager secret register SECRET_NAME -i
```

As an alternative to the interactive mode, also useful for values that
are long or contain newline or special characters, you can also use the special
`@` syntax to indicate to ZenML that the value needs to be read from a file:

```bash
zenml secrets-manager secret register SECRET_NAME --schema=aws \
   --aws_access_key_id=1234567890 \
   --aws_secret_access_key=abcdefghij \
   --aws_session_token=@/path/to/token.txt
```


To list all the secrets available, use the `list` command:

```bash
zenml secrets-manager secret list
```

To get the key-value pairs for a particular secret, use the `get` command:

```bash
zenml secrets-manager secret get SECRET_NAME
```

To update a secret, use the `update` command:

```bash
zenml secrets-manager secret update SECRET_NAME --key1=value1 --key2=value2 --key3=value3 ...
```

Note that the keys and values will be preserved in your `bash_history` file, so
you may prefer to use the interactive `update` command instead:

```shell
zenml secrets-manager secret update SECRET_NAME -i
```

Finally, to delete a secret, use the `delete` command:

```bash
zenml secrets-manager secret delete SECRET_NAME
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

Interacting with Model Deployers
-----------------------------------------

Model deployers are stack components responsible for online model serving.
They are responsible for deploying models to a remote server. Model deployers
also act as a registry for models that are served with ZenML.

If you wish to register a new model deployer, do so with the
`register` command:

```bash
zenml model-deployer register MODEL_DEPLOYER_NAME --flavor=MODEL_DEPLOYER_FLAVOR [--OPTIONS]
```

If you wish to list the model-deployers that have already been registered
within your ZenML project / repository, type:

```bash
zenml model-deployer list
```

If you wish to get more detailed information about a particular model deployer
within your ZenML project / repository, type:

```bash
zenml model-deployer describe MODEL_DEPLOYER_NAME
```

If you wish to delete a particular model deployer, pass the name of the
model deployers into the CLI with the following command:

```bash
zenml model-deployer delete MODEL_DEPLOYER_NAME
```

If you wish to retrieve logs corresponding to a particular model deployer, pass
the name of the model deployer into the CLI with the following command:

```bash
zenml model-deployer logs MODEL_DEPLOYER_NAME
```

Interacting with Deployed Models
--------------------------------

If you want to simply see what models have been deployed within your stack, run
the following command:

```bash
zenml model-deployer models list
```

This should give you a list of served models containing their uuid, the name
of the pipeline that produced them including the run id and the step name as
well as the status.
This information should help you identify the different models.

If you want further information about a specific model, simply copy the
UUID and the following command.

```bash
zenml model-deployer models describe <UUID>
```

If you are only interested in the prediction-url of the specific model you can
also run:

```bash
zenml model-deployer models get-url <UUID>
```

Finally, you will also be able to start/stop the services using the following
 two commands:

```bash
zenml model-deployer models start <UUID>
zenml model-deployer models stop <UUID>
```

If you want to completely remove a served model you can also irreversibly delete
 it using:

```bash
zenml model-deployer models delete <UUID>
```

Administering the Stack
-----------------------

The stack is a grouping of your artifact store, your orchestrator, and other
optional MLOps tools like experiment trackers or model deployers.
With the ZenML tool, switching from a local stack to a distributed cloud
environment can be accomplished with just a few CLI commands.

To register a new stack, you must already have registered the individual
components of the stack using the commands listed above.

Use the ``zenml stack register`` command to register your stack. It
takes four arguments as in the following example:

```bash
zenml stack register STACK_NAME \
       -a ARTIFACT_STORE_NAME \
       -o ORCHESTRATOR_NAME
```

Each corresponding argument should be the name, id or even the first few letters
 of the id that uniquely identify the artifact store or orchestrator.
(If you want to use your secrets manager, you should pass its name in with the
`-x` option flag.)

If you want to immediately set this newly created stack as your active stack,
simply pass along the `--set` flag.

```bash
zenml stack register STACK_NAME ... --set
```

If you want to share the stack and all of its components with everyone using
the same ZenML deployment, simply pass along the `--share` flag.

```bash
zenml stack register STACK_NAME ... --share
```

Even if you haven't done so at creation time of the stack, you can always
decide to do so at a later stage.

```bash
zenml stack share STACK_NAME
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

If you want to copy a stack, run the following command:
```shell
zenml stack copy SOURCE_STACK_NAME TARGET_STACK_NAME
```

If you wish to transfer one of your stacks to another machine, you can do so 
by exporting the stack configuration and then importing it again.

To export a stack to YAML, run the following command:

```bash
zenml stack export STACK_NAME FILENAME.yaml
```

This will create a FILENAME.yaml containing the config of your stack and all
of its components, which you can then import again like this:

```bash
zenml stack import STACK_NAME -f FILENAME.yaml
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

If you want to copy a stack component, run the following command:
```bash
zenml STACK_COMPONENT copy SOURCE_COMPONENT_NAME TARGET_COMPONENT_NAME
```

If you wish to update a specific stack component, use the following command,
switching out "STACK_COMPONENT" for the component you wish to update (i.e.
'orchestrator' or 'artifact-store' etc.):

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
zenml STACK_COMPONENT remove-attribute STACK_COMPONENT_NAME ATTRIBUTE_NAME [OTHER_ATTRIBUTE_NAME]
```

Note that you can only remove optional attributes.

If you want to register secrets for all secret references in a stack, use the
following command:

```shell
zenml stack register-secrets [<STACK_NAME>]
```

Administering your Pipelines
----------------------------

ZenML provides several CLI commands to help you administer your pipelines and
pipeline runs.

After you have run some pipelines by by executing the corresponding Python 
scripts, you can list all pipelines via:

```bash
zenml pipeline list
```

Since every pipeline run creates a new pipeline by default, you might
occasionally want to delete a pipeline, which you can do via:

```bash
zenml pipeline delete <PIPELINE_NAME>
```

This will delete the pipeline and change all corresponding pipeline runs to
become unlisted (not linked to any pipeline).

To list all pipeline runs that you have executed, use:

```bash
zenml pipeline runs list
```

To delete a pipeline run, use:

```bash
zenml pipeline runs delete <PIPELINE_RUN_NAME_OR_ID>
```

Each pipeline run automatically saves its artifacts in the artifact store. To
list all artifacts that have been saved, use:

```bash
zenml artifact list
```

The metadata of an artifact can only be deleted if it is no longer linked to
any pipeline runs, i.e., if the run that produced the artifact and all runs that
cached any of its steps have been deleted.

To delete all artifacts that are no longer linked to any pipeline runs, use:

```bash
zenml artifact prune
```

To delete a specific artifact, use:

```bash
zenml artifact delete <ARTIFACT_NAME_OR_ID>
```

Managing the local ZenML Dashboard
----------------------------------

The ZenML dashboard is a web-based UI that allows you to visualize and navigate
the stack configurations, pipelines and pipeline runs tracked by ZenML among
other things. You can start the ZenML dashboard locally by running the following
command:

```bash
zenml up
```

This will start the dashboard on your local machine where you can access it at
the URL printed to the console. If you want to stop the dashboard, simply run:

```bash
zenml down
```

The `zenml up` command has a few additional options that you can use to
customize how the ZenML dashboard is running.

By default, the dashboard is started as a background process. On some operating
systems, this capability is not available. In this case, you can use the
`--blocking` flag to start the dashboard in the foreground:

```bash
zenml up --blocking
```

This will block the terminal until you stop the dashboard with CTRL-C.

Another option you can use, if you have Docker installed on your machine, is to
run the dashboard in a Docker container. This is useful if you don't want to
install all the Zenml server dependencies on your machine. To do so, simply run:

```bash
zenml up --docker
```

The TCP port and the host address that the dashboard uses to listen for
connections can also be customized. Using an IP address that is not the default
`localhost` or 127.0.0.1 is especially useful if you're running some type of
local ZenML orchestrator, such as the k3d Kubeflow orchestrator or Docker
orchestrator, that cannot directly connect to the local ZenML server.

For example, to start the dashboard on port 9000 and have it listen
on all locally available interfaces on your machine, run:

```bash
zenml up --port 9000 --ip-address 0.0.0.0
```

Note that the above 0.0.0.0 IP address also exposes your ZenML dashboard
externally through your public interface. Alternatively, you can choose an
explicit IP address that is configured on one of your local interfaces, such as
the Docker bridge interface, which usually has the IP address `172.17.0.1`:

```bash
zenml up --port 9000 --ip-address 172.17.0.1
```

Managing the global configuration
---------------------------------

The ZenML global configuration CLI commands cover options such as enabling or
disabling the collection of anonymous usage statistics, changing the logging
verbosity and configuring your ZenML client to connect to a remote database or
ZenML server.

In order to help us better understand how the community uses ZenML, the library
reports anonymized usage statistics. You can always opt-out by using the CLI
command:

```bash
zenml analytics opt-out
```

If you want to opt back in, use the following command:

```bash
zenml analytics opt-in
```

The verbosity of the ZenML client output can be configured using the
``zenml logging`` command. For example, to set the verbosity to DEBUG, run:

```bash
zenml logging set-verbosity DEBUG
```

The ZenML client can be configured to connect to a remote database or ZenML
server with the `zenml connect` command. If no arguments are supplied, ZenML
will attempt to connect to the last ZenML server deployed from the local host
using the 'zenml deploy' command:

```bash
zenml connect
```

To connect to a ZenML server, you can either pass the configuration as command
line arguments or as a YAML file:

```bash
zenml connect --url=https://zenml.example.com:8080 --username=admin --no-verify-ssl
```

or

```bash
zenml connect --config=/path/to/zenml_server_config.yaml
```

The YAML file should have the following structure when connecting to a ZenML
server:

```yaml
url: <The URL of the ZenML server>
username: <The username to use for authentication>
password: <The password to use for authentication>
verify_ssl: |
   <Either a boolean, in which case it controls whether the
   server's TLS certificate is verified, or a string, in which case it
   must be a path to a CA certificate bundle to use or the CA bundle
   value itself>
```

Example of a ZenML server YAML configuration file:

```yaml
url: https://ac8ef63af203226194a7725ee71d85a-7635928635.us-east-1.elb.amazonaws.com/zenml
username: admin
password: Pa$$word123
verify_ssl: |
-----BEGIN CERTIFICATE-----
MIIDETCCAfmgAwIBAgIQYUmQg2LR/pHAMZb/vQwwXjANBgkqhkiG9w0BAQsFADAT
MREwDwYDVQQDEwh6ZW5tbC1jYTAeFw0yMjA5MjYxMzI3NDhaFw0yMzA5MjYxMzI3
...
ULnzA0JkRWRnFqH6uXeJo1KAVqtxn1xf8PYxx3NlNDr9wi8KKwARf2lwm6sH4mvq
1aZ/0iYnGKCu7rLJzxeguliMf69E
-----END CERTIFICATE-----
```

Both options can be combined, in which case the command line arguments will
override the values in the YAML file. For example, it is possible and
recommended that you supply the password only as a command line argument:

```bash
zenml connect --username zenml --password=Pa@#$#word --config=/path/to/zenml_server_config.yaml
```

To disconnect from the current ZenML server and revert to using the local
default database, use the following command:

```bash
zenml disconnect
```

You can inspect the current ZenML configuration at any given time using the
following command:

```bash
zenml status
```

Example output:

```
 zenml status
Running without an active repository root.
Connected to a ZenML server: 'https://ac8ef63af203226194a7725ee71d85a-7635928635.us-east-1.elb.amazonaws.com'
The current user is: 'default'
The active project is: 'default' (global)
The active stack is: 'default' (global)
The status of the local dashboard:
              ZenML server 'local'              
┏━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ URL            │ http://172.17.0.1:9000      ┃
┠────────────────┼─────────────────────────────┨
┃ STATUS         │ ✅                          ┃
┠────────────────┼─────────────────────────────┨
┃ STATUS_MESSAGE │ Docker container is running ┃
┠────────────────┼─────────────────────────────┨
┃ CONNECTED      │                             ┃
┗━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

The ``zenml connect`` command can also be used to configure your client with
more advanced options, such as connecting directly to a local or remote SQL
database. In this case, the `--raw-config` flag must be passed to instruct the
CLI to not validate or fill in the missing configuration fields. For example,
to connect to a remote MySQL database, run:

```bash
zenml connect --raw-config --config=/path/to/mysql_config.yaml
```

with a YAML configuration file that looks like this:

```yaml
type: sql
url: mysql://<username>:<password>@mysql.database.com/<database_name>
ssl_ca: |
   -----BEGIN CERTIFICATE-----
   MIIEBjCCAu6gAwIBAgIJAMc0ZzaSUK51MA0GCSqGSIb3DQEBCwUAMIGPMQswCQYD
   VQQGEwJVUzEQMA4GA1UEBwwHU2VhdHRsZTETMBEGA1UECAwKV2FzaGluZ3RvbjEi
   MCAGA1UECgwZQW1hem9uIFdlYiBTZXJ2aWNlcywgSW5jLjETMBEGA1UECwwKQW1h
   ...
   KoZIzj0EAwMDaAAwZQIxAIqqZWCSrIkZ7zsv/FygtAusW6yvlL935YAWYPVXU30m
   jkMFLM+/RJ9GMvnO8jHfCgIwB+whlkcItzE9CRQ6CsMo/d5cEHDUu/QW6jSIh9BR
   OGh9pTYPVkUbBiKPA7lVVhre
   -----END CERTIFICATE-----

ssl_cert: null
ssl_key: null
ssl_verify_server_cert: false
```

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

A freshly created user will by default be assigned the admin role. This
behavior can be overwritten:
```bash
zenml user create USER_NAME --role guest
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

A role groups permissions to resources. Currently, there are the following
globally scoped roles to choose from: 'write', 'read' and 'me'. To create
a role, run one of the following commands:
```bash
zenml role create ROLE_NAME -p write -p read -p me
zenml role create ROLE_NAME -p read
```

To delete a role run:
```bash
zenml role delete ROLE_NAME
```

To see a list of all roles, run:
```bash
zenml role list
```

You can also update the role name and the attached permissions of a role:
```bash
zenml role update [-n <NEW_NAME>| -r <PERMISSION_TO_REMOVE>| -a <PERMISSION_TO_ADD>]
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

At any point you may inspect all available permissions:
```bash
zenml permission list
```

Deploying ZenML to the cloud
----------------------------

The ZenML CLI provides a simple way to deploy ZenML to the cloud.

Deploying cloud resources using Stack Recipes
-----------------------------------------------

Stack Recipes allow you to quickly deploy fully-fledged MLOps stacks with just
a few commands. Each recipe uses Terraform modules under the hood and once
executed can set up a ZenML stack, ready to run your pipelines!

A number of stack recipes are already available at [the `mlops-stacks` repository](https://github.com/zenml-io/mlops-stacks/). List them
using the following command:

```bash
zenml stack recipes list
```

If you want to pull any specific recipe to your local system, use the `pull`
command:

```bash
zenml stack recipe pull <stack-recipe-name>
```

If you don't specify a name, `zenml stack recipe pull` will pull all the
recipes.

If you notice any inconsistency with the locally-pulled version and the GitHub
repository, run the `pull` command with the `-y` flag to download any recent
changes.

```bash
zenml stack recipe pull <stack-recipe-name> -y
```

Optionally, you can specify the relative path at which you want to install the
stack recipe(s). Use the `-p` or `--path` flag.
```bash
zenml stack recipe pull <stack-recipe-name> --path=<PATH>
```
By default, all recipes get downloaded under a directory called
`zenml_stack_recipes`.

To deploy a recipe, use the `deploy` command. Before running deploy, review the 
`zenml_stack_recipes/<stack-recipe-name>/locals.tf` file for configuring
non-sensitive variables and the
`zenml_stack_recipes/<stack-recipe-name>/values.tfvars`
file to add sensitive information like access keys and passwords.

```bash
zenml stack recipe deploy <stack-recipe-name>
```

Running deploy without any options will create a new ZenML stack with the same
name as the stack recipe name. Use the `--stack-name` option to specify your
own name.

```bash
zenml stack recipe deploy <stack-recipe-name> --stack-name=my_stack
```

If you wish to review the stack information from the newly-generated resources
before importing, you can run `deploy` with the `--no-import` flag.

```bash
zenml stack recipe deploy <stack-recipe-name> --no-import
```
This will still create a stack YAML configuration file but will not auto-import
it. You can make any changes you want to the configuration and then run
`zenml stack import` manually.

To remove all resources created as part of the recipe, run the `destroy`
command.

```bash
zenml stack recipe destroy <stack-recipe-name>
```

To delete all the recipe files from your system, you can use the `clean`
 command.

```bash
zenml stack recipe clean
```

This deletes all the recipes from the default path where they were downloaded.
"""

from zenml.cli.annotator import *  # noqa
from zenml.cli.artifact import *  # noqa
from zenml.cli.base import *  # noqa
from zenml.cli.config import *  # noqa
from zenml.cli.example import *  # noqa
from zenml.cli.feature import *  # noqa
from zenml.cli.integration import *  # noqa
from zenml.cli.model import *  # noqa
from zenml.cli.pipeline import *  # noqa
from zenml.cli.project import *  # noqa
from zenml.cli.role import *  # noqa
from zenml.cli.secret import *  # noqa
from zenml.cli.server import *  # noqa
from zenml.cli.stack import *  # noqa
from zenml.cli.stack_components import *  # noqa
from zenml.cli.stack_recipes import *  # noqa
from zenml.cli.user_management import *  # noqa
from zenml.cli.version import *  # noqa
