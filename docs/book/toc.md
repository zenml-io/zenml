# Table of contents

* [Introduction](index.md)

## Getting Started

* [Installation](getting-started/installation.md)
* [Quickstart](getting-started/quickstart.md)
* [Core Concepts](getting-started/core-concepts.md)
* [Organizing ML Code with ZenML](getting-started/organizing-zenml.md)
* [Creating custom logic](getting-started/creating-custom-logic.md)

## Benefits

* [Installation](benefits/installation.md)
* [Quickstart](benefits/quickstart.md)
* [Core Concepts](benefits/core-concepts.md)
* [Organizing ML Code with ZenML](benefits/organizing-zenml.md)

## Repository

* [What is a ZenML Repository](repository/what-is-a-repository.md)
* [The ZenML Repository Instance](repository/the-zenml-repository-instance.md)
* [Integration with Git](repository/integration-with-git.md)
* [Metadata Store](repository/metadata-store.md)
* [Artifact Store](repository/artifact-store.md)
* [Pipeline Directory](repository/pipeline-directory.md)
* [Team Collaboration](repository/team-collaboration-with-zenml.md)

## Datasources

* [What is a datasource](datasources/what-is-a-datasource.md)
* [Google Bigquery](datasources/google-bigquery.md)
* [Images](datasources/images.md)
* [CSV files](datasources/csv-files-locally.md)

## Pipelines

* [What is a pipeline?](pipelines/what-is-a-pipeline.md)
* [Training](pipelines/training.md)
* [Data \[WIP\]](pipelines/data.md)
* [Batch Inference \[WIP\]](pipelines/batch-inference.md)
* [Scheduling Jobs](pipelines/scheduling-jobs.md)

## Steps

* [Installation](steps/installation.md)
* [Quickstart](steps/quickstart.md)
* [Core Concepts](steps/core-concepts.md)
* [Organizing ML Code with ZenML](steps/organizing-zenml.md)

## Backends

* [What is a backend?](backends/what-is-a-backend.md)
* [Orchestrator Backends](backends/orchestrator-backends.md)
* [Processing Backends](backends/processing-backends.md)
* [Training Backends](backends/training-backends.md)
* [Using Docker](backends/using-docker.md)

## Tutorials

* [Creating your first pipeline](tutorials/creating-first-pipeline.md)
* [Running a pipeline on Google Cloud VM](tutorials/running-a-pipeline-on-a-google-cloud-vm.md)
* [Running a pipeline on Kubernetes](tutorials/running-a-pipeline-on-kubernetes.md)
* [Team collaboration with ZenML and Google Cloud](tutorials/team-collaboration-with-zenml-and-google-cloud.md)
* [Style Transfer using a CycleGAN](tutorials/style-transfer-using-a-cyclegan.md)
* [Classification with 59M samples](tutorials/building-a-classifier-on-33m-samples.md)

## Misc

* [Roadmap](misc/roadmap.md)
* [Changelogs](misc/changelogs.md)
* [Usage Analytics](misc/usage-analytics.md)

## Support

* [Contact](support/contact.md)
* [FAQ](support/faq-wip.md)

## API Reference

* [Zenml](api-reference/zenml/README.md)
  * [Backends](api-reference/zenml/zenml.backends/README.md)
    * [Orchestrator](api-reference/zenml/zenml.backends/zenml.backends.orchestrator/README.md)
      * [Kubeflow](api-reference/zenml/zenml.backends/zenml.backends.orchestrator/zenml.backends.orchestrator.kubeflow.md)
      * [Kubernetes](api-reference/zenml/zenml.backends/zenml.backends.orchestrator/zenml.backends.orchestrator.kubernetes.md)
    * [Processing](api-reference/zenml/zenml.backends/zenml.backends.processing.md)
    * [Training](api-reference/zenml/zenml.backends/zenml.backends.training.md)
  * [Cli](api-reference/zenml/zenml.cli.md)
  * [Components](api-reference/zenml/zenml.components/README.md)
    * [Pusher](api-reference/zenml/zenml.components/zenml.components.pusher.md)
    * [Sequencer](api-reference/zenml/zenml.components/zenml.components.sequencer.md)
    * [Split gen](api-reference/zenml/zenml.components/zenml.components.split_gen.md)
    * [Tokenizer](api-reference/zenml/zenml.components/zenml.components.tokenizer.md)
    * [Trainer](api-reference/zenml/zenml.components/zenml.components.trainer.md)
    * [Transform](api-reference/zenml/zenml.components/zenml.components.transform.md)
    * [Transform simple](api-reference/zenml/zenml.components/zenml.components.transform_simple.md)
  * [Datasources](api-reference/zenml/zenml.datasources.md)
  * [Metadata](api-reference/zenml/zenml.metadata.md)
  * [Pipelines](api-reference/zenml/zenml.pipelines.md)
  * [Repo](api-reference/zenml/zenml.repo.md)
  * [Standards](api-reference/zenml/zenml.standards.md)
  * [Steps](api-reference/zenml/zenml.steps/README.md)
    * [Inferrer](api-reference/zenml/zenml.steps/zenml.steps.inferrer.md)
    * [Preprocesser](api-reference/zenml/zenml.steps/zenml.steps.preprocesser/README.md)
      * [Standard preprocesser](api-reference/zenml/zenml.steps/zenml.steps.preprocesser/zenml.steps.preprocesser.standard_preprocesser/README.md)
        * [Methods](api-reference/zenml/zenml.steps/zenml.steps.preprocesser/zenml.steps.preprocesser.standard_preprocesser/zenml.steps.preprocesser.standard_preprocesser.methods.md)
    * [Sequencer](api-reference/zenml/zenml.steps/zenml.steps.sequencer/README.md)
      * [Standard sequencer](api-reference/zenml/zenml.steps/zenml.steps.sequencer/zenml.steps.sequencer.standard_sequencer/README.md)
        * [Methods](api-reference/zenml/zenml.steps/zenml.steps.sequencer/zenml.steps.sequencer.standard_sequencer/zenml.steps.sequencer.standard_sequencer.methods.md)
    * [Split](api-reference/zenml/zenml.steps/zenml.steps.split.md)
    * [Tokenizer](api-reference/zenml/zenml.steps/zenml.steps.tokenizer.md)
    * [Trainer](api-reference/zenml/zenml.steps/zenml.steps.trainer/README.md)
      * [Pytorch trainers](api-reference/zenml/zenml.steps/zenml.steps.trainer/zenml.steps.trainer.pytorch_trainers.md)
      * [Tensorflow trainers](api-reference/zenml/zenml.steps/zenml.steps.trainer/zenml.steps.trainer.tensorflow_trainers.md)
  * [Utils](api-reference/zenml/zenml.utils/README.md)
    * [Post training](api-reference/zenml/zenml.utils/zenml.utils.post_training.md)

