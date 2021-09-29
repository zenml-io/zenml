# Get up and running quickly
This example first runs a `TrainingPipeline` to train a Tensorflow-based classifier on the 
[Pime Indian Diabetes dataset](https://www.kaggle.com/uciml/pima-indians-diabetes-database) and then a 
`BatchInferencePipeline` to run an offline-batch job to get prediction results.

### Pre-requisites
In order to run this example, you need to install and initialize ZenML

```bash
pip install "zenml"
zenml example pull batch_inference
cd zenml_examples/batch_inference
git init
zenml init
```

### Run the project
Now we're ready. Execute:

```bash
python run.py
```


### Clean up
In order to clean up, in the root of your repo, delete the remaining zenml references.

```python
rm -r .zenml
rm -r pipelines
```

## Caveats
`BatchInferencePipeline` currently only works with Tensorflow SavedModels.

## Next Steps
Try [creating your own custom pytorch trainer](https://docs.zenml.io/getting-started/creating-custom-logic.html)!