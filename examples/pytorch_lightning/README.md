# Train using PyTorch Lightning
While, ZenML supports any library, it also comes packaged with special [PyTorch Lightning](https://pytorch_lightning.org/) support with 
the pre-built PyTorch Lightning trainer steps.


### Pre-requisites
In order to run this example, you need to clone the zenml repo.

```bash
git clone https://github.com/maiot-io/zenml.git
```

#### Note: Please skip below until pytorch_lightning is added as an extension
In order to run this example, you need to install and initialize ZenML:

```bash
pip install "zenml[pytorch]"
pip install pytorch-lightning==1.1.8
zenml example pull gcp_gpu_orchestrated
cd zenml_examples/gcp_gpu_orchestrated
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
There are currently certain limitations to this example and the code requires optimization. Contributions are welcome.

## Next Steps
Try [creating your own custom pytorch_lightning trainer](https://docs.zenml.io/getting-started/creating-custom-logic.html)!