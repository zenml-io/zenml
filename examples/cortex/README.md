# Reproducible deployments with ZenML and Cortex
The `CortexDeployer` step makes it easy to deploy models on a kubernetes cluster. It uses the [Cortex](https://github.com/cortexlabs/cortex) 
integration to achieve this.

## Adding a deployment step
The pattern to add a deployment step is:

```python
pipeline.add_deployment(
    DeployerStep(...)
)
```

## Running on Google Cloud Platform and Dataflow
This example utilize [Google Cloud Dataflow](https://cloud.google.com/dataflow) as the backend to 
distribute certain Steps in the quickstart pipeline example. In order to run, follow these steps:

### Pre-requisites
In order to run this example, make sure you have the cortex cluster up.

```python
cortex cluster up
```

### Run the project
Now we're ready. Execute:

```bash
export CORTEX_ENDPOINT_NAME='myawesomemodel'
python run.py
```

### Check deployment
To check status of endpoint:
```bash
cortex get $CORTEX_ENPOINT_NAME
```
To see logs:
```bash
cortex logs $CORTEX_ENPOINT_NAME
```

### Let's hit the endpoint
```bash

```

### Clean up
Delete the zenml references.

```python
cd ../..
rm -r .zenml
rm -r pipelines
```

## Caveat
Currently, the `CortexDeployer` step only works with a local orchestrator backend.

## Next Steps
Cortex makes it super easy to deploy your models straight to end-points in your cluster.