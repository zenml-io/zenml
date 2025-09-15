# :running: MLOps 101 with ZenML

Build your first production-ready MLOps pipelines with ZenML.

## :earth_americas: Overview

This repository is a comprehensive MLOps project that demonstrates the complete ML lifecycle from training to production deployment. It features: 

- A feature engineering pipeline that loads data and prepares it for training.
- A training pipeline that loads the preprocessed dataset and trains a model.
- A batch inference pipeline that runs predictions on the trained model with new data.
- **🆕 A deployment pipeline that deploys your model as an always-warm HTTP endpoint for real-time predictions.**

This is a representation of how it will all come together: 

<img src=".assets/pipeline_overview.png" width="70%" alt="Pipelines Overview">

Along the way we will also show you how to:

- Structure your code into MLOps pipelines.
- Automatically version, track, and cache data, models, and other artifacts.
- Transition your ML models from development to production.
- **🆕 Deploy pipelines as HTTP endpoints for real-time inference.**

## 🏃 Run on Colab

You can use Google Colab to see ZenML in action, no signup / installation required!

<a href="https://colab.research.google.com/github/zenml-io/zenml/blob/main/examples/mlops_starter/quickstart.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

## :computer: Run Locally

To run locally, install ZenML and pull this quickstart:

```shell
# Install ZenML
pip install "zenml[server]"

# clone the ZenML repository
git clone https://github.com/zenml-io/zenml.git
cd zenml/examples/mlops_starter
```

Now we're ready to start. You have two options for running the quickstart locally:

#### Option 1 - Interactively explore the quickstart using Jupyter Notebook:
```bash
pip install notebook
jupyter notebook
# open quickstart.ipynb
```

#### Option 2 - Execute the whole ML pipeline from a Python script:
```bash
# Install required zenml integrations
zenml integration install sklearn pandas -y

# Initialize ZenML
zenml init

# Start the ZenServer to enable dashboard access
zenml login --local

# Run the feature engineering pipeline
python run.py --feature-pipeline

# Run the training pipeline
python run.py --training-pipeline

# Run the training pipeline with versioned artifacts
python run.py --training-pipeline --train-dataset-version-name=1 --test-dataset-version-name=1

# Run the inference pipeline
python run.py --inference-pipeline

# Deploy directly with ZenML CLI
zenml pipeline deploy pipelines.inference --config configs/inference.yaml
```

## 🌵 Learning MLOps with ZenML

This project is also a great source of learning about some fundamental MLOps concepts. In sum, there are four exemplary steps happening, that can be mapped onto many other projects:

<details>
  <summary>🥇 Step 1: Load your data and execute feature engineering</summary>

We'll start off by importing our data. In this project, we'll be working with
[the Breast Cancer](https://archive.ics.uci.edu/dataset/17/breast+cancer+wisconsin+diagnostic) dataset
which is publicly available on the UCI Machine Learning Repository. The task is a classification
problem, to predict whether a patient is diagnosed with breast cancer or not.

When you're getting started with a machine learning problem you'll want to do
something similar to this: import your data and get it in the right shape for
your training. Here are the typical steps within a feature engineering pipeline.

The steps can be found defined the [steps](steps/) directory, while the [pipelines](pipelines/) directory has the pipeline code to connect them together.

<img src=".assets/feature_engineering_pipeline.png" width="50%" alt="Feature engineering pipeline" />

To execute the feature engineer pipelines, run:

```python
python run.py --feature-pipeline
```

After the pipeline has run, the pipeline will produce some logs like:

```shell
The latest feature engineering pipeline produced the following artifacts: 

1. Train Dataset - Name: dataset_trn, Version Name: 1 
2. Test Dataset: Name: dataset_tst, Version Name: 1
```

We will use these versions in the next pipeline.

</details>

<details>
  <summary>⌚ Step 2: Training pipeline</summary>

Now that our data is prepared, it makes sense to train some models to get a sense of how difficult the task is. The Breast Cancer dataset is sufficiently large and complex  that it's unlikely we'll be able to train a model that behaves perfectly since the problem is inherently complex, but we can get a sense of what a reasonable baseline looks like.

We'll start with two simple models, a SGD Classifier and a Random Forest
Classifier, both batteries-included from `sklearn`. We'll train them on the
same data and then compare their performance.

<img src=".assets/training_pipeline.png" width="50%" alt="Training pipeline">

Run it by using the ID's from the first step:

```python
# You can also ignore the `--train-dataset-version-name` and `--test-dataset-version-name` to use 
#  the latest versions
python run.py --training-pipeline --train-dataset-version-name 1 --test-dataset-version-name 1
```

To track these models, ZenML offers a *Model Control Plane*, which is a central register of all your ML models.
Each run of the training pipeline will produce a ZenML Model Version.

```shell
zenml model list
```

This will show you a new `breast_cancer_classifier` model with two versions, `sgd` and `rf` created. You can find out how this was configured in the [YAML pipeline configuration files](configs/).

If you are a [ZenML Pro](https://zenml.io/pro) user, you can see all of this visualized in the dashboard:

<img src=".assets/cloud_mcp_screenshot.png" width="70%" alt="Model Control Plane">

There is a lot more you can do with ZenML models, including the ability to
track metrics by adding metadata to it, or having them persist in a model
registry. However, these topics can be explored more in the
[ZenML docs](https://docs.zenml.io).

</details>

<details>
  <summary>💯 Step 3: Promoting the best model to production</summary>

For now, we will use the ZenML model control plane to promote our best
model to `production`. You can do this by simply setting the `stage` of
your chosen model version to the `production` tag.

```shell
zenml model version update breast_cancer_classifier rf --stage production
```

While we've demonstrated a manual promotion process for clarity, a more in-depth look at the [promoter code](steps/model_promoter.py) reveals that the training pipeline is designed to automate this step. It evaluates the latest model against established production metrics and, if the new model outperforms the existing one based on test set results, it will automatically promote the model to production. Here is an overview of the process:

<img src=".assets/cloud_mcp.png" width="60%" alt="Model Control Plane">

Again, if you are a [ZenML Pro](https://zenml.io/pro) user, you would be able to see all this in the cloud dashboard.

</details>

<details>
  <summary>🫅 Step 4: Consuming the model in production</summary>

Once the model is promoted, we can now consume the right model version in our
batch inference pipeline directly. Let's see how that works.

The batch inference pipeline simply takes the model marked as `production` and runs inference on it
with `live data`. The critical step here is the `inference_predict` step, where we load the model in memory and generate predictions. Apart from the loading the model, we must also load the preprocessing pipeline that we ran in feature engineering,
so that we can do the exact steps that we did on training time, in inference time. Let's bring it all together:

ZenML automatically links all artifacts to the `production` model version as well, including the predictions
that were returned in the pipeline. This completes the MLOps loop of training to inference:

<img src=".assets/inference_pipeline.png" width="45%" alt="Inference pipeline">

You can also see all predictions ever created as a complete history in the dashboard (Again only for [ZenML Pro](https://zenml.io/pro) users):

<img src=".assets/cloud_mcp_predictions.png" width="70%" alt="Model Control Plane">

</details>

<details>
  <summary>🚀 Step 5: Deploy Model as HTTP Endpoint (NEW!)</summary>

Now that we have a production model, we can deploy it as an always-warm HTTP endpoint for real-time predictions. This transforms our batch inference pipeline into a deploying endpoint that can handle live requests.

The deploying deployment uses the same inference pipeline but with a twist: it can accept input data directly as parameters instead of loading from sklearn. This makes it perfect for real-time deploying while maintaining the exact same preprocessing and prediction logic.

```bash
# Deploy the inference pipeline as a deploying endpoint
zenml pipeline deploy pipelines.inference --config configs/inference.yaml
```

Once deployed, you can test the endpoint:

```bash
# Test the deployed endpoint
python test_deploying.py --url http://your-endpoint-url
```

The endpoint accepts POST requests to `/invoke` with breast cancer feature data:

```json
{
  "input_data": [
    [17.99, 10.38, 122.8, ..., 0.1189],
    [20.57, 17.77, 132.9, ..., 0.08902]
  ],
  "random_state": 42,
  "target": "target"
}
```

And returns predictions with metadata:

```json
{
  "success": true,
  "outputs": {
    "predictions": [0, 1]
  },
  "execution_time": 0.123,
  "metadata": {
    "pipeline_name": "inference",
    "run_id": "...",
    "parameters_used": {...}
  }
}
```

**Key deploying features:**
- **Model Preloading**: The model and preprocessor are loaded once at startup using init hooks, ensuring fast response times
- **Real-time Inference**: Same pipeline logic as batch inference but optimized for deploying
- **API Documentation**: Automatic OpenAPI/Swagger docs at `/docs`
- **Health Monitoring**: Built-in health checks at `/health`
- **Input Validation**: Pydantic model validation for robust request handling

This completes the full MLOps loop: from data ingestion and training to production deploying with real-time inference capabilities.

</details>

## :bulb: Learn More

You're a legit MLOps engineer now! You've completed the full ML lifecycle:

🎯 **Training**: Trained and compared multiple models (SGD vs Random Forest)  
📊 **Evaluation**: Evaluated models against test data and metrics  
🏆 **Promotion**: Registered the best model to the production stage  
📦 **Batch Inference**: Made predictions on new data using batch pipelines  
🚀 **Real-time deploying**: Deployed your model as an always-warm HTTP endpoint  

You also learned how to iterate on your models and data by using ZenML's powerful abstractions for versioning, caching, and lineage tracking. You saw how to view your artifacts and stacks via the client as well as the ZenML Dashboard.

If you want to learn more about ZenML as a tool, then the
[:page_facing_up: **ZenML Docs**](https://docs.zenml.io/) are the perfect place
to get started. In particular, the [Production Guide](https://docs.zenml.io/user-guide/production-guide/)
goes into more detail as to how to transition these same pipelines into production on the cloud.

The best way to get a production ZenML instance up and running with all batteries included is the [ZenML Pro](https://zenml.io/pro). Check it out!

Also, make sure to join our <a href="https://zenml.io/slack" target="_blank">
    <img width="15" src="https://cdn3.iconfinder.com/data/icons/logos-and-brands-adobe/512/306_Slack-512.png" alt="Slack"/>
    <b>Slack Community</b> 
</a> to become part of the ZenML family!
