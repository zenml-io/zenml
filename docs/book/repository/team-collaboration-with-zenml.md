# Collaboration with ZenML

ZenML's mission is centered on reproducible Machine Learning, with easy access to integrations for your favorite technologies. A key aspect of this mission is the ability to easily collaborate with your team across machines and environments, without sacrifices.

Collaboration with ZenML means shared access to:

* [Git Repository](integration-with-git.md)
* [Pipeline directory](pipeline-directory.md)
* [Metadata Store](metadata-store.md)
* [Artifact Store](artifact-store.md)

Deploying the above in a shared setting makes all experiments within a ZenML repository reproducible and discoverable. 
This is regardless of which team member ran the corresponding pipelines, and regardless of the environment the experiments were run in.

```{note}
The Metadata and Artifact Stores respectively, while highly recommended, are not neccessary be shared to ensure collaboration. You could as well 
share the Git Repository with a committed local pipeline directory and still collaborate using ZenML. However, losing the Artifact and Metadata 
Store will invalidate all [caching](../benefits/reusing-artifacts.md), and all pipelines need them to be re-run on every team members local setup. This might 
have uninteded consequences, so please be careful when setting this up in production.
```

## Example

After ensuring that the above properties are accessible by all team members, any member of the team can create pipelines and 
experiment at their will.

So if Team Member A creates and pushes a pipeline like so:

```python
training_pipeline = TrainingPipeline(name='Pipeline A')

# add steps to the pipeline, not shown here

training_pipeline.run()
```

Then Team Member B can access this pipeline and use it as follows:

```python
from zenml.repo import Repository

# Get a reference in code to the current repo
repo = Repository()
pipeline_a = repo.get_pipeline_by_name('Pipeline A')

pipeline_a.view_schema()  # view schema
pipeline_a.view_statistics()  # view statistics of the run
pipeline_a.view_anomalies()  # view anomalies (feature drift etc)
pipeline_a.evaluate()  # view results
```

They can then create a new pipeline using this pipeline as base:
```python
pipeline_b = pipeline_a.copy(new_name='Pipeline B')  # pipeline_a itself is immutable
pipeline_b.add_trainer(...)  # change trainer step
pipeline_b.run()
```

In the above example, if there is a shared Metadata and Artifact Store, all steps preceding the TrainerStep in the pipeline will be [cached](../benefits/reusing-artifacts.md) and re-used in Pipeline B.
This way the entire team is benefiting from each other's work implicitly, and can see each other's results and progress as it evolves.

## How to set it up
For a concrete example on how to set up collaboration completely, check out our tutorial using [Google Cloud Platform](../tutorials/team-collaboration-with-zenml-and-google-cloud.md).
Using any other cloud provider is also possible, as the only requirement is the Metadata Store and Artifact Store exist in a globally accessible place.
Also, not using a cloud provider at all is also possible, but would entail losing the advantages of a shared metadata + artifact store (see above note.)