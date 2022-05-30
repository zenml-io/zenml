# Implementing a New Integration

When implementing a new integration for a stack component 
(or materializer/visualizer) there are quite a few steps to complete.
Here's a small guide to get you going:


### 1. Create `src/zenml/integrations/<name-of-integration>`
    All integrations live within `src/zenml/integrations/` in their own 
    subfolder.

### 2. Define the name of your integration in zenml.integrations.constants.py
    
```python
EXAMPLE_INTEGRATION = "<name-of-integration>"
```

This will be the name of the integration when you run:

```shell
 zenml integration install <name-of-integration>
```

Or when you specify pipeline requirements:

```python
from zenml.pipelines import pipeline
from zenml.integrations.constants import <EXAMPLE_INTEGRATION>

@pipeline(required_integrations=[<EXAMPLE_INTEGRATION>])
def custom_pipeline():
    ...
```

### 3. Create integration in `src/zenml/integrations/<name-of-integration>/__init__.py`

To create an integration you first need to subclass the `Integration` class, 
set some important attributes (`NAME` and `REQUIREMENTS`) and overwrite the 
`flavors` class method.

```python
from typing import List

from zenml.enums import StackComponentType
from zenml.integrations.constants import <EXAMPLE_INTEGRATION>
from zenml.integrations.integration import Integration
from zenml.zen_stores.models import FlavorWrapper

# This is the flavor that will be used when registering this stack component
#  `zenml <type-of-stack-component> register ... -f example-orchestrator-flavor`
EXAMPLE_ORCHESTRATOR_FLAVOR = <"example-orchestrator-flavor">

# Create a Subclass of the Integration Class
class ExampleIntegration(Integration):
    """Definition of Example Integration for ZenML."""

    NAME = <EXAMPLE_INTEGRATION>
    REQUIREMENTS = ["<INSERT PYTHON REQUIREMENTS HERE>"]

    @classmethod
    def flavors(cls) -> List[FlavorWrapper]:
        """Declare the stack component flavors for the <EXAMPLE> integration."""
        return [
            # Create a FlavorWrapper for each Stack Component this Integration implements
            FlavorWrapper(
                name=EXAMPLE_ORCHESTRATOR_FLAVOR,    
                source="<path.to.the.implementation.of.the.component",      # Give the source of the component implementation
                type=StackComponentType.<TYPE-OF-STACK-COMPONENT>,      # Define which component is implemented
                integration=cls.NAME,
            )
        ]

ExampleIntegration.check_installation() # this checks if the requirements are installed
```

Have a look at the MLFlow [Integration](mlflow/__init__.py) 
as an example for how it is done.

### 4. Create the implementation(s)

Each Integration can have implementations for multiple ZenML components. 
Generally the outer repository structure 
`src/zenml/<stack-component>/<base-component-impl.py` is reflected inside the 
integration folder: `integrations/<name-of-integration>/<stack-component>/<custom-component-impl.py`

Here you'll be able to extend and build out the implementation. See the docs on 
extensibility of the different components [here](https://docs.zenml.io/extending-zenml) or get inspired by the many 
integrations that are already implemented, for example the 
[mlflow experiment tracker](mlflow/experiment_trackers/mlflow_experiment_tracker.py)

### 5. Import in all the right places
The Integration itself must be imported within the integrations 
[`__init__.py`](__init__.py)

The Implementation of the Stack Component, Materializer or Visualizer needs to 
be imported within `src/zenml/integrations/<name-of-integration>/<specifc-component>/__init__.py`
