# Table of contents

* [Introduction](index.md)
* [Installation](installation.md)
* [Core Concepts](core-concepts.md)

## Starter Guide

* [Creating your ZenML repository](starter-guide/repository.md)
* [Designing your first pipeline](starter-guide/quickstart.md)
* [Registering a new datasource](starter-guide/datasource.md)
* [Modifying the split](starter-guide/split.md)
* [Adding your preprocessing logic](starter-guide/transform.md)
* [Creating your trainer](starter-guide/trainer.md)
* [Adding evaluation metrics](starter-guide/evaluator.md)
* [Deploy your model](starter-guide/deployer.md)
* [Post-training workflow](starter-guide/post-training.md)
* [Scaling to the cloud](starter-guide/scaling-to-the-cloud.md)

## Advanced Guide

* [Inspecting all pipelines in a repository](advanced-guide/inspecting-all-pipelines.md)
* [The metadata and artifact stores](advanced-guide/querying-the-metadata-store.md)
* [ZenML Repository Guidelines](advanced-guide/fetching-artifacts.md)
* [Team Collaboration](advanced-guide/team-collaboration.md)
* [Managing the environment](advanced-guide/integrations.md)
* [Backends](advanced-guide/backends.md)

## Support

* [Tutorials](support/tutorials.md)
* [Roadmap](support/roadmap.md)
* [Changelogs](support/release_notes.md)
* [Usage Analytics](support/usage-analytics.md)
* [Contact](support/contact.md)

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

