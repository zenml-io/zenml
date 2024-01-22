#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
```

If you wish to use one of [the available ZenML project templates](https://docs.zenml.io/user-guide/starter-guide/using-project-templates#list-of-zenml-project-templates)
to generate a ready-to-use project scaffold in your repository, you can do so by
passing the ``--template`` option:

```bash
zenml init --template <name_of_template>
```

Running the above command will result in input prompts being shown to you. If 
you would like to rely on default values for the ZenML project template - 
you can add ``--template-with-defaults`` to the same command, like this:

```bash
zenml init --template <name_of_template> --template-with-defaults
```

If you wish to delete all data relating to your workspace from the
directory, use the ``zenml clean`` command. This will:

-  delete all pipelines, pipeline runs and associated metadata
-  delete all artifacts

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

If you want to install all integrations apart from one or multiple integrations,
use the following syntax, for example, which will install all integrations
except `feast` and `aws`:

```shell
zenml integration install -i feast -i aws
```

Uninstalling a specific integration is as simple as typing:

```bash
zenml integration uninstall INTEGRATION_NAME
```

Filtering CLI output when listing
---------------------------------

Certain CLI `list` commands allow you to filter their output. For example, all
stack components allow you to pass custom parameters to the `list` command that
will filter the output. To learn more about the available filters, a good quick
reference is to use the `--help` command, as in the following example:

```shell
zenml orchestrator list --help
```

You will see a list of all the available filters for the `list` command along
with examples of how to use them.

The `--sort_by` option allows you to sort the output by a specific field and
takes an `asc` or `desc` argument to specify the order. For example, to sort the
output of the `list` command by the `name` field in ascending order, you would
type:

```shell
zenml orchestrator list --sort_by "asc:name"
```

For fields marked as being of type `TEXT` or `UUID`, you can use the `contains`,
`startswith` and `endswith` keywords along with their particular identifier. For
example, for the orchestrator `list` command, you can use the following filter
to find all orchestrators that contain the string `sagemaker` in their name:

```shell
zenml orchestrator list --name "contains:sagemaker"
```

For fields marked as being of type `BOOL`, you can use the 'True' or 'False'
values to filter the output.

Finally, for fields marked as being of type `DATETIME`, you can pass in datetime
values in the `%Y-%m-%d %H:%M:%S` format. These can be combined with the `gte`,
`lte`, `gt` and `lt` keywords (greater than or equal, less than or equal,
greater than and less than respectively) to specify the range of the filter. For
example, if I wanted to find all orchestrators that were created after the 1st
of January 2021, I would type:

```shell
zenml orchestrator list --created "gt:2021-01-01 00:00:00"
```

This syntax can also be combined to create more complex filters using the `or`
and `and` keywords.

Customizing your Artifact Store
-------------------------------

The artifact store is where all the inputs and outputs of your pipeline
steps are stored. By default, ZenML initializes your repository with an
artifact store with everything kept on your local machine. If you wish
to register a new artifact store, do so with the ``register`` command:

```bash
zenml artifact-store register ARTIFACT_STORE_NAME --flavor=ARTIFACT_STORE_FLAVOR [--OPTIONS]
```

You can also add any labels to your stack component using the `--label` or `-l` flag:

```bash
zenml artifact-store register ARTIFACT_STORE_NAME --flavor=ARTIFACT_STORE_FLAVOR -l key1=value1 -l key2=value2
```

If you wish to list the artifact stores that have already been
registered within your ZenML workspace / repository, type:

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

You can also add any label to your stack component using the `--label` or `-l` flag:

```bash
zenml orchestrator register ORCHESTRATOR_NAME --flavor=ORCHESTRATOR_FLAVOR -l key1=value1 -l key2=value2
```

If you wish to list the orchestrators that have already been registered
within your ZenML workspace / repository, type:

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

You can also add any label to your stack component using the `--label` or `-l` flag:

```bash
zenml container-registry register REGISTRY_NAME --flavor=REGISTRY_FLAVOR -l key1=value1 -l key2=value2
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

You can also add any label to your stack component using the `--label` or `-l` flag:

```bash
zenml experiment-tracker register EXPERIMENT_TRACKER_NAME \
      --flavor=EXPERIMENT_TRACKER_FLAVOR -l key1=value1 -l key2=value2
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

You can also add any label to your stack component using the `--label` or `-l` flag:

```bash
zenml step-operator register STEP_OPERATOR_NAME --flavor STEP_OPERATOR_FLAVOR -l key1=value1 -l key2=value2
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

Deploying Stack Components
--------------------------

Stack components can be deployed directly via the CLI. You can use the `deploy`
subcommand for this. For example, you could deploy a GCP artifact store using
the following command:

```shell
zenml artifact-store deploy -f gcp -p gcp -r us-east1 -x project_id=zenml-core basic_gcp_artifact_store
```

For full documentation on this functionality, please refer to [the dedicated
documentation on stack component deploy](https://docs.zenml.io/stacks-and-components/stack-deployment/deploy-a-stack-component).

Secrets Management
------------------

ZenML offers a way to securely store secrets associated with your other
stack components and infrastructure. A ZenML Secret is a collection or grouping
of key-value pairs stored by the ZenML secrets store.
ZenML Secrets are identified by a unique name which allows you to fetch or
reference them in your pipelines and stacks.

Depending on how you set up and deployed ZenML, the secrets store keeps secrets
in the local database or uses the ZenML server your client is connected to:

* if you are using the default ZenML client settings, or if you connect your
ZenML client to a local ZenML server started with `zenml up`, the secrets store
is using the same local SQLite database as the rest of ZenML
* if you connect your ZenML client to a remote ZenML server, the
secrets are no longer managed on your local machine, but through the remote
server instead. Secrets are stored in whatever secrets store back-end the
remote server is configured to use. This can be a SQL database, one of the
managed cloud secrets management services, or even a custom back-end.

To create a secret, use the `create` command and pass the key-value pairs
as command-line arguments:

```bash
zenml secret create SECRET_NAME --key1=value1 --key2=value2 --key3=value3 ...

# Another option is to use the '--values' option and provide key-value pairs in either JSON or YAML format.
zenml secret create SECRET_NAME --values='{"key1":"value2","key2":"value2","key3":"value3"}'
```

Note that when using the previous command the keys and values will be preserved in your `bash_history` file, so
you may prefer to use the interactive `create` command instead:

```shell
zenml secret create SECRET_NAME -i
```

As an alternative to the interactive mode, also useful for values that
are long or contain newline or special characters, you can also use the special
`@` syntax to indicate to ZenML that the value needs to be read from a file:

```bash
zenml secret create SECRET_NAME \
   --aws_access_key_id=1234567890 \
   --aws_secret_access_key=abcdefghij \
   --aws_session_token=@/path/to/token.txt

# Alternatively for providing key-value pairs, you can utilize the '--values' option by specifying a file path containing
# key-value pairs in either JSON or YAML format.
zenml secret create SECRET_NAME --values=@/path/to/token.txt
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

# Another option is to use the '--values' option and provide key-value pairs in either JSON or YAML format.
zenml secret update SECRET_NAME --values='{"key1":"value2","key2":"value2","key3":"value3"}'
```

Note that when using the previous command the keys and values will be preserved in your `bash_history` file, so
you may prefer to use the interactive `update` command instead:

```shell
zenml secret update SECRET_NAME -i
```

Finally, to delete a secret, use the `delete` command:

```bash
zenml secret delete SECRET_NAME
```

Secrets can be scoped to a workspace or a user. By default, secrets
are scoped to the current workspace. To scope a secret to a user, use the
`--scope user` argument in the `register` command.

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
--------------------------------

Model deployers are stack components responsible for online model serving.
They are responsible for deploying models to a remote server. Model deployers
also act as a registry for models that are served with ZenML.

If you wish to register a new model deployer, do so with the
`register` command:

```bash
zenml model-deployer register MODEL_DEPLOYER_NAME --flavor=MODEL_DEPLOYER_FLAVOR [--OPTIONS]
```

If you wish to list the model-deployers that have already been registered
within your ZenML workspace / repository, type:

```bash
zenml model-deployer list
```

If you wish to get more detailed information about a particular model deployer
within your ZenML workspace / repository, type:

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

If you want to immediately set this newly created stack as your active stack,
simply pass along the `--set` flag.

```bash
zenml stack register STACK_NAME ... --set
```

To list the stacks that you have registered within your current ZenML
workspace, type:

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
# assuming you want to remove the image builder and the feature-store
# from your stack
zenml stack remove-component -i -f
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

Administering your Code Repositories
------------------------------------

Code repositories enable ZenML to keep track of the code version that you use
for your pipeline runs. Additionally, running a pipeline which is tracked in
a registered code repository can decrease the time it takes Docker to build images for
containerized stack components.

To register a code repository, use the following CLI
command:
```shell
zenml code-repository register <NAME> --type=<CODE_REPOSITORY_TYPE] \
   [--CODE_REPOSITORY_OPTIONS]
```

ZenML currently supports code repositories of type `github` and `gitlab`, but
you can also use your custom code repository implementation by passing the
type `custom` and a source of your repository class.

```shell
zenml code-repository register <NAME> --type=custom \
   --source=<CODE_REPOSITORY_SOURCE> [--CODE_REPOSITORY_OPTIONS]
```

The `CODE_REPOSITORY_OPTIONS` depend on the configuration necessary for the
type of code repository that you're using.

If you want to list your registered code repositories, run:
```shell
zenml code-repository list
```

You can delete one of your registered code repositories like this:
```shell
zenml code-repository delete <REPOSITORY_NAME_OR_ID>
```

Administering your Models
----------------------------

ZenML provides several CLI commands to help you administer your models and
their versions as part of the Model Control Plane.

To register a new model, you can use the following CLI command:
```bash
zenml model register --name <NAME> [--MODEL_OPTIONS]
```

To list all registered models, use:
```bash
zenml model list [MODEL_FILTER_OPTIONS]
```

To update a model, use:
```bash
zenml model update <MODEL_NAME_OR_ID> [--MODEL_OPTIONS]
```

If you would like to add or remove tags from the model, use:
```bash
zenml model update <MODEL_NAME_OR_ID> --tag <TAG> --tag <TAG> .. 
   --remove-tag <TAG> --remove-tag <TAG> ..
```

To delete a model, use:
```bash
zenml model delete <MODEL_NAME_OR_ID>
```

The CLI interface for models also helps to navigate through artifacts linked to a specific model versions.
```bash
zenml model data_artifacts <MODEL_NAME_OR_ID> [-v <VERSION>]
zenml model deployment_artifacts <MODEL_NAME_OR_ID> [-v <VERSION>]
zenml model model_artifacts <MODEL_NAME_OR_ID> [-v <VERSION>]
```

You can also navigate the pipeline runs linked to a specific model versions:
```bash
zenml model runs <MODEL_NAME_OR_ID> [-v <VERSION>]
```

To list the model versions of a specific model, use:
```bash
zenml model version list [--model-name <MODEL_NAME> --name <MODEL_VERSION_NAME> OTHER_OPTIONS]
```

To delete a model version, use:
```bash
zenml model version delete <MODEL_NAME_OR_ID> <VERSION>
```

To update a model version, use:
```bash
zenml model version update <MODEL_NAME_OR_ID> <VERSION> [--MODEL_VERSION_OPTIONS]
```
These are some of the more common uses of model version updates:
- stage (i.e. promotion)
```bash
zenml model version update <MODEL_NAME_OR_ID> <VERSION> --stage <STAGE>
```
- tags
```bash
zenml model version update <MODEL_NAME_OR_ID> <VERSION> --tag <TAG> --tag <TAG> .. 
   --remove-tag <TAG> --remove-tag <TAG> ..
```

Administering your Pipelines
----------------------------

ZenML provides several CLI commands to help you administer your pipelines and
pipeline runs.

To explicitly register a pipeline you need to point to a pipeline instance
in your Python code. Let's say you have a Python file called `run.py` and
it contains the following code:

```python
from zenml import pipeline

@pipeline
def my_pipeline(...):
   # Connect your pipeline steps here
   pass
```

You can register your pipeline like this:
```bash
zenml pipeline register my_pipeline
```

To list all registered pipelines, use:

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

If you run any of your pipelines with `pipeline.run(schedule=...)`, ZenML keeps
track of the schedule and you can list all schedules via:

```bash
zenml pipeline schedule list
```

To delete a schedule, use:

```bash
zenml pipeline schedule delete <SCHEDULE_NAME_OR_ID>
```

Note, however, that this will only delete the reference saved in ZenML and does
NOT stop/delete the schedule in the respective orchestrator. This still needs to
be done manually. For example, using the Airflow orchestrator you would have 
to open the web UI to manually click to stop the schedule from executing.

Each pipeline run automatically saves its artifacts in the artifact store. To
list all artifacts that have been saved, use:

```bash
zenml artifact list
```

Each artifact has one or several versions. To list artifact versions, use:

```bash
zenml artifact versions list
```

If you would like to rename an artifact or adjust the tags of an artifact or
artifact version, use the corresponding `update` command:

```bash
zenml artifact update <NAME> -n <NEW_NAME>
zenml artifact update <NAME> -t <TAG1> -t <TAG2> -r <TAG_TO_REMOVE>
zenml artifact version update <NAME> -v <VERSION> -t <TAG1> -t <TAG2> -r <TAG_TO_REMOVE>
```

The metadata of artifacts or artifact versions stored by ZenML can only be 
deleted once they are no longer used by any pipeline runs. I.e., an artifact
version can only be deleted if the run that produced it and all runs that used
it as an input have been deleted. Similarly, an artifact can only be deleted if
all its versions can be deleted.

To delete all artifacts and artifact versions that are no longer linked to any 
pipeline runs, use:

```bash
zenml artifact prune
```

Each pipeline run that requires Docker images also stores a build which
contains the image names used for this run. To list all builds, use:

```bash
zenml pipeline builds list
```

To delete a specific build, use:

```bash
zenml pipeline builds delete <BUILD_ID>
```

Building an image without running your Pipelines
----------------------------------

To build Docker images for your pipeline without actually running the pipeline,
use:

```bash
zenml pipeline build <PIPELINE_ID_OR_NAME>
```

To specify settings for the Docker builds, use the `--config/-c` option of the
command. For more information about the structure of this configuration file,
check out the `zenml.pipelines.base_pipeline.BasePipeline.build(...)` method.

```bash
zenml pipeline build <PIPELINE_ID_OR_NAME> --config=<PATH_TO_CONFIG_YAML>
```

If you want to build the pipeline for a stack different than your current active
stack, use the `--stack` option.
```bash
zenml pipeline build <PIPELINE_ID_OR_NAME> --stack=<STACK_ID_OR_NAME>
```


To run a pipeline that was previously registered, use:

```bash
zenml pipeline run  <PIPELINE_ID_OR_NAME>
```

To specify settings for the pipeline, use the `--config/-c` option of the
command. For more information about the structure of this configuration file,
check out the `zenml.pipelines.base_pipeline.BasePipeline.run(...)` method.

```bash
zenml pipeline run <PIPELINE_ID_OR_NAME> --config=<PATH_TO_CONFIG_YAML>
```

If you want to run the pipeline on a stack different than your current active
stack, use the `--stack` option.
```bash
zenml pipeline run <PIPELINE_ID_OR_NAME> --stack=<STACK_ID_OR_NAME>
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
the URL printed to the console. 

If you have closed the dashboard in your browser and want to open it again, 
you can run:

```bash
zenml show
```

If you want to stop the dashboard, simply run:

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
zenml connect --url=https://zenml.example.com:8080 --no-verify-ssl
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

You can open the ZenML dashboard of your currently connected ZenML server using
the following command:

```bash
zenml show

Note that if you have set your `AUTO_OPEN_DASHBOARD` environment variable to `false` then this will not open the dashboard until you set it back to `true`.
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
The active workspace is: 'default' (global)
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

Managing users and workspaces
-------------------------------------------

When using the ZenML service, you can manage permissions by managing users and
workspaces and using the CLI.
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


Managing service accounts
-------------------------

ZenML supports the use of service accounts to authenticate clients to the
ZenML server using API keys. This is useful for automating tasks such as
running pipelines or deploying models.

To create a new service account, run:

```bash
zenml service-account create SERVICE_ACCOUNT_NAME
```

This command creates a service account and an API key for it. The API key is
displayed as part of the command output and cannot be retrieved later. You can
then use the issued API key to connect your ZenML client to the server with the
CLI:

```bash
zenml connect --url https://... --api-key <API_KEY>
```

or by setting the `ZENML_STORE_URL` and `ZENML_STORE_API_KEY` environment
variables when you set up your ZenML client for the first time: 

```bash
export ZENML_STORE_URL=https://...
export ZENML_STORE_API_KEY=<API_KEY>
```

To see all the service accounts you've created and their API keys, use the
following commands:

```bash
zenml service-account list
zenml service-account api-key <SERVICE_ACCOUNT_NAME> list
```

Additionally, the following command allows you to more precisely inspect one of
these service accounts and an API key:

```bash
zenml service-account describe <SERVICE_ACCOUNT_NAME>
zenml service-account api-key <SERVICE_ACCOUNT_NAME> describe <API_KEY_NAME>
```

API keys don't have an expiration date. For increased security, we recommend
that you regularly rotate the API keys to prevent unauthorized access to your
ZenML server. You can do this with the ZenML CLI:

```bash
zenml service-account api-key <SERVICE_ACCOUNT_NAME> rotate <API_KEY_NAME>
```

Running this command will create a new API key and invalidate the old one. The
new API key is displayed as part of the command output and cannot be retrieved
later. You can then use the new API key to connect your ZenML client to the
server just as described above.

When rotating an API key, you can also configure a retention period for the old
API key. This is useful if you need to keep the old API key for a while to
ensure that all your workloads have been updated to use the new API key. You can
do this with the `--retain` flag. For example, to rotate an API key and keep the
old one for 60 minutes, you can run the following command:

```bash
zenml service-account api-key <SERVICE_ACCOUNT_NAME> rotate <API_KEY_NAME> \
      --retain 60
```

For increased security, you can deactivate a service account or an API key using
one of the following commands:

```
zenml service-account update <SERVICE_ACCOUNT_NAME> --active false
zenml service-account api-key <SERVICE_ACCOUNT_NAME> update <API_KEY_NAME> \
      --active false
```

Deactivating a service account or an API key will prevent it from being used to
authenticate and has immediate effect on all workloads that use it.

To permanently delete an API key for a service account, use the following
command:

```bash
zenml service-account api-key <SERVICE_ACCOUNT_NAME> delete <API_KEY_NAME>
```

Deploying ZenML to the cloud
----------------------------

The ZenML CLI provides a simple way to deploy ZenML to the cloud. Simply run

```bash
zenml deploy
```

You will be prompted to provide a name for your deployment and details like what
cloud provider you want to deploy to, in addition to the username, password, and
email you want to set for the default user — and that's it! It creates the
database and any VPCs, permissions, and more that are needed.

In order to be able to run the deploy command, you should have your cloud
provider's CLI configured locally with permissions to create resources like
MySQL databases and networks.

Interacting with the ZenML Hub
------------------------------

The ZenML Hub is a central location for discovering and sharing third-party 
ZenML code, such as custom integrations, components, steps, pipelines, 
materializers, and more. 
You can browse the ZenML Hub at [https://hub.zenml.io](https://hub.zenml.io).

The ZenML CLI provides various commands to interact with the ZenML Hub:

- Listing all plugins available on the Hub:
```bash
zenml hub list
```

- Installing a Hub plugin:
```bash
zenml hub install
```
Installed plugins can be imported via `from zenml.hub.<plugin_name> import ...`. 


- Uninstalling a Hub plugin:
```bash
zenml hub uninstall
```

- Cloning the source code of a Hub plugin (without installing it):
```bash
zenml hub clone
```
This is useful, e.g., for extending an existing plugin or for getting the 
examples of a plugin.

- Submitting/contributing a plugin to the Hub (requires login, see below):
```bash
zenml hub submit
```
If you are unsure about which arguments you need to set, you can run the
command in interactive mode:
```bash
zenml hub submit --interactive
```
This will ask for and validate inputs one at a time.

- Logging in to the Hub:
```bash
zenml hub login
```

- Logging out of the Hub:
```bash
zenml hub logout
```

- Viewing the build logs of a plugin you submitted to the Hub:
```bash
zenml hub logs
```
"""

from zenml.cli.version import *  # noqa
from zenml.cli.annotator import *  # noqa
from zenml.cli.artifact import *  # noqa
from zenml.cli.authorized_device import *  # noqa
from zenml.cli.base import *  # noqa
from zenml.cli.code_repository import *  # noqa
from zenml.cli.config import *  # noqa
from zenml.cli.downgrade import *  # noqa
from zenml.cli.feature import *  # noqa
from zenml.cli.hub import *  # noqa
from zenml.cli.integration import *  # noqa
from zenml.cli.model import *  # noqa
from zenml.cli.model_registry import *  # noqa
from zenml.cli.pipeline import *  # noqa
from zenml.cli.secret import *  # noqa
from zenml.cli.served_model import *  # noqa
from zenml.cli.server import *  # noqa
from zenml.cli.service_accounts import *  # noqa
from zenml.cli.service_connectors import *  # noqa
from zenml.cli.stack import *  # noqa
from zenml.cli.stack_components import *  # noqa
from zenml.cli.stack_recipes import *  # noqa
from zenml.cli.user_management import *  # noqa
from zenml.cli.workspace import *  # noqa
from zenml.cli.tag import *  # noqa
