# Pipeline Configuration

## Setting step parameters using Config

Sometimes you want to flexibly adjust parameters when you run your pipeline. This is where the step 
configurations come into play. In the following example we want to be able to change the learning rate for each 
pipeline run. For this, we create a `TrainerConfig` that contains all the parameters that concern the trainer step.



```python
import tensorflow as tf

from zenml.pipelines import pipeline
from zenml.steps import step, Output, BaseStepConfig

@step
def importer_func() -> Output(
    X_train=np.ndarray, y_train=np.ndarray, X_test=np.ndarray, y_test=np.ndarray
):
    """Importing data"""
    ...
    
class TrainerConfig(BaseStepConfig):
    """Trainer params"""
    lr: float = 0.001

@step
def trainer_func(
    config: TrainerConfig, # not an artifact, passed in when pipeline is instantiated
    X_train: np.ndarray,
    y_train: np.ndarray
):
    """Training model"""
    optimizer = tf.keras.optimizers.Adam(config.lr)
    ...

@pipeline
def my_pipeline(
    importer,
    trainer,
):
    """Links all the steps together in a pipeline"""
    X_train, y_train, X_test, y_test = importer()
    model = trainer(X_train=X_train, y_train=y_train)

pipeline_instance = my_pipeline(
            importer=importer_func(),
            trainer=trainer_func(config=TrainerConfig(lr=0.003))
            )
            
pipeline_instance.run()
```

## Setting step parameters using a config file

In addition to setting parameters for your pipeline steps in code as seen above, ZenML also allows you to use a 
configuration [yaml](https://yaml.org) file. This configuration file must follow the following structure:

```yaml
steps:
  step_name:
    parameters:
      parameter_name: parameter_value
      some_other_parameter_name: 2
  some_other_step_name:
    ...
```

For our example from above this results in the following configuration yaml.&#x20;

```yaml
steps:
  trainer:
    parameters:
      lr: 0.005
```

Use the configuration file by calling the pipeline method `with_config(...)`:

```python
pipeline_instance = my_pipeline(
            importer=importer_func(),
            trainer=trainer_func()
            ).with_config("path_to_config.yaml")
            
pipeline_instance.run()
```
