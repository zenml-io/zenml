# Model Versions

Each model can have many versions. Model versions are a way for you to track different iterations of your training process, complete with some extra dashboard and API functionality to support the full ML lifecycle.

E.g. Based on your business rules during training, you can associate model version with stages and promote them to production. You have an interface that allows you to link these versions with non-technical artifacts and data, e.g. business data, datasets, or even stages in your process and workflow.

Model versions are created implicitly as you are running your machine learning training, so you don't have to immediately think about this. If you want more control over versions, our API has you covered, with an option to explicitly name your versions.

## Explicitly name your model version

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

{% hint style="info" %}
Please note in the above example if the model version exists, it is automatically associated with the pipeline and becomes active in the pipeline context. Therefore, a user should be careful and intentional as to whether you want to create a new pipeline, or fetch an existing one. See below for an example of fetching a model from an existing version/stage.
{% endhint %}

## Use name templates for your model versions

If you want to continuously run the same project, but keep track of your model versions using semantical naming, you can rely on templated naming in the `version` and/or `name` argument to the `Model` object. Instead of static model version name from the previous section, templated names will be unique with every new run, but also will be semantically searchable and readable by your team.

```python
from zenml import Model, step, pipeline

model= Model(
    name="{team}_my_model",
    version="experiment_with_phi_3_{date}_{time}"
)

# The step configuration will take precedence over the pipeline
@step(model=model)
def llm_trainer(...) -> ...:
    ...

# This configures it for all steps within the pipeline
@pipeline(model=model, substitutions={"team": "Team_A"})
def training_pipeline( ... ):
    # training happens here
```

Here we are specifically setting the model configuration for a particular step or for the pipeline as a whole. Once you run this pipeline it will produce a model version with a name evaluated at a runtime, like `experiment_with_phi_3_2024_08_30_12_42_53`. Subsequent runs will have the same name of the model and model version, since the substitutions like `time` and `date` are evaluated for the whole pipeline run. We also used a custom substitution via `{team}` placeholder and set it to `Team_A` in the `pipeline` decorator.

{% hint style="info" %}
The substitutions for the custom placeholders like `team` can be set in:
- `@pipeline` decorator, so they are effective for all steps in this pipeline
- `pipeline.with_options` function, so they are effective for all steps in this pipeline run
- `@step` decorator, so they are effective for this step (this overrides the pipeline settings)
- `step.with_options` function, so they are effective for this step run (this overrides the pipeline settings)

Standard substitutions always available and consistent in all steps of the pipeline are:
- `{date}`: current date, e.g. `2024_11_27`
- `{time}`: current time in UTC format, e.g. `11_07_09_326492`
{% endhint %}

## Fetching model versions by stage

A common pattern is to assign a special `stage` to a model version, i.e. `production`, `staging`, `development` etc. This marks this version especially, and can be used to fetch it using a particular semantic meaning, disconnected from the concrete model version. A model version can be assigned a particular stage in the dashboard or by executing the following command in the CLI:

```shell
zenml model version update MODEL_NAME --stage=STAGE
```

These stages can then be passed in as a `version` to fetch the right model version at a later point:


```python
from zenml import Model, step, pipeline

model= Model(
    name="my_model",
    version="production"
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

## Autonumbering of versions

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
<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>