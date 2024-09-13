# zenml.integrations.seldon.custom_deployer package

## Submodules

## zenml.integrations.seldon.custom_deployer.zenml_custom_model module

Implements a custom model for the Seldon integration.

### *class* zenml.integrations.seldon.custom_deployer.zenml_custom_model.ZenMLCustomModel(model_name: str, model_uri: str, predict_func: str)

Bases: `object`

Custom model class for ZenML and Seldon.

This class is used to implement a custom model for the Seldon Core integration,
which is used as the main entry point for custom code execution.

Attributes:
: name: The name of the model.
  model_uri: The URI of the model.
  predict_func: The predict function of the model.

#### load() → bool

Load the model.

This function loads the model into memory and sets the ready flag to True.
The model is loaded using the materializer, by saving the information of
the artifact to a file at the preparing time and loading it again at the
prediction time by the materializer.

Returns:
: True if the model was loaded successfully, False otherwise.

#### predict(X: ndarray[Any, Any] | List[Any] | str | bytes | Dict[str, Any], features_names: List[str] | None, \*\*kwargs: Any) → ndarray[Any, Any] | List[Any] | str | bytes | Dict[str, Any]

Predict the given request.

The main predict function of the model. This function is called by the
Seldon Core server when a request is received. Then inside this function,
the user-defined predict function is called.

Args:
: X: The request to predict in a dictionary.
  features_names: The names of the features.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Additional arguments.

Returns:
: The prediction dictionary.

Raises:
: Exception: If function could not be called.
  NotImplementedError: If the model is not ready.
  TypeError: If the request is not a dictionary.

## Module contents

Initialization of ZenML custom deployer.
