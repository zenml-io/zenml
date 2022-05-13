# 🔦 Using PyTorch with ZenML

This example demonstrate how we can use ZenML and PyTorch to build, train, and test ML models.

[PyTorch](https://pytorch.org/) is an open-source machine learning framework that accelerates the path from research prototyping to production deployment.

With the ZenML PyTorch integration, you can pass `torch.nn.Module` and `torch.utils.data.DataLoader` objects through steps as first class citizens. ZenML will automatically make sure 
to track and version these objects.

# 🖥 Run it locally

## ⏩ SuperQuick `pytorch` run

If you're really in a hurry and just want to see this example pipeline run
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run pytorch
```

## 👣 Step-by-Step

### 📄 Prerequisites

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install pytorch -f
pip install -r requirements.txt  # for torchvision

# pull example
cd zenml/examples/pytorch

# initialize
zenml init
```

### ▶️ Run the Code

Now we're ready. Execute the pipeline:

```shell
# sequence-classification
python run.py
```

This will train a PyTorch model on the Fashion MNIST dataset.

### 🧽 Clean up

In order to clean up, delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```
