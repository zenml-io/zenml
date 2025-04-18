---
description: Build and deploy ML models using Baseten.
---

# Baseten

Baseten is a platform for building and deploying machine learning models. It uses [Truss](https://truss.baseten.co/), an open-source tool for packaging models into deployable units. Baseten provides a serverless platform for hosting ML models with automatic scaling, GPU support, and easy deployment.

The Baseten Model Deployer is one of the available flavors of the [Model Deployer](./model-deployers.md) stack component. Provided with the Baseten integration, it can be used to deploy and manage [Truss](https://truss.baseten.co/) models on the Baseten platform.

## When to use it?

You should use the Baseten Model Deployer when:

* **Simplicity is key**: You want a simple way to deploy models without managing infrastructure
* **GPU deployments**: You need GPU-accelerated inference for your models
* **Serverless scaling**: You want automatic scaling based on traffic
* **Production deployments**: You need a reliable, managed service for model hosting
* **Quick iteration**: You want to rapidly deploy and update models during development

Specifically, the Baseten Model Deployer is a good choice if:

* You want to deploy your models using the Baseten platform
* You are looking for a serverless solution for your ML models without dealing with the complexity of infrastructure management
* You need to package your models using Truss for easy deployment to Baseten
* You want to deploy large language models (LLMs) or other compute-intensive models

If you are looking to deploy your models with other Kubernetes-based solutions, or more simple local solutions, you can take a look at one of the other [Model Deployer Flavors](./model-deployers.md#model-deployers-flavors) available in ZenML.

## Installation and Setup

### Installing the Integration

To use the Baseten Model Deployer, you need to install the ZenML Baseten integration:

```bash
zenml integration install baseten -y
```

This command installs all the necessary dependencies, including the Baseten Python client and Truss packages.

### Creating and Storing API Keys Securely

The model deployer needs a Baseten API key to authenticate with the Baseten platform. For security, we recommend storing this key as a ZenML secret.

**Step 1**: Create a Baseten API key
* Sign in to your Baseten account at [app.baseten.co](https://app.baseten.co/)
* Navigate to Settings → API Keys
* Create a new API key with appropriate permissions
* Copy the API key for the next step

**Step 2**: Store the API key as a ZenML secret
```bash
zenml secret create baseten_secret --api_key=<YOUR_BASETEN_API_KEY_VALUE>
```

Alternatively, you can use the Python client:
```python
from zenml.client import Client

Client().create_secret(
    name="baseten_secret",
    values={"api_key": "YOUR_BASETEN_API_KEY_VALUE"}
)
```

### Registering the Model Deployer

Now you can register the Baseten model deployer with ZenML:

```bash
zenml model-deployer register baseten_deployer \
    --flavor=baseten \
    --baseten_api_key={{baseten_secret.api_key}}
```

You can also specify additional configuration options:
```bash
zenml model-deployer register baseten_deployer \
    --flavor=baseten \
    --baseten_api_key={{baseten_secret.api_key}} \
    --gpu=T4 \
    --cpu=2 \
    --memory=4Gi \
    --replicas=1
```

### Adding to Your Stack

Finally, add the model deployer to your ZenML stack:

```bash
# Create a new stack with the Baseten model deployer
zenml stack register my_baseten_stack \
    -a default \
    -o default \
    -d baseten_deployer

# Or update an existing stack
zenml stack update my_existing_stack -d baseten_deployer

# Set the stack as active
zenml stack set my_baseten_stack
```

## Using the Baseten Model Deployer

Using the Baseten model deployer involves two main steps:

1. **Building a Truss package** to encapsulate your model and its dependencies
2. **Deploying the Truss package** to Baseten's platform

ZenML provides built-in steps for both of these operations, making it easy to include Baseten deployments in your ML pipelines.

### Building a Truss Package

ZenML provides the `baseten_truss_builder` step that handles the creation of a Truss package from your trained model.

```python
from zenml import step, pipeline
from zenml.integrations.baseten.steps import baseten_truss_builder

@step
def train_model():
    """Train a simple model for demonstration."""
    from sklearn.datasets import load_iris
    from sklearn.ensemble import RandomForestClassifier
    
    # Load the iris dataset
    X, y = load_iris(return_X_y=True)
    
    # Train a simple random forest
    rf = RandomForestClassifier(n_estimators=10)
    rf.fit(X, y)
    return rf

@pipeline
def training_and_packaging_pipeline():
    # Train the model
    model = train_model()
    
    # Package the model as a Truss
    truss_dir = baseten_truss_builder(
        model=model,
        model_name="iris_classifier",
        python_version="py39",
        requirements=["scikit-learn", "joblib", "numpy"],
        resources={
            "cpu": "1", 
            "memory": "2Gi", 
            "use_gpu": False
        },
        overwrite=True  # Overwrite existing Truss directory
    )
    
    return truss_dir
```

#### Truss Builder Parameters

The `baseten_truss_builder` step supports the following parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `model` | Any | The trained model object to package |
| `truss_dir` | str | Directory path to create the Truss (default: "truss") |
| `model_name` | str | Name for the model in Baseten |
| `python_version` | str | Python version to use (e.g., "py39", "py310") |
| `requirements` | List[str] | Python package dependencies |
| `resources` | Dict | Resource specifications (cpu, memory, use_gpu) |
| `overwrite` | bool | Whether to overwrite an existing Truss directory |
| `include_numpy` | bool | Whether to automatically include numpy in requirements |
| `model_type` | str | Optional type of the model for serialization. If not provided, the type will be automatically detected. Supported types: "sklearn", "pytorch", "tensorflow", "xgboost", "lightgbm", "huggingface", or "generic". |

#### Truss Structure

The resulting Truss directory will have the following structure:

```
truss_dir/
├── config.yaml         # Configuration for Baseten deployment
└── model/
    ├── model.*         # Serialized model file (format depends on model type)
    └── model.py        # Model definition with load and predict methods
```

The model file format depends on the model type:
- `model.joblib`: For scikit-learn, XGBoost and LightGBM models
- `model.pt`: For PyTorch models
- `model.h5` or `tf_model/`: For TensorFlow models
- `hf_model/`: For Hugging Face models
- `model.cloudpickle` or `model.pickle`: For generic models

The `model.py` file includes a robust implementation of a model class with proper error handling and validation that automatically detects and loads the correct model format.

### Deploying a Truss to Baseten

Once you have a Truss package, you can deploy it to Baseten using the `baseten_model_deployer_step`:

```python
from zenml import pipeline
from zenml.integrations.baseten.steps import baseten_model_deployer_step

@pipeline
def deployment_pipeline():
    # Get the path to your Truss directory
    truss_dir = "path/to/truss_dir"  # Or output from baseten_truss_builder
    
    # Deploy to Baseten
    service = baseten_model_deployer_step(
        truss_dir=truss_dir,
        model_name="iris_classifier",
        service_name="iris-classifier-service",
        framework="sklearn",
        replace=True,  # Replace existing deployment if any
        timeout=300,   # Deployment timeout in seconds
    )
    
    return service
```

#### Deployer Step Parameters

The `baseten_model_deployer_step` supports the following parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `truss_dir` | str | Path to the Truss directory |
| `model_name` | str | Name of the model in Baseten |
| `framework` | str | Framework/type of the model (default: "sklearn") |
| `deploy_decision` | bool | Whether to deploy the model (default: True) |
| `timeout` | int | Timeout in seconds for deployment (default: 300) |
| `replace` | bool | Whether to replace existing deployments (default: True) |
| `service_name` | str | Custom name for the service in ZenML (optional) |
| `environment_variables` | Dict[str, str] | Environment variables for deployment (optional) |
| `resources` | Dict[str, Any] | Resource requirements override (optional) |

### Complete End-to-End Pipeline

Here's a complete example of a pipeline that trains a model, packages it as a Truss, deploys it to Baseten, and makes predictions:

```python
from zenml import pipeline, step
from zenml.integrations.baseten.steps import baseten_truss_builder, baseten_model_deployer_step
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_iris
import torch
import torch.nn as nn

@step
def train_sklearn_model() -> RandomForestClassifier:
    """Train a scikit-learn model for demonstration."""
    X, y = load_iris(return_X_y=True)
    rf = RandomForestClassifier(n_estimators=10)
    rf.fit(X, y)
    return rf

@step
def train_pytorch_model() -> nn.Module:
    """Train a PyTorch model for demonstration."""
    X, y = load_iris(return_X_y=True)
    X = torch.tensor(X, dtype=torch.float32)
    y = torch.tensor(y, dtype=torch.long)
    
    # Simple PyTorch model
    model = nn.Sequential(
        nn.Linear(4, 10),
        nn.ReLU(),
        nn.Linear(10, 3)
    )
    
    # Quick training
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    
    for _ in range(100):
        optimizer.zero_grad()
        outputs = model(X)
        loss = criterion(outputs, y)
        loss.backward()
        optimizer.step()
    
    model.eval()
    return model

@step
def get_sample_data() -> np.ndarray:
    """Get sample data for prediction."""
    X, _ = load_iris(return_X_y=True)
    return X[:5]  # Use first 5 samples

@step
def predict(service, data: np.ndarray) -> dict:
    """Make predictions using the deployed model."""
    response = service.predict({"instances": data.tolist()})
    return response

@pipeline
def sklearn_model_pipeline():
    # Train scikit-learn model
    model = train_sklearn_model()
    
    # Package as Truss - type will be auto-detected
    truss_dir = baseten_truss_builder(
        model=model,
        model_name="iris_sklearn",
        resources={"cpu": "1", "memory": "2Gi", "use_gpu": False}
    )
    
    # Deploy to Baseten
    service = baseten_model_deployer_step(
        truss_dir=truss_dir,
        model_name="iris_sklearn",
        service_name="iris-sklearn-service"
    )
    
    # Make predictions
    data = get_sample_data()
    predictions = predict(service=service, data=data)
    
    return predictions

@pipeline
def pytorch_model_pipeline():
    # Train PyTorch model
    model = train_pytorch_model()
    
    # Package as Truss with explicit model type
    truss_dir = baseten_truss_builder(
        model=model,
        model_name="iris_pytorch",
        model_type="pytorch",  # Explicitly set model type
        resources={"cpu": "1", "memory": "2Gi", "use_gpu": False},
        requirements=["torch", "numpy"]  # Specify dependencies
    )
    
    # Deploy to Baseten
    service = baseten_model_deployer_step(
        truss_dir=truss_dir,
        model_name="iris_pytorch",
        service_name="iris-pytorch-service"
    )
    
    # Make predictions
    data = get_sample_data()
    predictions = predict(service=service, data=data)
    
    return predictions
```

### Service Lifecycle Management

The Baseten model deployer manages the complete lifecycle of your model deployment:

1. **Deployment**: Pushing your model to Baseten
2. **Status Tracking**: Monitoring the deployment status
3. **Prediction**: Making inference requests
4. **Starting/Stopping**: Activating or deactivating the deployment
5. **Deletion**: Removing the deployment when no longer needed

You can interact with the deployment service directly:

```python
# Get an existing service
from zenml.client import Client

services = Client().list_services(service_name="iris-classifier-service")
if services.items:
    service = services.items[0]
    
    # Check status
    if service.is_running:
        print(f"Service is running at: {service.prediction_url}")
    
    # Make predictions
    response = service.predict({"instances": [[5.1, 3.5, 1.4, 0.2]]})
    print(f"Prediction: {response}")
    
    # Stop the service
    service.stop()
    
    # Delete the service
    service.delete()
```

## Troubleshooting

Here are solutions to common issues when using the Baseten model deployer:

### Deployment Failures

If your deployment fails, check the following:

1. **API Key**: Ensure your Baseten API key is valid and has the necessary permissions
2. **Truss Structure**: Verify your Truss directory has the correct structure (config.yaml and model/model.py)
3. **Resource Requirements**: Make sure you're not requesting resources beyond your Baseten account limits
4. **Network Issues**: Check your internet connection and any proxies that might interfere with API calls

### Prediction Errors

If predictions fail:

1. **Input Format**: Ensure your input data matches the expected format in your model.py file
2. **Service Status**: Check if the service is running with `service.is_running`
3. **Network Timeout**: Large models might take longer to respond; adjust timeout settings if needed
4. **Model Type**: If you're experiencing issues with a specific model type:
   - Try explicitly setting `model_type` when calling `baseten_truss_builder`
   - Verify that the required dependencies are included in the `requirements` list
   - For PyTorch models, ensure model is in evaluation mode with `model.eval()`
   - For TensorFlow models, check if additional dependencies like h5py are needed
   - For Hugging Face models, try using save_pretrained/from_pretrained methods directly

### Resource Management

To optimize costs and performance:

1. **Stop Unused Deployments**: Use `service.stop()` when not actively using a deployment
2. **Delete Old Deployments**: Clean up with `service.delete()` when a deployment is no longer needed
3. **Right-size Resources**: Configure appropriate CPU, memory, and GPU resources based on your model's needs

## Advanced Configuration

### Custom Model Types

Baseten now supports various model types out of the box, including:

- PyTorch models
- TensorFlow/Keras models
- Hugging Face transformers
- XGBoost models
- LightGBM models
- Scikit-learn models
- Generic Python objects via cloudpickle/pickle

The model type is automatically detected based on the model's module namespace, but you can also explicitly specify it:

```python
truss_dir = baseten_truss_builder(
    model=model,
    model_type="pytorch",  # Explicitly specify model type
    resources={"cpu": "2", "memory": "4Gi", "use_gpu": True}
)
```

The automatic detection logic works as follows:
- Models from `sklearn.*` modules → sklearn
- Models from `torch.*` modules → pytorch
- Models from `tensorflow.*`, `tf.*`, or `keras.*` modules → tensorflow
- Models from `xgboost.*` modules → xgboost
- Models from `lightgbm.*` modules → lightgbm
- Models from `transformers.*` or `diffusers.*` modules → huggingface
- Any other model type → generic (uses cloudpickle or pickle)

The generated `model.py` file contains smart logic for:

1. **Model Loading**: Automatically detects and loads different model types with appropriate methods
2. **Input Processing**: Framework-specific preprocessing for each model type:
   - PyTorch: Converts inputs to PyTorch tensors
   - TensorFlow: Handles tensor inputs and batch dimensions
   - Hugging Face: Special handling for text and tokenized inputs
   - Default: Converts to numpy arrays for traditional ML frameworks

3. **Output Processing**: Framework-specific output handling:
   - PyTorch: Properly detaches tensors, moves them to CPU, and converts to lists
   - TensorFlow: Converts EagerTensors and handles dictionary outputs
   - Hugging Face: Processes nested tensor structures in model outputs
   - Generic: Handles numpy arrays and mixed-type outputs

This smart processing ensures your models work correctly regardless of the framework, without requiring any custom code.

### GPU Acceleration

To deploy GPU-accelerated models:

```python
# In baseten_truss_builder
truss_dir = baseten_truss_builder(
    model=model,
    resources={"cpu": "2", "memory": "8Gi", "use_gpu": True}
)

# Or directly in model deployer registration
zenml model-deployer register baseten_deployer \
    --flavor=baseten \
    --baseten_api_key={{baseten_secret.api_key}} \
    --gpu=T4  # Specify GPU type
```

For more information and a full list of configurable attributes of the Baseten
Model Deployer, check out the [SDK
Docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-baseten/#zenml.integrations.baseten.model_deployers.baseten_model_deployer).
