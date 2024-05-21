# Model Versions

Each model can have many versions. Model versions are a way for you to track different iterations of your training process, complete with some extra dashboard and API functionality to support the full ML lifecycle.

### When are model versions created?

Model versions are created implicitly as you are running your machine learning training, so you don't have to immediately think about this. If you want more control over versions, our API has you covered, with an option to explicitly name your versions.

### Explicitly name your model version

If you want to explicitly name your model version, you can do so by passing in the `version` argument to the `Model` object. If you don't do this, ZenML will automatically generate a version number for you.

```python
from zenml import Model, step, pipeline

model= Model(
    name="my_model",
    version="1.0.5"
)

# The step configuration will take precedence over the pipeline
@step(model=model)
def svc_trainer(...) -> ...:
    ...

# This configures it for all steps within the pipeline
@pipeline(model=model)
def training_pipeline( ... ):
    # training happens here
```

Here we are specifically setting the model configuration for a particular step or for the pipeline as a whole.

### Autonumbering of versions

ZenML automatically numbers your model versions for you. If you don't specify a version number, or if you pass `None` into the `version` argument of the `Model` object, ZenML will automatically generate a version number (or a new version, if you already have a version) for you. For example if we had a model version `really_good_version` for model `my_model` and we wanted to create a new version of this model, we could do so as follows:

```python
from zenml import Model, step

model = Model(
    name="my_model",
    version="even_better_version"
)

@step(model=model)
def svc_trainer(...) -> ...:
    ...
```

A new model version will be created and ZenML will track that this is the next in the iteration sequence of the models using the `number` property. If `really_good_version` was the 5th version of `my_model`, then `even_better_version` will be the 6th version of `my_model`.

```python
from zenml import Model

earlier_version = Model(
    name="my_model",
    version="really_good_version"
).number # == 5

updated_version = Model(
    name="my_model",
    version="even_better_version"
).number # == 6
```
