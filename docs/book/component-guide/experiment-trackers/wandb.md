---
description: Logging and visualizing experiments with Weights & Biases.
---

# Weights & Biases

The Weights & Biases Experiment Tracker is an [Experiment Tracker](./) flavor provided with the Weights & Biases ZenML integration that uses [the Weights & Biases experiment tracking platform](https://wandb.ai/site/experiment-tracking) to log and visualize information from your pipeline steps (e.g. models, parameters, metrics).

### When would you want to use it?

[Weights & Biases](https://wandb.ai/site/experiment-tracking) is a very popular platform that you would normally use in the iterative ML experimentation phase to track and visualize experiment results. That doesn't mean that it cannot be repurposed to track and visualize the results produced by your automated pipeline runs, as you make the transition towards a more production-oriented workflow.

You should use the Weights & Biases Experiment Tracker:

* if you have already been using Weights & Biases to track experiment results for your project and would like to continue doing so as you are incorporating MLOps workflows and best practices in your project through ZenML.
* if you are looking for a more visually interactive way of navigating the results produced from your ZenML pipeline runs (e.g. models, metrics, datasets)
* if you would like to connect ZenML to Weights & Biases to share the artifacts and metrics logged by your pipelines with your team, organization, or external stakeholders

You should consider one of the other [Experiment Tracker flavors](./#experiment-tracker-flavors) if you have never worked with Weights & Biases before and would rather use another experiment tracking tool that you are more familiar with.

### How do you deploy it?

The Weights & Biases Experiment Tracker flavor is provided by the W\&B ZenML integration, you need to install it on your local machine to be able to register a Weights & Biases Experiment Tracker and add it to your stack:

```shell
zenml integration install wandb -y
```

The Weights & Biases Experiment Tracker needs to be configured with the credentials required to connect to the Weights & Biases platform using one of the [available authentication methods](wandb.md#authentication-methods).

#### Authentication Methods

You need to configure the following credentials for authentication to the Weights & Biases platform:

* `api_key`: Mandatory API key token of your Weights & Biases account.
* `project_name`: The name of the project where you're sending the new run. If the project is not specified, the run is put in an "Uncategorized" project.
* `entity`: An entity is a username or team name where you're sending runs. This entity must exist before you can send runs there, so make sure to create your account or team in the UI before starting to log runs. If you don't specify an entity, the run will be sent to your default entity, which is usually your username.

{% tabs %}
{% tab title="Basic Authentication" %}
This option configures the credentials for the Weights & Biases platform directly as stack component attributes.

{% hint style="warning" %}
This is not recommended for production settings as the credentials won't be stored securely and will be clearly visible in the stack configuration.
{% endhint %}

```shell
# Register the Weights & Biases experiment tracker
zenml experiment-tracker register wandb_experiment_tracker --flavor=wandb \ 
    --entity=<entity> --project_name=<project_name> --api_key=<key>

# Register and set a stack with the new experiment tracker
zenml stack register custom_stack -e wandb_experiment_tracker ... --set
```
{% endtab %}

{% tab title="ZenML Secret (Recommended)" %}
This method requires you to [configure a ZenML secret](https://docs.zenml.io/how-to/project-setup-and-management/interact-with-secrets) to store the Weights & Biases tracking service credentials securely.

You can create the secret using the `zenml secret create` command:

```shell
zenml secret create wandb_secret \
    --entity=<ENTITY> \
    --project_name=<PROJECT_NAME>
    --api_key=<API_KEY>
```

Once the secret is created, you can use it to configure the wandb Experiment Tracker:

```shell
# Reference the entity, project and api-key in our experiment tracker component
zenml experiment-tracker register wandb_tracker \
    --flavor=wandb \
    --entity={{wandb_secret.entity}} \
    --project_name={{wandb_secret.project_name}} \
    --api_key={{wandb_secret.api_key}}
    ...
```

{% hint style="info" %}
Read more about [ZenML Secrets](https://docs.zenml.io/how-to/project-setup-and-management/interact-with-secrets) in the ZenML documentation.
{% endhint %}
{% endtab %}
{% endtabs %}

For more, up-to-date information on the Weights & Biases Experiment Tracker implementation and its configuration, you can have a look at [the SDK docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-wandb.html#zenml.integrations.wandb) .

### How do you use it?

To be able to log information from a ZenML pipeline step using the Weights & Biases Experiment Tracker component in the active stack, you need to enable an experiment tracker using the `@step` decorator. Then use Weights & Biases logging or auto-logging capabilities as you would normally do, e.g.:

```python
import wandb
from wandb.integration.keras import WandbCallback


@step(experiment_tracker="<WANDB_TRACKER_STACK_COMPONENT_NAME>")
def tf_trainer(
    config: TrainerConfig,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
) -> tf.keras.Model:
    ...

    model.fit(
        x_train,
        y_train,
        epochs=config.epochs,
        validation_data=(x_val, y_val),
        callbacks=[
            WandbCallback(
                log_evaluation=True,
                validation_steps=16,
                validation_data=(x_val, y_val),
            )
        ],
    )

    metric = ...

    wandb.log({"<METRIC_NAME>": metric})
```

{% hint style="info" %}
Instead of hardcoding an experiment tracker name, you can also use the [Client](https://docs.zenml.io/reference/python-client) to dynamically use the experiment tracker of your active stack:

```python
from zenml.client import Client

experiment_tracker = Client().active_stack.experiment_tracker

@step(experiment_tracker=experiment_tracker.name)
def tf_trainer(...):
    ...
```
{% endhint %}

### Weights & Biases UI

Weights & Biases comes with a web-based UI that you can use to find further details about your tracked experiments.

Every ZenML step that uses Weights & Biases should create a separate experiment run which you can inspect in the Weights & Biases UI:

![WandB UI](../../.gitbook/assets/WandBUI.png)

You can find the URL of the Weights & Biases experiment linked to a specific ZenML run via the metadata of the step in which the experiment tracker was used:

```python
from zenml.client import Client

last_run = client.get_pipeline("<PIPELINE_NAME>").last_run
trainer_step = last_run.steps["<STEP_NAME>"]
tracking_url = trainer_step.run_metadata["experiment_tracker_url"].value
print(tracking_url)
```

Or on the ZenML dashboard as metadata of a step that uses the tracker:

![WandB UI](../../.gitbook/assets/wandb_dag.png)

Alternatively, you can see an overview of all experiment runs at https://wandb.ai/{ENTITY\_NAME}/{PROJECT\_NAME}/runs/.

{% hint style="info" %}
The naming convention of each Weights & Biases experiment run is `{pipeline_run_name}_{step_name}` (e.g. `wandb_example_pipeline-25_Apr_22-20_06_33_535737_tf_evaluator`) and each experiment run will be tagged with both `pipeline_name` and `pipeline_run_name`, which you can use to group and filter experiment runs.
{% endhint %}

#### Additional configuration

For additional configuration of the Weights & Biases experiment tracker, you can pass `WandbExperimentTrackerSettings` to overwrite the [wandb.Settings](https://github.com/wandb/client/blob/master/wandb/sdk/wandb_settings.py#L353) or pass additional tags for your runs:

```python
import wandb
from zenml.integrations.wandb.flavors.wandb_experiment_tracker_flavor import WandbExperimentTrackerSettings

wandb_settings = WandbExperimentTrackerSettings(
    settings=wandb.Settings(...),
    tags=["some_tag"],
    enable_weave=True, # Enable Weave integration
)


@step(
    experiment_tracker="<WANDB_TRACKER_STACK_COMPONENT_NAME>",
    settings={
        "experiment_tracker": wandb_settings
    }
)
def my_step(
    x_test: np.ndarray,
    y_test: np.ndarray,
    model: tf.keras.Model,
) -> float:
    """Everything in this step is auto-logged"""
    ...
```

### Using Weights & Biases Weave

[Weights & Biases Weave](https://weave-docs.wandb.ai/) is a customizable dashboard interface that allows you to visualize and interact with your machine learning models, data, and results. ZenML provides built-in support for Weave through the `WandbExperimentTrackerSettings`.

#### Enabling and Disabling Weave

You can enable or disable Weave for specific steps in your pipeline by configuring the `enable_weave` parameter in the `WandbExperimentTrackerSettings` (or setting it when registering the experiment tracker component):

```python
import weave
from openai import OpenAI

from zenml import pipeline, step
from zenml.integrations.wandb.flavors.wandb_experiment_tracker_flavor import (
    WandbExperimentTrackerSettings,
)

# Settings to enable Weave
wandb_with_weave_settings = WandbExperimentTrackerSettings(
    tags=["weave_enabled"],
    enable_weave=True,  # Enable Weave integration
)

# Settings to disable Weave
wandb_without_weave_settings = WandbExperimentTrackerSettings(
    tags=["weave_disabled"],
    enable_weave=False,  # Explicitly disable Weave integration
)
```

#### Using Weave with ZenML Steps

To use Weave with your ZenML steps, you need to:

1. Configure your `WandbExperimentTrackerSettings` with `enable_weave=True`
2. Apply the `@weave.op()` decorator to your step function
3. Configure your step to use the Weights & Biases experiment tracker with your Weave settings

Here's an example:

```python
@step(
    experiment_tracker="wandb_weave",  # Your W&B experiment tracker component name
    settings={"experiment_tracker": wandb_with_weave_settings},
)
@weave.op()  # The Weave decorator
def my_step_with_weave() -> str:
    """This step will use Weave for enhanced visualization"""
    # Your step implementation
    return "Step with Weave enabled"
```

{% hint style="warning" %}
**Important**: The decorator order is critical. The `@weave.op()` decorator must be applied AFTER the `@step` decorator (i.e., closer to the function definition). If you reverse the order, your step won't work correctly.

```python
# CORRECT ORDER
@step(experiment_tracker="wandb_weave")
@weave.op()
def correct_order_step():
    ...

# INCORRECT ORDER - will cause issues
@weave.op()
@step(experiment_tracker="wandb_weave")
def incorrect_order_step():
    ...
```
{% endhint %}

To explicitly disable Weave for specific steps, while keeping the ability to use the `@weave.op()` decorator:

```python
@step(
    experiment_tracker="wandb_weave",
    settings={"experiment_tracker": wandb_without_weave_settings},
)
@weave.op()
def my_step_without_weave() -> str:
    """This step will not use Weave even with the @weave.op() decorator"""
    # Your step implementation
    return "Step with Weave disabled"
```

#### Weave Initialization Behavior

When using Weave with ZenML, there are a few important behaviors to understand:

1. If `enable_weave=True` and a `project_name` is specified in your W\&B experiment tracker, Weave will be initialized with that project name.
2. If `enable_weave=True` but no `project_name` is specified, Weave initialization will be skipped.
3. If `enable_weave=False` and a `project_name` is specified (explicit disabling), Weave will be disabled with `settings={"disabled": True}`.
4. If `enable_weave=False` and no `project_name` is specified, Weave disabling will be skipped.

{% hint style="info" %}
For more information about Weights & Biases Weave and its capabilities, visit the [Weave documentation](https://docs.wandb.ai/guides/weave).
{% endhint %}

## Full Code Example

This section shows an end to end run with the ZenML W\&B integration.

<details>

<summary>Example without Weave</summary>

```python
from typing import Tuple
from zenml import pipeline, step
from zenml.client import Client
from zenml.integrations.wandb.flavors.wandb_experiment_tracker_flavor import (
    WandbExperimentTrackerSettings,
)
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
    DistilBertForSequenceClassification,
)
from datasets import load_dataset, Dataset
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import wandb

# Get the experiment tracker from the active stack
experiment_tracker = Client().active_stack.experiment_tracker

@step
def prepare_data() -> Tuple[Dataset, Dataset]:
    dataset = load_dataset("imdb")
    tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
    def tokenize_function(examples):
        return tokenizer(examples["text"], padding="max_length", truncation=True)
    tokenized_datasets = dataset.map(tokenize_function, batched=True)
    return (
        tokenized_datasets["train"].shuffle(seed=42).select(range(1000)),
        tokenized_datasets["test"].shuffle(seed=42).select(range(100)),
    )


# Train the model
@step(experiment_tracker=experiment_tracker.name)
def train_model(
    train_dataset: Dataset, eval_dataset: Dataset
) -> DistilBertForSequenceClassification:

    model = AutoModelForSequenceClassification.from_pretrained(
        "distilbert-base-uncased", num_labels=2
    )

    training_args = TrainingArguments(
        output_dir="./results",
        num_train_epochs=3,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir="./logs",
        evaluation_strategy="epoch",
        logging_steps=100,
        report_to=["wandb"],
    )

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        predictions = np.argmax(logits, axis=-1)
        precision, recall, f1, _ = precision_recall_fscore_support(
            labels, predictions, average="binary"
        )
        acc = accuracy_score(labels, predictions)
        return {"accuracy": acc, "f1": f1, "precision": precision, "recall": recall}

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        compute_metrics=compute_metrics,
    )

    trainer.train()

    # Evaluate the model
    eval_results = trainer.evaluate()
    print(f"Evaluation results: {eval_results}")

    # Log final evaluation results
    wandb.log({"final_evaluation": eval_results})

    return model


@pipeline(enable_cache=False)
def fine_tuning_pipeline():
    train_dataset, eval_dataset = prepare_data()
    model = train_model(train_dataset, eval_dataset)


if __name__ == "__main__":
    # Run the pipeline
    wandb_settings = WandbExperimentTrackerSettings(
        tags=["distilbert", "imdb", "sentiment-analysis"],
    )

    fine_tuning_pipeline.with_options(settings={"experiment_tracker": wandb_settings})()
```

</details>

<details>

<summary>Example with Weave for LLM Tracing</summary>

```python
import weave
from openai import OpenAI
import numpy as np
from sklearn.metrics import accuracy_score
import pandas as pd

from zenml import pipeline, step
from zenml.client import Client
from zenml.integrations.wandb.flavors.wandb_experiment_tracker_flavor import (
    WandbExperimentTrackerSettings,
)

# Get the experiment tracker from the active stack
experiment_tracker = Client().active_stack.experiment_tracker

# Create settings for Weave-enabled tracking
weave_settings = WandbExperimentTrackerSettings(
    tags=["weave_example", "llm_pipeline"],
    enable_weave=True,
)

# OpenAI client for LLM calls
openai_client = OpenAI()

@step
def prepare_data() -> pd.DataFrame:
    """Prepare sample data for LLM processing"""
    data = {
        "id": range(10),
        "text": [
            "I love this product, it's amazing!",
            "This was a waste of money, terrible.",
            "Pretty good, but could be improved.",
            "Not worth the price, disappointed.",
            "Absolutely fantastic experience!",
            "It's okay, nothing special though.",
            "Would definitely recommend to others.",
            "Had some issues, but support was helpful.",
            "Don't buy this, it doesn't work properly.",
            "Perfect for my needs, very satisfied."
        ]
    }
    return pd.DataFrame(data)

@step(
    experiment_tracker=experiment_tracker.name,
    settings={"experiment_tracker": weave_settings},
)
@weave.op()  # Weave decorator AFTER the step decorator
def classify_sentiment(data: pd.DataFrame) -> pd.DataFrame:
    """Classify the sentiment of each text using an LLM"""
    results = []
    
    for _, row in data.iterrows():
        prompt = f"Classify the sentiment of this text as POSITIVE, NEGATIVE, or NEUTRAL: '{row['text']}'"
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        
        sentiment = response.choices[0].message.content.strip()
        results.append({
            "id": row["id"],
            "text": row["text"],
            "sentiment": sentiment,
        })
    
    # Create a DataFrame with results
    result_df = pd.DataFrame(results)
    
    # Log some metrics to Wandb
    sentiments = result_df["sentiment"].value_counts()
    import wandb
    wandb.log({
        "positive_count": sentiments.get("POSITIVE", 0),
        "negative_count": sentiments.get("NEGATIVE", 0),
        "neutral_count": sentiments.get("NEUTRAL", 0),
        "sample_data": wandb.Table(dataframe=result_df),
    })
    
    return result_df


@pipeline(enable_cache=False)
def sentiment_analysis_pipeline():
    """Pipeline for sentiment analysis with Weave tracking"""
    data = prepare_data()
    results = classify_sentiment(data)

if __name__ == "__main__":
    # Set pipeline-level settings
    pipeline_settings = {
        "experiment_tracker": WandbExperimentTrackerSettings(
            tags=["sentiment_analysis_pipeline"],
            enable_weave=True,
        )
    }
    
    # Run the pipeline with the settings
    sentiment_analysis_pipeline.with_options(settings=pipeline_settings)()
```

</details>

Check out the [SDK docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-wandb.html#zenml.integrations.wandb) for a full list of available attributes and [this docs page](https://docs.zenml.io/concepts/steps_and_pipelines/configuration) for more information on how to specify settings.
