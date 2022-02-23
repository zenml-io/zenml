---
description: Implement end-to-end ML workflows with Continuous Training and Deployment.
---

# Continuous Training and Continuous Deployment (CT/CD)

As an organization develops across the [MLOps maturity model](https://docs.microsoft.com/en-us/azure/architecture/example-scenario/mlops/mlops-maturity-model), 
the terms Continuous Training and Continuous Deployment (CT/CD) get more relevant.

- Continuous Training refers to the paradigm where a team deploy training pipelines that run automatically to train models on
new (fresh) data. (e.g. Every two weeks, take the latest data from an API, and train a new model on it.)
- Continuous Deployment refers to the paradigm where a newly trained models are automatically deployed to a prediction 
service/server, when a criterion in production is fulfilled (e.g. if a trained model has a certain accuracy, or overall performs better than the previous one, deploy it in production.)

ZenML allows both paradigms with the [Schedules](../introduction/core-concepts.md) and [Services](../introduction/core-concepts.md).

## Setting a pipeline schedule for Continuous Training (CT)

ZenML supports running pipelines on a schedule as follows:

```python
import datetime
from datetime import timedelta
from zenml.pipelines import Schedule

# Create a schedule to run a pipeline every minute for the next ten minutes
schedule = Schedule(
    start_time=datetime.now(),
    end_time=datetime.now() + timedelta(minutes=10),
    interval_second=60,
)

# Run the pipeline on a schedule
my_pipeline(
    ...  # steps
).run(schedule=schedule)
```

The above deploys a pipeline, potentially on a [production stack](cloud-pipelines)), on a defined schedule. If the 
pipeline has a well-defined data loading/importing step, then 

## Interacting with services for Continuous Deployment (CD)

ZenML interacts with external systems like prediction servers with a so-called `Service` object. These object implement
generic functionality concerning the life-cycle management and tracking of an external service (e.g. process, container, 
Kubernetes deployment etc.).

One concrete example of a `Service` is the built-in `LocalDaemonService`, a service represented by a local daemon
process. This extends the base service class with functionality concerning the life-cycle management and tracking
of external services implemented as local daemon processes.

Another concrete example of a `Service` implementation -- this time a prediction service provided by a ZenML integration -- is the `MLFlowDeploymentService`. It enables serving models with MLflow deployment server instances, also running
locally as daemon processes.

Services can be passed through steps like any other object, and used to interact with the external systems that
they represent:

```python
@step
def my_step(my_service: MyService) -> ...:
    if not my_service.is_running:
        my_service.start() # starts service
    my_service.stop()  # stops service
```

You can see a concrete example of using Services in a continuous training and continuous deployment setting with the 
[MLflow deployment example](https://github.com/zenml-io/zenml/tree/main/examples/mlflow_deployment).