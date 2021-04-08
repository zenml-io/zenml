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

* [Zenml](../sphinx_docs/_build/html/zenml.html)
  * [Backends](../sphinx_docs/_build/html/zenml.backends.html)
    * [Orchestrator](../sphinx_docs/_build/html/zenml.backends.orchestrator.html)
      * [Kubeflow](../sphinx_docs/_build/html/zenml.backends.orchestrator.kubeflow.html)
      * [Kubernetes](../sphinx_docs/_build/html/zenml.backends.orchestrator.kubernetes.html)
    * [Processing](../sphinx_docs/_build/html/zenml.backends.processing.html)
    * [Training](../sphinx_docs/_build/html/zenml.backends.training.html)
  * [Cli](../sphinx_docs/_build/html/zenml.cli.html)
  * [Components](../sphinx_docs/_build/html/zenml.components.html)
    * [Pusher](../sphinx_docs/_build/html/zenml.components.pusher.html)
    * [Sequencer](../sphinx_docs/_build/html/zenml.components.sequencer.html)
    * [Split gen](../sphinx_docs/_build/html/zenml.components.split_gen.html)
    * [Tokenizer](../sphinx_docs/_build/html/zenml.components.tokenizer.html)
    * [Trainer](../sphinx_docs/_build/html/zenml.components.trainer.html)
    * [Transform](../sphinx_docs/_build/html/zenml.components.transform.html)
    * [Transform simple](../sphinx_docs/_build/html/zenml.components.transform_simple.html)
  * [Datasources](../sphinx_docs/_build/html/zenml.datasources.html)
  * [Metadata](../sphinx_docs/_build/html/zenml.metadata.html)
  * [Pipelines](../sphinx_docs/_build/html/zenml.pipelines.html)
  * [Repo](../sphinx_docs/_build/html/zenml.repo.html)
  * [Standards](../sphinx_docs/_build/html/zenml.standards.html)
  * [Steps](../sphinx_docs/_build/html/zenml.steps.html)
    * [Inferrer](../sphinx_docs/_build/html/zenml.steps.inferrer.html)
    * [Preprocesser](../sphinx_docs/_build/html/zenml.steps.preprocesser.html)
      * [Standard preprocesser](../sphinx_docs/_build/html/zenml.steps.preprocesser.standard_preprocesser.html)
        * [Methods](../sphinx_docs/_build/html/zenml.steps.preprocesser.standard_preprocesser.methods.html)
    * [Sequencer](../sphinx_docs/_build/html/zenml.steps.sequencer.html)
      * [Standard sequencer](../sphinx_docs/_build/html/zenml.steps.sequencer.standard_sequencer.html)
        * [Methods](../sphinx_docs/_build/html/zenml.steps.sequencer.standard_sequencer.methods.html)
    * [Split](../sphinx_docs/_build/html/zenml.steps.split.html)
    * [Tokenizer](../sphinx_docs/_build/html/zenml.steps.tokenizer.html)
    * [Trainer](../sphinx_docs/_build/html/zenml.steps.trainer.html)
      * [Pytorch trainers](../sphinx_docs/_build/html/zenml.steps.trainer.pytorch_trainers.html)
      * [Tensorflow trainers](../sphinx_docs/_build/html/zenml.steps.trainer.tensorflow_trainers.html)
  * [Utils](../sphinx_docs/_build/html/zenml.utils.html)
    * [Post training](../sphinx_docs/_build/html/zenml.utils.post_training.html)
