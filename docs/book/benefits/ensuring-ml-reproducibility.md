# Ensuring ML reproducibility with ZenML
Reproducibility is a key aspect of machine learning in research and production.
ZenML is built with reproducibility in mind. Reproducibility is a core motivation of DevOps methodologies: Builds need to be reproducible. Commonly, this is achieved by version control of code, version pinning of dependencies, and automation of workflows. 

ZenML bundles these practices into a coherent framework for Machine Learning. Machine Learning brings an added level of complexity to version control, beyond versioning code: Data is inherently hard to version.

## Why should I care?
Having the ability to reproduce results in a machine learning system is critical to increase trust, reliability, and 
explainability as our models develop.


In the research of POC phase of development, reproducing experiments ensures that critical information is not lost due to 
human error. In production, this is even more critical: ML models tend to go through a lifecycle of being destroyed, forged anew and re-created as development evolves 
from rudimentary notebook snippets to a testable, production codebase. Therefore, we better make sure that every 
time a model is (re-) trained, the results are what we expect them to be.

```{hint}
To understand why reproducibility is so important in more detail, check out this [blog post](https://blog.zenml.io/is-your-ml-reproducible/).
```

## How ZenML guarantees reproducibility
Throughout development, ZenML has mechanisms in place that automatically ensure reproducibility in the following aspects:

* Code
* Configuration
* Environment
* Data

```{hint}
If working in a team, you might consider setting up a [collaborative environment](../repository/team-collaboration-with-zenml.md) to share reproducibility across your team.
```
### Versioning of data

ZenML takes an easy, yet effective approach to version controlling data. When sourcing data, either via dedicated data pipelines or within your training pipelines, ZenML creates an immutable snapshot of the data \(TFRecords\) used for your specific pipeline. This snapshot is tracked, just like any other pipeline step, and becomes available as a starting point to subsequent pipelines when using the same parameters for sourcing data.

**NOTE:** The principle behind versioning data in ZenML is a variation of the method used for caching pipeline steps.

### Versioning of code

It is not necessary to reinvent the wheel when it comes to version control of code - chances are, you’re 
already using git to do so \(and if not, you should\). ZenML can tap into a repository's history and allow 
for version-pinning of your own code via git SHA’s. All relevant code is pinned via the [integration logic described here](../repository/integration-with-git.md). 

By tying the git sha (which is essentially a snapshot of code in time) to a ML pipeline, ZenML ensures that any person with access to that 
git repository can re-run all parts of that pipeline by using Git history. This becomes exceptionally powerful when you have code you want/need to embed at serving time, as there is now not just the lineage of data, but also the lineage of code from experiment to serving.

### Declarative configuration
Declarative configurations are a staple of DevOps methodologies, ultimately brought to fame through [Terraform](https://terraform.io/). In a nutshell: A pipeline’s configuration declares the “state” the pipeline should be in and the processing that should be applied, and ZenML figures out where the code lies and what computations to apply.

ZenML already natively [separates configuration from code in its design](tracked-metadata.md). That means that every step in a pipeline has its parameters 
tracked and stored in the [declarative config file](../pipelines/what-is-a-pipeline.md) and also the [metadata store](../repository/metadata-store.md).
Therefore, pulling a pipeline and running it in another environment not only ensures that the code will be the same, but also the 
configuration.

That way, when your teammate clones your repo and re-runs a pipeline config on a different environment, the pipeline remains reproducible.

### Metadata tracking

While versioning and declarative configs are essential for reproducibility, there needs to be a system that keeps track of all processes as they happen. Google’s [ML Metadata](https://github.com/google/ml-metadata) standardizes metadata tracking and makes it easy to keep track of iterative experimentation as it happens. ZenML uses ML Metadata extensively \(natively as well as via the TFX interface\) to automatically track all **relevant** parameters that are created through ZenML pipeline interfaces. This not only helps in post-training workflows to compare results as experiments progress but also has the added advantage of leveraging caching of pipeline steps.

The Metadata Store can be simply configured to use any MySQL server \(=&gt;5.6\):

```text
zenml config metadata set mysql \
    --host="127.0.0.1" \ 
    --port="3306" \
    --username="USER" \
    --password="PASSWD" \
    --database="DATABASE"
```

### Artifact tracking

With ZenML, inputs and outputs are tracked for every pipeline step. Output artifacts \(e.g. binary representations of data, splits, preprocessing results, models\) are centrally stored and are automatically used for [caching](../benefits/reusing-artifacts.md). To facilitate that, ZenML relies on a Metadata Store and an Artifact Store.

By default, both will point to a subfolder of your local `.zenml` directory, which is created when you run `zenml init`. It’ll contain both the Metadata Store \(default: SQLite\) as well as the Artifact Store \(default: tf.Records in local folders\).

More advanced configurations might want to centralize both the Metadata as well as the Artifact Store, for example for use in Continuous Integration or for collaboration across teams:

The Artifact Store offers native support for Google Cloud Storage:

```text
zenml config artifacts set "gs://your-bucket/sub/dir"
```

### Environment
ZenML is designed with [extensibility in mind](integrations.md). The ML eco-system has myriad cool tools that are useful in different scenarios. The 
integration system implemented in ZenML allows to extend it quite easily with these tools. This allows for easy tracking of 
requirements across environments.

Apart from organized integrations, ZenML is fully usable with [Docker](../backends/using-docker.md). Users can create their own custom images 
and use them in custom [Backends](../backends/what-is-a-backend.md). Everything is again tracked in the declarative configuration output, therefore 
can be reproduced any time from scratch or in another enviornment.


### Data
Every ZenML step produces artifacts that are persisted in the [Artifact Store](../repository/artifact-store.md), and individually 
tracked by the [Metadata Store](../repository/metadata-store.md). The combination of these two ensures that all data running through 
the system exists in a system that tracks it completely end-to-end. This is also what allows for cool features such as [caching](../benefits/reusing-artifacts.md). 
Therefore, having access to a shared metadata and artifact store ensures reproducible pipelines across environments.

Having this system in place also ensures data versioning. This is achieved by the fact that every [Datasource](../datasources/what-is-a-datasource.md) has an 
associated `DataStep` whose output artifact is a snapshot of the entire datasource in time.

## Conclusion
The aspects outlined above put together guarantee reproducible machine learning when using ZenML. Any ZenML pipeline 
can be pulled and run again and results would be exactly the same across environments. Try it yourself by running a pipeline and 
then re-running it immediately after to see how this works.

In conclusion, whether you are a researcher tracking experiments, or in a production setting, ZenML makes reproducing your 
machine learning code much easier.