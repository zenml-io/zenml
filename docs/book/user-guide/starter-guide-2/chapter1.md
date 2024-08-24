[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/zenml-io/zenml/blob/main/tutorials/starter-guide-2/chapter1.ipynb) [![Run Locally](https://img.shields.io/badge/run-locally-blue)](https://github.com/zenml-io/zenml)

# 🐣 Starter guide

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/your-repo/zenml-docs/blob/main/notebooks/01_introduction.ipynb) [![Run Locally](https://img.shields.io/badge/run-locally-blue)](https://github.com/your-repo/zenml-docs)

Welcome to the ZenML Starter Guide! If you're an MLOps engineer aiming to build robust ML platforms, or a data scientist interested in leveraging the power of MLOps, this is the perfect place to begin. Our guide is designed to provide you with the foundational knowledge of the ZenML framework and equip you with the initial tools to manage the complexity of machine learning operations.

![Embarking on MLOps can be intricate. ZenML simplifies the journey.](../../docs/book/.gitbook/assets/01_pipeline.png)

Throughout this guide, we'll cover essential topics including:

- Creating your first ML pipeline
- Understanding caching between pipeline steps
- Fetching objects after pipelines have run
- Managing data and data versioning
- Tracking your machine learning models
- Structuring your pipelines, models, and artifacts

Before jumping in, make sure you have a Python environment ready and `virtualenv` installed to follow along with ease.


```python
!pip install zenml
```

By the end, you will have completed a starter project, marking the beginning of your journey into MLOps with ZenML.

Let this guide be not only your introduction to ZenML but also a foundational asset in your MLOps toolkit. Prepare your development environment, and let's get started!


```python
from zenml import pipeline, step

@step
def load_data() -> dict:
    """Simulates loading of training data and labels."""

    training_data = [[1, 2], [3, 4], [5, 6]]
    labels = [0, 1, 0]
    
    return {'features': training_data, 'labels': labels}

@step
def train_model(data: dict) -> None:
    """
    A mock 'training' process that also demonstrates using the input data.
    In a real-world scenario, this would be replaced with actual model fitting logic.
    """
    total_features = sum(map(sum, data['features']))
    total_labels = sum(data['labels'])
    
    print(f"Trained model using {len(data['features'])} data points. "
          f"Feature sum is {total_features}, label sum is {total_labels}")

@pipeline
def simple_ml_pipeline():
    """Define a pipeline that connects the steps."""
    dataset = load_data()
    train_model(dataset)

if __name__ == "__main__":
    run = simple_ml_pipeline()
    # You can now use the `run` object to see steps, outputs, etc.
```


{% hint style="info" %}
* **`@step`** is a decorator that converts its function into a step that can be used within a pipeline
* **`@pipeline`** defines a function as a pipeline and within this function, the steps are called and their outputs link them together.
{% endhint %}

Copy this code into a new file and name it `run.py`. Then run it with your command line:


```python
from zenml import pipeline, step

@step
def load_data() -> dict:
    """Simulates loading of training data and labels."""

    training_data = [[1, 2], [3, 4], [5, 6]]
    labels = [0, 1, 0]
    
    return {'features': training_data, 'labels': labels}

@step
def train_model(data: dict) -> None:
    """
    A mock 'training' process that also demonstrates using the input data.
    In a real-world scenario, this would be replaced with actual model fitting logic.
    """
    total_features = sum(map(sum, data['features']))
    total_labels = sum(data['labels'])
    
    print(f"Trained model using {len(data['features'])} data points. "
          f"Feature sum is {total_features}, label sum is {total_labels}")

@pipeline
def simple_ml_pipeline():
    """Define a pipeline that connects the steps."""
    dataset = load_data()
    train_model(dataset)

if __name__ == "__main__":
    run = simple_ml_pipeline()
    # You can now use the `run` object to see steps, outputs, etc.
```


```python
from zenml import pipeline, step

@step
def load_data() -> dict:
    """Simulates loading of training data and labels."""

    training_data = [[1, 2], [3, 4], [5, 6]]
    labels = [0, 1, 0]
    
    return {'features': training_data, 'labels': labels}

@step
def train_model(data: dict) -> None:
    """
    A mock 'training' process that also demonstrates using the input data.
    In a real-world scenario, this would be replaced with actual model fitting logic.
    """
    total_features = sum(map(sum, data['features']))
    total_labels = sum(data['labels'])
    
    print(f"Trained model using {len(data['features'])} data points. "
          f"Feature sum is {total_features}, label sum is {total_labels}")

@pipeline
def simple_ml_pipeline():
    """Define a pipeline that connects the steps."""
    dataset = load_data()
    train_model(dataset)

if __name__ == "__main__":
    run = simple_ml_pipeline()
    # You can now use the `run` object to see steps, outputs, etc.
```


```python
from zenml import pipeline, step

@step
def load_data() -> dict:
    """Simulates loading of training data and labels."""

    training_data = [[1, 2], [3, 4], [5, 6]]
    labels = [0, 1, 0]
    
    return {'features': training_data, 'labels': labels}

@step
def train_model(data: dict) -> None:
    """
    A mock 'training' process that also demonstrates using the input data.
    In a real-world scenario, this would be replaced with actual model fitting logic.
    """
    total_features = sum(map(sum, data['features']))
    total_labels = sum(data['labels'])
    
    print(f"Trained model using {len(data['features'])} data points. "
          f"Feature sum is {total_features}, label sum is {total_labels}")

@pipeline
def simple_ml_pipeline():
    """Define a pipeline that connects the steps."""
    dataset = load_data()
    train_model(dataset)

if __name__ == "__main__":
    run = simple_ml_pipeline()
    # You can now use the `run` object to see steps, outputs, etc.
```


