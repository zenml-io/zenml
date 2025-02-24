"""Implementation of the Baseten Truss builder step."""

import os
import shutil
import traceback
from typing import Any, Dict, List, Optional, Tuple

import yaml

from zenml import step
from zenml.logger import get_logger

# Import serializers conditionally to avoid hard dependencies
try:
    import joblib

    HAS_JOBLIB = True
except ImportError:
    HAS_JOBLIB = False

try:
    import cloudpickle

    HAS_CLOUDPICKLE = True
except ImportError:
    HAS_CLOUDPICKLE = False

try:
    import pickle

    HAS_PICKLE = True
except ImportError:
    HAS_PICKLE = False

logger = get_logger(__name__)


def _validate_resources(resources: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate resources configuration for Baseten.

    Args:
        resources: Dictionary of resource requirements

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(resources, dict):
        return False, f"Resources must be a dictionary, got {type(resources)}"

    # Check for required keys
    required_keys = ["cpu", "memory"]
    for key in required_keys:
        if key not in resources:
            return False, f"Missing required resource key: {key}"

    # Validate CPU
    try:
        cpu = resources["cpu"]
        if isinstance(cpu, str):
            cpu_value = float(cpu.rstrip("m"))
        elif isinstance(cpu, (int, float)):
            cpu_value = float(cpu)
        else:
            return False, f"CPU must be a number or string, got {type(cpu)}"

        if cpu_value <= 0:
            return False, f"CPU must be positive, got {cpu_value}"
    except (ValueError, TypeError) as e:
        return False, f"Invalid CPU value: {str(e)}"

    # Validate memory
    try:
        memory = resources["memory"]
        if not isinstance(memory, str):
            return (
                False,
                f"Memory must be a string (e.g., '2Gi'), got {type(memory)}",
            )

        # Basic format validation for memory
        if not any(memory.endswith(unit) for unit in ["Mi", "Gi", "Ti"]):
            return False, f"Memory must end with Mi, Gi, or Ti, got {memory}"

        memory_value = float(memory[:-2])
        if memory_value <= 0:
            return False, f"Memory must be positive, got {memory_value}"
    except (ValueError, TypeError) as e:
        return False, f"Invalid memory value: {str(e)}"

    # GPU is optional
    if "use_gpu" in resources:
        if not isinstance(resources["use_gpu"], bool):
            return (
                False,
                f"use_gpu must be a boolean, got {type(resources['use_gpu'])}",
            )

    return True, ""


def _validate_requirements(requirements: List[str]) -> Tuple[bool, str]:
    """Validate requirements list for Baseten.

    Args:
        requirements: List of Python package requirements

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(requirements, list):
        return False, f"Requirements must be a list, got {type(requirements)}"

    for req in requirements:
        if not isinstance(req, str):
            return False, f"Each requirement must be a string, got {type(req)}"

    return True, ""


def _detect_model_type(model: Any) -> str:
    """Detect the type of the model to determine the best serialization method.

    Args:
        model: The model to detect

    Returns:
        String representing the model type
    """
    # Check for common ML frameworks
    model_type = "generic"
    model_module = type(model).__module__
    model_class_name = type(model).__name__

    # Scikit-learn models
    if model_module.startswith("sklearn"):
        return "sklearn"

    # PyTorch models - check module and also if it's a nn.Module subclass
    if model_module.startswith("torch") or (
        hasattr(model, "__class__")
        and hasattr(model.__class__, "__bases__")
        and any(
            "torch.nn.modules" in str(base) for base in model.__class__.__mro__
        )
    ):
        return "pytorch"

    # TensorFlow/Keras models
    if model_module.startswith(("tensorflow", "tf", "keras")):
        return "tensorflow"

    # XGBoost models
    if model_module.startswith("xgboost"):
        return "xgboost"

    # LightGBM models
    if model_module.startswith("lightgbm"):
        return "lightgbm"

    # Hugging Face models
    if model_module.startswith(("transformers", "diffusers")):
        return "huggingface"

    # Default to generic for any other type
    return model_type


def _save_model(
    model: Any, model_dir: str, model_type: Optional[str] = None
) -> Tuple[str, List[str]]:
    """Save model using the appropriate serialization method based on its type.

    Args:
        model: The model to save
        model_dir: Directory to save the model in
        model_type: Optional explicit model type to use for serialization

    Returns:
        Tuple of (serialization_method, required_packages)

    Raises:
        RuntimeError: If model serialization fails
    """
    # Detect model type if not explicitly provided
    if not model_type:
        model_type = _detect_model_type(model)

    logger.info(f"Detected/specified model type: {model_type}")

    required_packages = []
    serialization_method = "unknown"

    try:
        # Specialized serialization based on model type
        if model_type == "pytorch":
            # Use PyTorch serialization
            import torch

            model_path = os.path.join(model_dir, "model.pt")
            torch.save(model, model_path)
            required_packages = ["torch"]
            serialization_method = "pytorch"

        elif model_type == "tensorflow":
            # Use TensorFlow serialization
            try:
                # Try SavedModel format first
                model_path = os.path.join(model_dir, "tf_model")
                model.save(model_path)
                required_packages = ["tensorflow"]
                serialization_method = "tensorflow"
            except Exception as e:
                # Fall back to H5 if SavedModel fails
                logger.warning(f"TF SavedModel failed, trying H5: {str(e)}")
                model_path = os.path.join(model_dir, "model.h5")
                model.save(model_path)
                required_packages = ["tensorflow", "h5py"]
                serialization_method = "tensorflow-h5"

        elif (
            model_type == "sklearn"
            or model_type == "xgboost"
            or model_type == "lightgbm"
        ):
            # Use joblib for these model types
            if not HAS_JOBLIB:
                raise ImportError(
                    "joblib is required for this model type but not installed"
                )

            model_path = os.path.join(model_dir, "model.joblib")
            joblib.dump(model, model_path)
            required_packages = ["joblib"]

            # Add the specific ML library
            if model_type == "sklearn":
                required_packages.append("scikit-learn")
            elif model_type == "xgboost":
                required_packages.append("xgboost")
            elif model_type == "lightgbm":
                required_packages.append("lightgbm")

            serialization_method = "joblib"

        elif model_type == "huggingface":
            # Use the Hugging Face save_pretrained method if available
            model_path = os.path.join(model_dir, "hf_model")
            os.makedirs(model_path, exist_ok=True)

            try:
                model.save_pretrained(model_path)
                required_packages = ["transformers"]
                serialization_method = "huggingface"
            except AttributeError:
                # Fall back to pickle if save_pretrained is not available
                logger.warning(
                    "Model doesn't support save_pretrained, falling back to pickle"
                )
                model_path = os.path.join(model_dir, "model.pickle")

                if HAS_CLOUDPICKLE:
                    with open(model_path, "wb") as f:
                        cloudpickle.dump(model, f)
                    required_packages = ["cloudpickle"]
                    serialization_method = "cloudpickle"
                else:
                    with open(model_path, "wb") as f:
                        pickle.dump(model, f)
                    required_packages = []  # pickle is in stdlib
                    serialization_method = "pickle"

        else:
            # Generic fallback approach
            logger.warning(
                f"No specialized serialization for model type '{model_type}', "
                "falling back to cloudpickle/pickle"
            )

            # Try cloudpickle first, then pickle
            if HAS_CLOUDPICKLE:
                model_path = os.path.join(model_dir, "model.cloudpickle")
                with open(model_path, "wb") as f:
                    cloudpickle.dump(model, f)
                required_packages = ["cloudpickle"]
                serialization_method = "cloudpickle"
            elif HAS_PICKLE:
                model_path = os.path.join(model_dir, "model.pickle")
                with open(model_path, "wb") as f:
                    pickle.dump(model, f)
                required_packages = []  # pickle is in stdlib
                serialization_method = "pickle"
            else:
                raise RuntimeError(
                    "Neither cloudpickle nor pickle is available"
                )

        logger.info(f"Successfully saved model using {serialization_method}")
        return serialization_method, required_packages

    except Exception as e:
        logger.error(f"Failed to serialize model: {str(e)}")
        logger.error(traceback.format_exc())
        raise RuntimeError(f"Failed to serialize model: {str(e)}")


@step
def baseten_truss_builder(
    model: Any,
    truss_dir: str = "truss",
    model_name: Optional[str] = None,
    python_version: str = "py39",
    requirements: Optional[List[str]] = None,
    resources: Optional[Dict[str, Any]] = None,
    overwrite: bool = False,
    include_numpy: bool = True,
    model_type: Optional[str] = None,
) -> str:
    """Build a Truss directory for deployment to Baseten.

    This step creates a Truss directory structure that can be deployed to Baseten.
    It packages your model with the necessary files for deployment.

    Args:
        model: The trained model to package (will be serialized based on model_type)
        truss_dir: Directory to create the Truss in (absolute or relative path)
        model_name: Name for the model in Baseten (defaults to directory name if not specified)
        python_version: Python version to use (e.g., "py39", "py310")
        requirements: List of Python package dependencies
        resources: Dict of resource requirements (cpu, memory, use_gpu)
        overwrite: Whether to overwrite the truss_dir if it already exists
        include_numpy: Whether to automatically include numpy in requirements
        model_type: Optional type of the model for serialization. If not provided,
            the type will be automatically detected. Supported types: "sklearn",
            "pytorch", "tensorflow", "xgboost", "lightgbm", "huggingface", or "generic".

    Returns:
        Path to the created Truss directory (absolute path)

    Raises:
        ValueError: If inputs are invalid or directory creation fails
        RuntimeError: If model serialization or file operations fail
    """
    # Use default requirements if none provided
    if requirements is None:
        requirements = ["scikit-learn", "joblib"]

    # Always include numpy if requested (and not already there)
    if include_numpy and "numpy" not in requirements:
        requirements.append("numpy")

    # Use default resources if none provided
    if resources is None:
        resources = {
            "cpu": "1",
            "memory": "2Gi",
            "use_gpu": False,
        }

    # Validate inputs
    if model is None:
        raise ValueError("Model cannot be None")

    # Validate resources
    is_valid, error_msg = _validate_resources(resources)
    if not is_valid:
        raise ValueError(f"Invalid resources configuration: {error_msg}")

    # Validate requirements
    is_valid, error_msg = _validate_requirements(requirements)
    if not is_valid:
        raise ValueError(f"Invalid requirements: {error_msg}")

    # Validate python version
    valid_python_versions = ["py38", "py39", "py310", "py311"]
    if python_version not in valid_python_versions:
        raise ValueError(
            f"Invalid python_version: {python_version}. "
            f"Must be one of {valid_python_versions}"
        )

    # Convert truss_dir to absolute path if it's relative
    truss_dir = os.path.abspath(truss_dir)

    # Check if the directory already exists
    if os.path.exists(truss_dir):
        if overwrite:
            logger.warning(
                f"Overwriting existing Truss directory: {truss_dir}"
            )
            try:
                shutil.rmtree(truss_dir)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to delete existing directory {truss_dir}: {str(e)}"
                )
        else:
            raise ValueError(
                f"Truss directory {truss_dir} already exists. "
                "Set overwrite=True to overwrite it."
            )

    try:
        # Create the Truss directory structure
        os.makedirs(truss_dir, exist_ok=True)
        model_dir = os.path.join(truss_dir, "model")
        os.makedirs(model_dir, exist_ok=True)

        # Set model name (use directory name if not specified)
        if not model_name:
            model_name = os.path.basename(truss_dir)

        logger.info(f"Creating Truss for model '{model_name}' in {truss_dir}")

        # Save the model using appropriate serialization method
        try:
            # Use the flexible model saving function
            serialization_method, additional_packages = _save_model(
                model=model, model_dir=model_dir, model_type=model_type
            )

            # Add required packages for the specific serialization method
            for package in additional_packages:
                if package not in requirements:
                    requirements.append(package)

            logger.info(
                f"Saved model using {serialization_method} serialization"
            )
        except Exception as e:
            logger.error(f"Failed to serialize model: {str(e)}")
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Failed to serialize model: {str(e)}")

        # Create config.yaml - store detected model type
        config = {
            "model_name": model_name,
            "python_version": python_version,
            "requirements": requirements,
            "resources": resources,
            "model_type": "custom",
            "zenml_model_type": model_type or _detect_model_type(model),
            "serialization_method": serialization_method,
        }

        config_path = os.path.join(truss_dir, "config.yaml")
        try:
            with open(config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False)
            logger.info(f"Created config.yaml at {config_path}")
        except Exception as e:
            logger.error(f"Failed to write config.yaml: {str(e)}")
            raise RuntimeError(f"Failed to write config.yaml: {str(e)}")

        # Create a dynamic model.py based on the serialization method
        model_code = f'''
import os
import traceback
import numpy as np
from typing import Dict, Any, List, Union, Optional, Tuple

# Serialization method used: {serialization_method}

class Model:
    def __init__(self, **kwargs):
        self._model = None
        self._is_loaded = False
        self._serialization_method = "{serialization_method}"
        
    def load(self):
        """Load the model from the serialized format"""
        try:
            # Use the appropriate loading method based on serialization
            if self._serialization_method == "pytorch":
                import torch
                self._model = torch.load('model/model.pt')
                
            elif self._serialization_method == "tensorflow":
                import tensorflow as tf
                model_path = 'model/tf_model'
                if os.path.exists(model_path):
                    self._model = tf.keras.models.load_model(model_path)
                else:
                    # Fall back to H5 if SavedModel not found
                    self._model = tf.keras.models.load_model('model/model.h5')
                    
            elif self._serialization_method == "tensorflow-h5":
                import tensorflow as tf
                self._model = tf.keras.models.load_model('model/model.h5')
                
            elif self._serialization_method == "joblib":
                import joblib
                self._model = joblib.load('model/model.joblib')
                
            elif self._serialization_method == "huggingface":
                # Dynamically import the right module based on the model
                model_path = 'model/hf_model'
                
                # Try to determine the model type from the config
                try:
                    import json
                    import os
                    if os.path.exists(os.path.join(model_path, 'config.json')):
                        with open(os.path.join(model_path, 'config.json')) as f:
                            config = json.load(f)
                        model_type = config.get('model_type')
                        
                        # Import appropriate model class based on model_type
                        if model_type == 'bert':
                            from transformers import BertModel, BertForSequenceClassification
                            # Check for specific model class
                            if os.path.exists(os.path.join(model_path, 'pytorch_model.bin')):
                                self._model = BertForSequenceClassification.from_pretrained(model_path)
                            else:
                                self._model = BertModel.from_pretrained(model_path)
                        elif model_type == 'gpt2':
                            from transformers import GPT2Model, GPT2LMHeadModel
                            if os.path.exists(os.path.join(model_path, 'pytorch_model.bin')):
                                self._model = GPT2LMHeadModel.from_pretrained(model_path)
                            else:
                                self._model = GPT2Model.from_pretrained(model_path)
                        else:
                            # Generic case
                            from transformers import AutoModel
                            self._model = AutoModel.from_pretrained(model_path)
                    else:
                        # If no config, try AutoModel
                        from transformers import AutoModel
                        self._model = AutoModel.from_pretrained(model_path)
                except Exception as e:
                    # Fall back to direct loading with cloudpickle if HF specific loading fails
                    print(f"Failed to load with HF: {{e}}, falling back to pickle")
                    if os.path.exists('model/model.pickle'):
                        import pickle
                        with open('model/model.pickle', 'rb') as f:
                            self._model = pickle.load(f)
                    elif os.path.exists('model/model.cloudpickle'):
                        import cloudpickle
                        with open('model/model.cloudpickle', 'rb') as f:
                            self._model = cloudpickle.load(f)
            
            elif self._serialization_method == "cloudpickle":
                import cloudpickle
                with open('model/model.cloudpickle', 'rb') as f:
                    self._model = cloudpickle.load(f)
                    
            elif self._serialization_method == "pickle":
                import pickle
                with open('model/model.pickle', 'rb') as f:
                    self._model = pickle.load(f)
                    
            else:
                # Try to load with each method as a fallback
                try_methods = [
                    ('joblib', lambda: __import__('joblib').load('model/model.joblib')),
                    ('torch', lambda: __import__('torch').load('model/model.pt')),
                    ('cloudpickle', lambda: __import__('cloudpickle').load(open('model/model.cloudpickle', 'rb'))),
                    ('pickle', lambda: __import__('pickle').load(open('model/model.pickle', 'rb')))
                ]
                
                for method_name, load_func in try_methods:
                    try:
                        if os.path.exists(f'model/model.{{method_name.split(".")[-1]}}'):
                            self._model = load_func()
                            self._serialization_method = method_name
                            print(f"Successfully loaded model with {{method_name}}")
                            break
                    except Exception as method_error:
                        print(f"Failed to load with {{method_name}}: {{method_error}}")
                
                if self._model is None:
                    raise RuntimeError("Could not load model with any available method")
            
            self._is_loaded = True
            print(f"Successfully loaded model using {{self._serialization_method}}")
            
        except Exception as e:
            traceback.print_exc()
            raise RuntimeError(f"Failed to load model: {{str(e)}}")
        
    def _process_input(self, instances: List) -> Any:
        """Pre-process the input based on model type.
        
        Args:
            instances: List of input data
            
        Returns:
            Properly formatted data for the specific model type
        """
        # Framework-specific input processing
        if self._serialization_method == "pytorch":
            # Convert to PyTorch tensor
            try:
                import torch
                # Check if input is already a tensor
                if isinstance(instances, torch.Tensor):
                    return instances
                # Try to convert to tensor (handles numpy arrays and lists)
                return torch.tensor(instances, dtype=torch.float32)
            except Exception as e:
                print(f"Warning: Failed to convert input to PyTorch tensor: {{e}}")
                # Fall back to numpy
                return np.array(instances)
                
        elif self._serialization_method in ["tensorflow", "tensorflow-h5"]:
            # For TensorFlow, numpy arrays are appropriate
            try:
                import tensorflow as tf
                # Check if input is already a tensor
                if isinstance(instances, tf.Tensor):
                    return instances
                # Handle different input shapes
                array = np.array(instances)
                # Add batch dimension if needed and not already present
                if len(array.shape) == 1:
                    array = np.expand_dims(array, axis=0)
                return array
            except Exception as e:
                print(f"Warning: Failed to process TensorFlow input: {{e}}")
                return np.array(instances)
                
        elif self._serialization_method == "huggingface":
            # Hugging Face can take various input formats
            if all(isinstance(i, str) for i in instances):
                # Text inputs for NLP models - pass as is
                return instances
            elif all(isinstance(i, dict) for i in instances):
                # Dictionary inputs for tokenized data - pass as is
                return instances
            else:
                # Default to numpy array for other types
                return np.array(instances)
                
        else:
            # Default to numpy array for sklearn, xgboost, lightgbm, etc.
            return np.array(instances)
    
    def _process_output(self, predictions: Any) -> List:
        """Post-process model outputs to a standardized format.
        
        Args:
            predictions: Raw model predictions
            
        Returns:
            Processed predictions in a standard list format
        """
        # Framework-specific output processing
        if self._serialization_method == "pytorch":
            try:
                import torch
                # Convert PyTorch tensors to lists
                if isinstance(predictions, torch.Tensor):
                    # Move to CPU if on GPU
                    if predictions.is_cuda:
                        predictions = predictions.cpu()
                    # Detach from computation graph and convert to numpy then list
                    return predictions.detach().numpy().tolist()
                # Try to handle other PyTorch-specific outputs
                elif hasattr(predictions, 'logits') and isinstance(predictions.logits, torch.Tensor):
                    # Common in HuggingFace outputs
                    return predictions.logits.detach().cpu().numpy().tolist()
            except Exception as e:
                print(f"Warning: Failed to process PyTorch output: {{e}}")
                # Fall through to generic handlers
                
        elif self._serialization_method in ["tensorflow", "tensorflow-h5"]:
            try:
                import tensorflow as tf
                # Handle TensorFlow EagerTensor
                if isinstance(predictions, tf.Tensor):
                    return predictions.numpy().tolist()
                # Handle dictionary outputs (common in Keras models)
                elif isinstance(predictions, dict) and any(isinstance(v, tf.Tensor) for v in predictions.values()):
                    return {{k: v.numpy().tolist() if isinstance(v, tf.Tensor) else v 
                           for k, v in predictions.items()}}
            except Exception as e:
                print(f"Warning: Failed to process TensorFlow output: {{e}}")
                # Fall through to generic handlers
                
        elif self._serialization_method == "huggingface":
            # Handle various HuggingFace output types
            try:
                # Dictionary with tensors (common HF output format)
                if isinstance(predictions, dict):
                    processed = {{}}
                    for k, v in predictions.items():
                        if hasattr(v, 'numpy'):
                            processed[k] = v.numpy().tolist()
                        elif hasattr(v, 'tolist'):
                            processed[k] = v.tolist()
                        else:
                            processed[k] = v
                    return processed
            except Exception as e:
                print(f"Warning: Failed to process HuggingFace output: {{e}}")
                # Fall through to generic handlers
                
        # Generic output handling for all model types
        if isinstance(predictions, np.ndarray):
            return predictions.tolist()
        elif hasattr(predictions, 'tolist'):
            return predictions.tolist()
        elif isinstance(predictions, list):
            return predictions
        elif isinstance(predictions, dict):
            # Convert any numpy arrays in dict values to lists
            return {{k: v.tolist() if hasattr(v, 'tolist') else v 
                   for k, v in predictions.items()}}
        else:
            # Single value or unknown type
            return [predictions]
        
    def predict(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Predict with the model
        
        Args:
            request: Dictionary with 'instances' key containing input data
            
        Returns:
            Dictionary with 'predictions' key containing model predictions
            
        Raises:
            ValueError: If request format is invalid
            RuntimeError: If prediction fails
        """
        # Load the model if not already loaded
        if not self._is_loaded:
            self.load()
            
        try:
            # Validate request format
            if not isinstance(request, dict):
                raise ValueError(f"Request must be a dictionary, got {{type(request)}}")
                
            if "instances" not in request:
                raise ValueError("Request must contain 'instances' key")
                
            instances = request["instances"]
            if not isinstance(instances, list):
                raise ValueError(f"'instances' must be a list, got {{type(instances)}}")
                
            # Pre-process the input according to model type
            processed_input = self._process_input(instances)
            
            # Make prediction
            predictions = self._model.predict(processed_input)
            
            # Post-process the predictions to a standardized format
            processed_predictions = self._process_output(predictions)
            
            # Return predictions
            return {{"predictions": processed_predictions}}
            
        except Exception as e:
            # Log detailed error but return a clean message
            traceback.print_exc()
            if isinstance(e, ValueError):
                raise ValueError(f"Invalid request format: {{str(e)}}")
            else:
                raise RuntimeError(f"Prediction failed: {{str(e)}}")
'''

        model_py_path = os.path.join(model_dir, "model.py")
        try:
            with open(model_py_path, "w") as f:
                f.write(model_code.strip())
            logger.info(f"Created model.py at {model_py_path}")
        except Exception as e:
            logger.error(f"Failed to write model.py: {str(e)}")
            raise RuntimeError(f"Failed to write model.py: {str(e)}")

        # Verify the Truss directory structure is complete
        required_files = [
            os.path.join(truss_dir, "config.yaml"),
            os.path.join(model_dir, "model.py"),
        ]

        # At least one model file should exist based on serialization method
        model_file_exists = False
        possible_model_files = [
            os.path.join(model_dir, "model.joblib"),
            os.path.join(model_dir, "model.pt"),
            os.path.join(model_dir, "model.pickle"),
            os.path.join(model_dir, "model.cloudpickle"),
            os.path.join(model_dir, "model.h5"),
            os.path.join(model_dir, "tf_model"),
            os.path.join(model_dir, "hf_model"),
        ]

        for model_file in possible_model_files:
            if os.path.exists(model_file):
                model_file_exists = True
                break

        if not model_file_exists:
            raise RuntimeError(f"No model file was created in {model_dir}")

        # Check required files
        for file_path in required_files:
            if not os.path.exists(file_path):
                raise RuntimeError(
                    f"Required file {file_path} was not created"
                )

        logger.info(f"Successfully created Truss package at {truss_dir}")
        return truss_dir

    except Exception as e:
        # Clean up on failure if the directory was created
        if os.path.exists(truss_dir) and overwrite:
            try:
                logger.warning(
                    f"Cleaning up failed Truss directory: {truss_dir}"
                )
                shutil.rmtree(truss_dir)
            except Exception as cleanup_error:
                logger.error(
                    f"Failed to clean up directory: {str(cleanup_error)}"
                )

        # Re-raise with additional context
        if isinstance(e, (ValueError, RuntimeError)):
            raise
        else:
            raise RuntimeError(f"Error creating Truss package: {str(e)}")
