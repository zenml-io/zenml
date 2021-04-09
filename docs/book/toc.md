# Table of contents

* [Introduction](index.md)
* [Installation](installation.md)
* [Core Concepts](core-concepts.md)

## Starter Guide

* [Creating your ZenML repository](starter-guide/repository.md)
* [Writing your first training pipeline](starter-guide/quickstart.md)
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
* [Querying the metadata store](advanced-guide/querying-the-metadata-store.md)
* [Fetching artifacts](advanced-guide/fetching-artifacts.md)

## Support

* [Tutorials](support/tutorials.md)
* [Roadmap](../../ROADMAP.md)
* [Changelogs](../../RELEASE_NOTES.md)
* [Usage Analytics](support/usage-analytics.md)
* [Contact](support/contact.md)

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
