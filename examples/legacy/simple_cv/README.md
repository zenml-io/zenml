# Train a simple image-based classifier
This example how to use a [Tensorflow Dataset](https://www.tensorflow.org/datasets) based Datasource `TFDSDatasource` to train an image classifier for the MNIST dataset.
It uses Tensorflow to create the network.

### Pre-requisites
In order to run this example, you need to install and initialize ZenML:

```bash
pip install "zenml"
zenml example pull simple_cv
cd zenml_examples/simple_cv
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
Try using build different ZenML trainers for for more advanced CV tasks like object detection and image segmentation!