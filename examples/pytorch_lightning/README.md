# Train using PyTorch Lightning
While, ZenML supports any library, it also comes packaged with special [PyTorch Lightning](https://pytorch_lightning.org/) support with 
the pre-built PyTorch Lightning trainer steps.


### Pre-requisites
In order to run this example, you need to clone the zenml repo.

```bash
git clone https://github.com/maiot-io/zenml.git
```

#### Note: Please skip below until pytorch_lightning is added as an extension
Before continuing, either [install the zenml pip package](https://docs.zenml.io/getting-started/installation.html) or install it [from the cloned repo](../../zenml/README.md). 
Also needed are the `pytorch-lightning` and `torch-vision` libraries:

```bash
pip install zenml[pytorch]
pip instal pytorch-lightning==1.1.8
```

Then:
```
cd zenml
zenml init
cd examples/pytorch_lightning
```

#### Short-term fix:


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
The PyTorch Lightning Trainer does not yet work with the `Evaluator` or `Deployer` steps that follow it in a `TrainingPipeline`.

## Next Steps
Try [creating your own custom pytorch_lightning trainer](https://docs.zenml.io/getting-started/creating-custom-logic.html)!