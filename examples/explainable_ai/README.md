# 🔦 Using FoXAI with ZenML

This example demonstrate how we can use ZenML and FoXAI to build, train, 
test and explain ML models.

[FoXAI](https://github.com/softwaremill/FoXAI) is an open-source machine learning
framework for explainable AI.

# 🖥 Run it locally

## 👣 Step-by-Step

### 📄 Prerequisites

```shell
# install CLI
pip install "zenml[server]"

# install ZenML integrations
zenml integration install pytorch
pip install -r requirements.txt  # for torchvision

# initialize
zenml init

# Start the ZenServer to enable dashboard access
zenml up
```

### ▶️ Run the Code

Now we're ready. Execute the pipeline:

```shell
# sequence-classification
python run.py
```

This will load pre-trained model from torchvision hub and explain the model
against CIFAR10 dataset.