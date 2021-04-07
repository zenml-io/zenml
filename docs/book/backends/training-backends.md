# Training Backends

ZenML has built-in support for dedicated training backends. These are backends specifically built to provide an edge for training models, e.g. through the availability of GPUs/TPUs, or other performance optimizations.

To use them, simply define your `TrainerStep` along with a `TrainingBackend` for different use-cases.

## Supported Training Backends

### Google Cloud AI platform

Google offers a dedicated service for training models with access to GPUs and TPUs called [Google Cloud AI Platform](https://cloud.google.com/ai-platform/docs). ZenML has built-in support to run `TrainingSteps` on Google Cloud AI Platform.

**Prerequisites:**

* [Enable billing](https://cloud.google.com/billing/docs/how-to/modify-project#enable_billing_for_a_project) in your Google Cloud Platform project.
* Make sure you have permissions to launch a training Job on Google AI Platform.
* Make sure you enable the following APIs:
  * Google Cloud AI Platform
  * Cloud SQL
  * Cloud Storage

**Usage:**

```python
from zenml.backends.training import SingleGPUTrainingGCAIPBackend
from zenml.steps.trainer import TFFeedForwardTrainer

(...)

# Add a trainer with a GCAIP backend
training_backend = SingleGPUTrainingGCAIPBackend(
  project=GCP_PROJECT,
  job_dir=TRAINING_JOB_DIR
)

training_pipeline.add_trainer(
  TFFeedForwardTrainer(...).with_backend(training_backend))
```

### AWS Sagemaker

Support for AWS Sagemaker is coming soon. Stay tuned to our releases, or let us know on [Slack](https://zenml.io/slack-invite/) if you have an urgent use-case for AWS Sagemaker!

If you would like to see any of this functionality earlier, or if you're missing a specific backend, please let us know via our [Slack Channel](https://zenml.io/slack-invite/) or [create an issue on GitHub](https://https://github.com/maiot-io/zenml).

