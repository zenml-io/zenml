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

## Deploying on a Cortex GCP cluster
This example will utilize a `TrainingPipeline` with a `CortexDeployer` Step to deploy a trained model to a 
cluster end-point right after training.

### Pre-requisites
Then you can clone the repo and initialize a zenml repo:
```bash
git clone https://github.com/maiot-io/zenml.git
```

Before continuing, either install the [zenml pip package](https://pypi.org/project/zenml/) or to install it [from the cloned repo](../../zenml/README.md). 
In both cases, make sure to install the cortex extension (e.g. `pip install zenml[cortex]`)

```
zenml init
cd examples/cortex
```

And export the required configuration variables:
```bash
export CORTEX_ENV='gcp'
export CORTEX_ENDPOINT_NAME='myawesomemodel'
export GCP_BUCKET='gs://mybucket'  # to be used as the artifact store
```

In order to run this example, make sure you have the cortex cluster up.

```python
cortex cluster-gcp up
```
Then accept all the defaults, most important of which is the name of the `env`, which should be equal to the 
`CORTEX_ENV` env variable above. This will default to `gcp`.

You can also change this according to your requirements. Follow any of the steps outlined in the [Cortex docs](https://docs.cortex.dev/clusters/gcp/install).



### Run the script
Now we're ready. Execute:

```bash
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
Get rid of cortex references:
```bash
cortex delete $CORTEX_ENPOINT_NAME
cortex cluster-gcp down
```

Delete the zenml references:

```python
cd ../..
rm -r .zenml
rm -r pipelines
```

## Caveats
Currently, the `CortexDeployer` step only works with a local orchestrator backend. Also the `cortex` integration 
currently does not work with the `gcp` integration. It is also important to note that this also only works with the 
a Google Cloud Bucket as the artifact store, because the model needs to be available to the cluster and a local artifact 
store would not work.

Let us know via [Slack](https://zenml.io/slack-invite) if you would like to see more backends!

## Next Steps
[Cortex](https://github.com/cortexlabs/cortex) makes it super easy to reproducibly deploy your models straight to 
an end-point in your cluster. A big thank you to the  cortex team for helping out in this integration and example!

Try using different [Workloads](https://docs.cortex.dev/workloads/batch) and [Predictors](https://docs.cortex.dev/workloads/realtime/predictors) in the 
cortex config passed to the `CortexDeployer` step. You can set up batch workloads, split traffic on your cluster and lots more.