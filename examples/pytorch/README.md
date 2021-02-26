# Train using PyTorch
While, ZenML supports any library, it also comes packaged with special [PyTorch](https://pytorch.org/) support with 
the pre-built PyTorch trainer steps.


### Pre-requisites
In order to run this example, you need to clone the zenml repo.

```bash
git clone https://github.com/maiot-io/zenml.git
```

Before continuing, either [install the zenml pip package](https://docs.zenml.io/getting-started/installation.html) or install it [from the cloned repo](../../zenml/README.md). 
In both cases, make sure to also install the pytorch extension (e.g. with pip: `pip install zenml[pytorch]`)

```
cd zenml
zenml init
cd examples/pytorch
```


### Run the project
Now we're ready. Execute:

```bash
python run.py
```


### Clean up
In order to clean up, in the root of your repo, delete the remaining zenml references.

```python
cd ../..
rm -r .zenml
rm -r pipelines
```

## Caveats
The PyTorch Trainer does not yet work with the `Evaluator` or `Deployer` steps that follow it in a `TrainingPipeline`.

## Next Steps
Try [creating your own custom pytorch trainer](https://docs.zenml.io/getting-started/creating-custom-logic.html)!