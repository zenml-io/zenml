---
description: Orchestrating the run pipelines
---

The orchestrator is one of the most critical components of your stack, as it
defines where the actual pipeline job runs. It controls how and where each
individual step within a pipeline is executed. Therefore, the orchestrator can
be used to great effect to scale jobs into production.

{% hint style="warning" %}
Before reading this chapter, make sure that you are familiar with the
concept of [stacks, stack components and their flavors](./introduction.md).  
{% endhint %}

## Base Implementation

ZenML aims to enable orchestration with any orchestration tool. This is where
the `BaseOrchestrator` comes into play. It abstracts many of the ZenML specific
details away from the actual implementation and exposes a simplified interface:

1. As it is the base class for a specific type of StackComponent,
   it inherits from the StackComponent class. This sets the TYPE
   variable to the specific StackComponentType. 
2. The FLAVOR class variable needs to be set in the particular sub-class as it 
   is meant to indentify the implementation flavor of the particular 
   orchestrator.
3. Lastly, the base class features one `abstractmethod`s: 
   `prepare_or_run_pipeline`. In the implementation of every
   `Orchestrator` flavor, it is required to define this method with respect
   to the flavor at hand.

Putting all these considerations together, we end up with the following
(simplified) implementation:

```python
from abc import abstractmethod, ABC
from typing import Any, ClassVar, List

from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline

from zenml.enums import StackComponentType
from zenml.stack import StackComponent
from zenml.steps import BaseStep


class BaseOrchestrator(StackComponent, ABC):
    """Base class for all orchestrators. ..."""

    # --- Class variables ---
    TYPE: ClassVar[StackComponentType] = StackComponentType.ORCHESTRATOR
    

    @abstractmethod
    def prepare_or_run_pipeline(
        self,
        sorted_steps: List[BaseStep],
        pipeline: "BasePipeline",
        pb2_pipeline: Pb2Pipeline,
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> Any:
       """
       Prepares and runs the pipeline outright or returns an intermediate
       pipeline representation that gets deployed.
       """
```

## List of available artifact stores

Out of the box, ZenML comes with a `LocalOrchestrator` implementation, which
is a simple implementation for running your pipelines locally.

Moreover, additional orchestrators can be found in specific `integrations`
modules, such as the `AirflowOrchestrator` in the `airflow` integration and the
`KubeflowOrchestrator` in the `kubeflow` integration.

|                       | Flavor    | Integration |
|-----------------------|-----------|-------------|
| LocalOrchestrator     | local     | `built-in`  |
| AirflowOrchestrator   | airflow   | airflow     |
| KubeflowOrchestrator  | kubeflow  | kubeflow    |

If you would like to see the available flavors for artifact stores, you can
use the command:

```shell
zenml orchestrator flavor list
```

## Build your own custom orchestrator

If you want to create your own custom flavor for an artifact store, you can 
follow the following steps:

1. Create a class which inherits from the `BaseOrchestrator`.
2. Define the `FLAVOR` class variable.
3. Implement the `abstactmethod`s based on your desired orchestrator.

Once you are done with the implementation, you can register it through the CLI 
as:

```shell
zenml orchestrator flavor register <THE-SOURCE-PATH-OF-YOUR-ORCHESTRATOR>
```