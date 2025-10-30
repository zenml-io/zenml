# simple_pipeline.py
from zenml import pipeline, step
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from typing import Tuple
from typing_extensions import Annotated
import numpy as np
import openai

@step
def create_dataset() -> Tuple[
    Annotated[np.ndarray, "X_train"],
    Annotated[np.ndarray, "X_test"], 
    Annotated[np.ndarray, "y_train"],
    Annotated[np.ndarray, "y_test"]
]:
    """Generate a simple classification dataset."""
    X, y = make_classification(n_samples=100, n_features=4, n_classes=2, random_state=42)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    return X_train, X_test, y_train, y_test

@step
def train_model(X_train: np.ndarray, y_train: np.ndarray) -> RandomForestClassifier:
    """Train a simple sklearn model."""
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X_train, y_train)
    return model

@step
def evaluate_model(model: RandomForestClassifier, X_test: np.ndarray, y_test: np.ndarray) -> float:
    """Evaluate the model accuracy."""
    predictions = model.predict(X_test)
    return accuracy_score(y_test, predictions)

@step
def generate_summary(accuracy: float) -> str:
    """Use OpenAI to generate a model summary."""
    client = openai.OpenAI()  # Set OPENAI_API_KEY environment variable
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{
            "role": "user", 
            "content": f"Write a brief summary of a ML model with {accuracy:.2%} accuracy."
        }],
        max_tokens=50
    )
    return response.choices[0].message.content

@pipeline
def simple_ml_pipeline():
    """A simple pipeline combining sklearn and OpenAI."""
    X_train, X_test, y_train, y_test = create_dataset()
    model = train_model(X_train, y_train)
    accuracy = evaluate_model(model, X_test, y_test)
    summary = generate_summary(accuracy)
    return summary

if __name__ == "__main__":
    result = simple_ml_pipeline()
