## Examples

Here you can find a list of practical examples on how you can use ZenML with brief descriptions for each example:

- **aws_orchestrated**: Runs pipeline on an EC2 instance on `Amazon Web Services` as the orchestration backend.
- **backends**: Showcases switching between various backends for different use-cases.
- **batch_inference**: Runs a batch inference pipeline using the result of a training pipeline.
- **bootstrapping**: Example on how to bootstrap different services on GCP for various backends using Terraform. 
- **collaboration**: How to collaborate using ZenML across multiple devices and teams.
- **cortex**: Tutorial on how to integrate with [Cortex](https://cortex.dev) to deploy your models.
- **batch_inference**: Run a offline batch inference job.
- **gan**: Tutorial on how to create and train a GAN model with a custom `TrainerStep` and `PreprocessorStep`.
- **gcp_dataflow_processing**: Showcases distributed preprocessing wth [Dataflow](https://cloud.google.com/dataflow) as the processing backend.
- **gcp_gcaip_deployment**: Deploying a classifier with [Google Cloud AI Platform](https://cloud.google.com/ai-platform).
- **gcp_gcaip_training**: Training a classifier with [Google Cloud AI Platform](https://cloud.google.com/ai-platform).
- **gcp_gpu_orchestrated**: Training a classifier on an (optionally preemtible) cuda-enabled Google Cloud Platform virtual machine.
- **gcp_kubernetes_orchestrated**: Launches a kubernetes job on a kubernetes cluster.
- **gcp_orchestrated**: Runs pipeline on an (optionally preemtible) virtual machine on `Google Cloud Platform` as the orchestration backend.
- **nlp**: Uses the awesome [HuggingFace](https://huggingface.co/) library to create a NLP Training pipeline.
- **pytorch**: Showcases PyTorch support.
- **pytorch_lightning**: Showcases [PyTorch Lightning](https://www.pytorchlightning.ai/) support.
- **quickstart**: The official quickstart tutorial.
- **regression**: Showcases a regression use-case.
- **scikit**: An example of using a [scikit-learn](https://scikit-learn.org/) trainer within ZenML.
- **simple_cv**: Show-cases a simple CV example using Tensorflow Datasets and MNIST.

In order to quickly run any of these examples, use the ZenML CLI:

```bash
# install CLI
pip install zenml

# initialize CLI
git init
zenml init

# pull example
zenml examples pull EXAMPLE_NAME
cd zenml_examples/EXAMPLE_NAME
```

Have any questions? Want more tutorials? Spot out-dated, frustrating tutorials? We got you covered!

Feel free to let us know by creating an 
[issue](https://github.com/maiot-io/zenml/issues) here on our Github or by reaching out to us on our 
[Slack](https://zenml.io/slack-invite/). 