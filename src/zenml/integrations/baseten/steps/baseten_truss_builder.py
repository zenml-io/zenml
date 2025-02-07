"""Implementation of the Baseten Truss builder step."""

import os
import joblib
import yaml
from typing import Optional, Any
from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def baseten_truss_builder(
    model: Any,
    truss_dir: str = "truss",
    model_name: Optional[str] = None,
    python_version: str = "py39",
    requirements: Optional[list] = None,
    resources: Optional[dict] = None,
) -> str:
    """Build a Truss directory for deployment to Baseten.

    Args:
        model: The trained model to package
        truss_dir: Directory to create the Truss in
        model_name: Name for the model in Baseten
        python_version: Python version to use
        requirements: List of Python package requirements
        resources: Dict of resource requirements (cpu, memory, gpu)

    Returns:
        Path to the created Truss directory
    """
    # Create the Truss directory structure
    os.makedirs(truss_dir, exist_ok=True)
    model_dir = os.path.join(truss_dir, "model")
    os.makedirs(model_dir, exist_ok=True)

    # Save the model
    model_path = os.path.join(model_dir, "model.joblib")
    joblib.dump(model, model_path)
    logger.info(f"Saved model to {model_path}")

    # Create config.yaml
    config = {
        "model_name": model_name or os.path.basename(truss_dir),
        "python_version": python_version,
        "requirements": requirements or ["scikit-learn", "joblib"],
        "resources": resources
        or {
            "cpu": "1",
            "memory": "2Gi",
            "use_gpu": False,
        },
        "model_type": "custom",
    }

    config_path = os.path.join(truss_dir, "config.yaml")
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    logger.info(f"Created config.yaml at {config_path}")

    # Create model.py
    model_code = '''
import joblib
import numpy as np
from typing import Dict, Any

class Model:
    def __init__(self, **kwargs):
        self._model = None
        
    def load(self):
        """Load the model from the serialized format"""
        self._model = joblib.load('model/model.joblib')
        
    def predict(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Predict with the model"""
        if not self._model:
            self.load()
            
        # Extract features from the request
        features = np.array(request["instances"])
        
        # Make prediction
        predictions = self._model.predict(features)
        
        # Return predictions
        return {"predictions": predictions.tolist()}
'''

    model_py_path = os.path.join(model_dir, "model.py")
    with open(model_py_path, "w") as f:
        f.write(model_code.strip())
    logger.info(f"Created model.py at {model_py_path}")

    return os.path.abspath(truss_dir)
