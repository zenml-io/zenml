# Get up and running quickly
This example uses a `TrainingPipeline` to train a PyTorch-based regression model on the 
[Boston Housing dataset](https://www.cs.toronto.edu/~delve/data/boston/bostonDetail.html#:~:text=The%20Boston%20Housing%20Dataset,the%20area%20of%20Boston%20Mass.).

### Pre-requisites
In order to run this example, you need to install and initialize ZenML:

```bash
pip install "zenml"
zenml example pull pytorch
cd zenml_examples/pytorch
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

## Next Steps
Try [creating your own custom pytorch trainer](https://docs.zenml.io/getting-started/creating-custom-logic.html)!