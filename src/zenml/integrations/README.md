# Implementing a New Integration

One of the main goals of ZenML is to find some semblance of order in the 
ever-growing MLOps landscape. ZenML already provides 
[numerous integrations](https://zenml.io/integrations) into many popular tools, 
and allows you to extend ZenML in order to fill in any gaps that are remaining.

However, what if you want to make your extension of ZenML part of the main 
codebase, to share it with others? If you are such a person, e.g., a tooling 
provider in the ML/MLOps space, or just want to contribute a tooling integration 
to ZenML, this guide is intended for you.

## Step 1: Categorize your integration

In order to create a new integration into ZenML, you would need to first find 
the categories that your integration belongs to. The list of categories can be 
found on [this page](https://docs.zenml.io/getting-started/introduction).

Note that one integration may belong to different categories: For example, the 
cloud integrations (AWS/GCP/Azure) contain container registries, artifact 
stores, orchestrators etc.

## Step 2: Create individual stack component flavors

Each category selected above would correspond to a 
[stack component flavor](https://docs.zenml.io/getting-started/introduction). 
You can now start developing these individual stack component flavors by 
following the detailed instructions on each stack component page.

Before you package your new components into an integration, you may want to 
first register them with the `zenml <STACK_COMPONENT> flavor register` command 
and use/test them as a regular custom flavor. E.g., when 
[developing an orchestrator](https://docs.zenml.io/getting-started/introduction) 
you can use:

```
zenml orchestrator flavor register <flavor.my_flavor.MyOrchestratorFlavor>
```

See the docs on extensibility of the different components 
[here ](https://docs.zenml.io/getting-started/introduction) or get inspired 
by the many integrations that are already implemented, for example the mlflow 
[experiment tracker](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/mlflow/experiment_trackers/mlflow_experiment_tracker.py).

## Step 3: Integrate into the ZenML repo

You can now start the process of including your integration into the base ZenML 
package. Follow this checklist to prepare everything:

### Clone Repo

Once your stack components work as a custom flavor, you can now 
[clone the main zenml repository](https://github.com/zenml-io/zenml) and follow 
the [contributing guide](https://github.com/zenml-io/zenml/blob/main/CONTRIBUTING.md) 
to set up your local environment for develop.

### **Create the integration directory**

All integrations live within [`src/zenml/integrations/`](https://github.com/zenml-io/zenml/tree/main/src/zenml/integrations) 
in their own sub-folder. You should create a new folder in this directory with 
the name of your integration.


### Example integration directory structure

```
/src/zenml/integrations/                        <- ZenML integration directory
    <example-integration>                       <- Root integration directory
        |
        ├── artifact-stores                     <- Separated directory for  
        |      ├── __init_.py                      every type
        |      └── <example-artifact-store>     <- Implementation class for the  
        ├── orchestrators                          artifact store flavor
        |      ├── __init_.py
        |      └── <example-orchestrator>       <- Implementation class for the  
        |                                          orchestrator flavor
        ├── flavors 
        |      ├── __init_.py 
        |      ├── <example-artifact-store-flavor>  <- Config class and flavor
        |      └── <example-orchestrator-flavor>    <- Config class and flavor
        |
        └── __init_.py                          <- Integration class 
```

### Define the name of your integration in constants

In [`zenml/integrations/constants.py`](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/constants.py), add:

```python
EXAMPLE_INTEGRATION = "<name-of-integration>"
```

This will be the name of the integration when you run:

```shell
 zenml integration install <name-of-integration>
```

### Create the integration class \_\_init\_\_.py

In `src/zenml/integrations/<YOUR_INTEGRATION>/init__.py` you must now 
create an new class, which is a subclass of the `Integration` class, set some 
important attributes (`NAME` and `REQUIREMENTS`), and overwrite the `flavors` 
class method.

```python
from zenml.integrations.constants import <EXAMPLE_INTEGRATION>
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

# This is the flavor that will be used when registering this stack component
#  `zenml <type-of-stack-component> register ... -f example-orchestrator-flavor`
EXAMPLE_ORCHESTRATOR_FLAVOR = <"example-orchestrator-flavor">

# Create a Subclass of the Integration Class
class ExampleIntegration(Integration):
    """Definition of Example Integration for ZenML."""

    NAME = <EXAMPLE_INTEGRATION>
    REQUIREMENTS = ["<INSERT PYTHON REQUIREMENTS HERE>"]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the <EXAMPLE> integration."""
        from zenml.integrations.<example_flavor> import <ExampleFlavor>
        
        return [<ExampleFlavor>]
        
ExampleIntegration.check_installation() # this checks if the requirements are installed
```

Have a look at the [MLflow Integration](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/mlflow/__init__.py) 
as an example for how it is done.

### Import in all the right places

The Integration itself must be imported within 
[`src/zenml/integrations/__init__.py`](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/\_\_init\_\_.py).

## Step 4: Create a PR and celebrate :tada:

You can now [create a PR](https://github.com/zenml-io/zenml/compare) to ZenML 
and wait for the core maintainers to take a look. Thank you so much for your 
contribution to the code-base, rock on!
