# Train using PyTorch
While, ZenML supports any library, it also comes packaged with special [PyTorch](https://pytorch.org/) support with 
the pre-built PyTorch trainer steps.


### Pre-requisites
In order to run this example, you need to install and initialize ZenML:

```bash
pip install "zenml[pytorch]"
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

## Caveats
The PyTorch Trainer does not yet work with the `Evaluator` or `Deployer` steps that follow it in a `TrainingPipeline`.

## Next Steps
Try [creating your own custom pytorch trainer](https://docs.zenml.io/getting-started/creating-custom-logic.html)!