---
description: ZenML pipelines are fully-aware of external, longer-lived services.
---

# Interact with external services

ZenML interacts with external systems (e.g. prediction services, monitoring systems, visualization services) with a so-called `Service` abstraction. 
The concrete implementation of this abstraction deals with functionality concerning the life-cycle management and tracking of an external service (e.g. process, container, 
Kubernetes deployment etc.).

One concrete example of a `Service` is the built-in `LocalDaemonService`, a service represented by a local daemon
process. This extends the base service class with functionality concerning the life-cycle management and tracking
of external services implemented as local daemon processes.

Services can be passed through steps like any other object, and used to interact with the external systems that
they represent:

```python
@step
def my_step(my_service: MyService) -> ...:
    if not my_service.is_running:
        my_service.start() # starts service
    my_service.stop()  # stops service
```

You can see full examples of using services here:

* Visualizing training with tensorboard with the [Kubeflow tensorboard example](https://github.com/zenml-io/zenml/tree/main/examples/kubeflow).
* Continuous training and continuous deployment setting with the [MLflow deployment example](https://github.com/zenml-io/zenml/tree/main/examples/mlflow_deployment).
* Continuous training and continuous deployment setting with the [Seldon deployment example](https://github.com/zenml-io/zenml/tree/main/examples/seldon_deployment).

## Examples services

One concrete example of a `Service` implementation is the `TensorboardService`.
It enables visualizing [Tensorboard](https://www.tensorflow.org/tensorboard) logs easily by managing a local Tensorboard server.

```python
service = TensorboardService(
    TensorboardServiceConfig(
        logdir=logdir,
    )
)

# start the service
service.start(timeout=20)

# stop the service
service.stop()
```

This couples nicely with the `TensorboardVisualizer` to visualize Tensorboard logs.

Other examples of Services can be found in the [continuous training and deployment guide](continuous-training-and-deployment.md).