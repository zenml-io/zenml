# Train a simple image-based classifier
This example how to use a [Tensorflow Dataset](https://www.tensorflow.org/datasets) based Datasource `TFDSDatasource` to train an image classifier for the MNIST dataset.
It uses Tensorflow to create the network.

### Pre-requisites
In order to run this example, you need to clone the zenml repo.

```bash
git clone https://github.com/maiot-io/zenml.git
```

Before continuing, either [install the zenml pip package](https://docs.zenml.io/getting-started/installation.html) or install it [from the cloned repo](../../zenml/README.md). 
In both cases, make sure to also install the pytorch extension (e.g. with pip: `pip install zenml`)

```
cd zenml
zenml init
cd examples/simple_cv
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

## Next Steps
Try using build different ZenML trainers for for more advanced CV tasks like object detection and image segmentation!