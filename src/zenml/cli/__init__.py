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

.. code:: bash

   zenml version

If you ever need more information on exactly what a certain command will
do, use the ``--help`` flag attached to the end of your command string.

For example, to get a sense of all of the commands available to you
while using the ``zenml`` command, type:

.. code:: bash

   zenml --help

If you were instead looking to know more about a specific command, you
can type something like this:

.. code:: bash

   zenml metadata-store register --help

This will give you information about how to register a metadata store.
(See below for more on that).

Beginning a Project
-------------------

In order to start working on your project, initialize a ZenML repository
within your current directory with ZenML’s own config and resource management
tools:

.. code:: bash

   zenml init

This is all you need to begin using all the MLOps goodness that ZenML
provides!

By default, ``zenml init`` will install its own hidden ``.zen`` folder
inside the current directory from which you are running the command.
You can also pass in a directory path manually using the
``--repo_path`` option:

.. code:: bash

   zenml init --repo_path /path/to/dir

If you wish to specify that you do not want analytics to be transmitted
back to ZenML about your usage of the tool, pass in ``False`` to the
``--analytics_opt_in`` option:

.. code:: bash

   zenml init --analytics_opt_in false

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

.. code:: bash

   zenml example list

If you want more detailed information about a specific example, use the
``info`` subcommand in combination with the name of the example, like
this:

.. code:: bash

   zenml example info quickstart

If you want to pull all the examples into your current working directory
(wherever you are executing the ``zenml`` command from in your
terminal), the CLI will create a ``zenml_examples`` folder for you if it
doesn’t already exist whenever you use the ``pull`` subcommand. The
default is to copy all the examples, like this:

.. code:: bash

   zenml example pull

If you’d only like to pull a single example, add the name of that
example (for example, ``quickstart``) as an argument to the same
command, as follows:

.. code:: bash

   zenml example pull quickstart

If you would like to force-redownload the examples, use the ``--force``
or ``-f`` flag as in this example:

.. code:: bash

   zenml example pull --force

This will redownload all the examples afresh, using the same version of
ZenML as you currently have installed. If for some reason you want to
download examples corresponding to a previous release of ZenML, use the
``--version`` or ``-v`` flag to specify, as in the following example:

.. code:: bash

   zenml example pull --force --version 0.3.8

If you wish to run the example, allowing the ZenML CLI to do the work of setting
up whatever dependencies are required, use the ``run`` subcommand:

.. code:: bash

   zenml example run quickstart

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
artifacts are all tracked within the metadata store. By default ZenML
initializes your repository with a metadata store kept on your local
machine. If you wish to register a new metadata store, do so with the
``register`` command:

.. code:: bash

   zenml metadata-store register METADATA_STORE_NAME --type METADATA_STORE_TYPE [--OPTIONS]

If you wish to list the metadata stores that have already been
registered within your ZenML project / repository, type:

.. code:: bash

   zenml metadata-store list

If you wish to delete a particular metadata store, pass the name of the
metadata store into the CLI with the following command:

.. code:: bash

   zenml metadata-store delete METADATA_STORE_NAME

Customizing your Artifact Store
-------------------------------

The artifact store is where all the inputs and outputs of your pipeline
steps are stored. By default, ZenML initializes your repository with an
artifact store with everything kept on your local machine. If you wish
to register a new artifact store, do so with the ``register`` command:

.. code:: bash

   zenml artifact-store register ARTIFACT_STORE_NAME --type ARTIFACT_STORE_TYPE [--OPTIONS]

If you wish to list the artifact stores that have already been
registered within your ZenML project / repository, type:

.. code:: bash

   zenml artifact-store list

If you wish to delete a particular artifact store, pass the name of the
artifact store into the CLI with the following command:

.. code:: bash

   zenml artifact-store delete ARTIFACT_STORE_NAME

Customizing your Orchestrator
-----------------------------

An orchestrator is a special kind of backend that manages the running of
each step of the pipeline. Orchestrators administer the actual pipeline
runs. By default, ZenML initializes your repository with an orchestrator
that runs everything on your local machine.

If you wish to register a new orchestrator, do so with the ``register``
command:

.. code:: bash

   zenml orchestrator register ORCHESTRATOR_NAME --type ORCHESTRATOR_TYPE [--ORCHESTRATOR_OPTIONS]

If you wish to list the orchestrators that have already been registered
within your ZenML project / repository, type:

.. code:: bash

   zenml orchestrator list

If you wish to delete a particular orchestrator, pass the name of the
orchestrator into the CLI with the following command:

.. code:: bash

   zenml orchestrator delete ORCHESTRATOR_NAME

Customizing your Container Registry
-----------------------------------

The container registry is where all the images that are used by a
container-based orchestrator are stored. By default, a default ZenML local stack
will not register a container registry. If you wish to register a new container
registry, do so with the `register` command:

```bash
zenml container-registry register REGISTRY_NAME --type REGISTRY_TYPE [--REGISTRY_OPTIONS]
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
By default (without a specific registry name passed in) it will describe the
active or currently used container registry:

```bash
zenml container-registry describe [REGISTRY_NAME]
```

To delete a container registry (and all of its contents), use the `delete`
command:

```bash
zenml container-registry delete
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

.. code:: bash

   zenml stack register STACK_NAME \
       -m METADATA_STORE_NAME \
       -a ARTIFACT_STORE_NAME \
       -o ORCHESTRATOR_NAME

Each corresponding argument should be the name you passed in as an
identifier for the artifact store, metadata store or orchestrator when
you originally registered it.

To list the stacks that you have registered within your current ZenML
project, type:

.. code:: bash

   zenml stack list

To delete a stack that you have previously registered, type:

.. code:: bash

   zenml stack delete STACK_NAME

By default, ZenML uses a local stack whereby all pipelines run on your
local computer. If you wish to set a different stack as the current
active stack to be used when running your pipeline, type:

.. code:: bash

   zenml stack set STACK_NAME

This changes a configuration property within your local environment.

To see which stack is currently set as the default active stack, type:

.. code:: bash

   zenml stack get

"""

from zenml.cli.artifact_store import *  # noqa
from zenml.cli.base import *  # noqa
from zenml.cli.config import *  # noqa
from zenml.cli.container_registry import *  # noqa
from zenml.cli.example import *  # noqa
from zenml.cli.integration import *  # noqa
from zenml.cli.metadata_store import *  # noqa
from zenml.cli.orchestrator import *  # noqa
from zenml.cli.pipeline import *  # noqa
from zenml.cli.stack import *  # noqa
from zenml.cli.version import *  # noqa
