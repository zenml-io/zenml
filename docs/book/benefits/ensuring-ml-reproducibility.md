# Ensuring ML reproducibility with ZenML
Reproducibility is a key aspect of machine learning in research and production. ZenML is explicitly designed with 
reproduce machine learning in mind.

## Why should I care?
Having the ability to reproduce results in a machine learning system is critical to increase trust, reliability, and 
explainability as our models develop.


In the research of POC phase of development, reproducing experiments ensures that critical information is not lost due to 
human error. In production, this is even more critical: ML models tend to go through a lifecycle of being destroyed, forged anew and re-created as development evolves 
from rudimentary notebook snippets to a testable, production codebase. Therefore, we better make sure that every 
time a model is (re-) trained, the results are what we expect them to be.

```{hint}
To understand why reproducibility is so important in more detail, check out 
https://blog.maiot.io/is-your-ml-reproducible/
```

## How ZenML guarantees reproducibility
Throughout development, ZenML has mechanisms in place that automatically ensure reproducibility in the following aspects:

* Code
* Configuration
* Environment
* Data

```{hint}
If working in a team, you might consider setting up a [collaborative environment](../repository/team-collaboration-with-zenml.md)  
to share reproducibility across your team.
```

### Code
All relevant code is git-pinned via the [integration logic described here](../repository/integration-with-git.md). By tying the 
git sha (which is essentially a snapshot of code in time) to a ML pipeline, ZenML ensures that any person with access to that 
git repository can re-run all parts of that pipeline by using Git history.

### Configuration
ZenML already natively [seperates configuration from code in its design](). That means that every step in a pipeline has its parameters 
tracked and stored in the [declarative config file](../pipelines/what-is-a-pipeline.md) and also the [metadata store](../repository/metadata-store.md).
Therefore, pulling a pipeline and running it in another environment not only ensures that the code will be the same, but also the 
configuration.

### Environment
ZenML is designed with [extensibility in mind](). The ML eco-system has myriad cool tools that are useful in different scenarios. The 
integration system implemented in ZenML allows to extend it quite easily with these tools. This allows for easy tracking of 
requirements across environments.

Apart from organized integrations, ZenML is fully usable with [Docker](../backends/using-docker.md). Users can create their own custom images 
and use them in custom [Backends](../backends/what-is-a-backend.md). Everything is again tracked in the declarative configuration output, therefore 
can be reproduced any time from scratch or in another enviornment.

### Data
Every ZenML step produces artifacts that are persisted in the [Artifact Store](../repository/artifact-store.md), and individually 
tracked by the [Metadata Store](../repository/metadata-store.md). The combination of these two ensures that all data running through 
the system exists in a system that tracks it completely end-to-end. This is also what allows for cool features such as [caching](../pipelines/reusing-artifacts.md). 
Therefore, having access to a shared metadata and artifact store ensures reproducible pipelines across environments.

Having this system in place also ensures data versioning. This is achieved by the fact that every [Datasource](../datasources/what-is-a-datasource.md) has an 
associated `DataStep` whose output artifact is a snapshot of the entire datasource in time.

## Conclusion
The four aspects outlined above put together guarantee reproducible machine learning when using ZenML. Any ZenML pipeline 
can be pulled and run again and results would be exactly the same across environments. Try it yourself by running a pipeline and 
then re-running it immediately after to see how this works.

In conclusion, whether you are a researcher tracking experiments, or in a production setting, ZenML makes reproducing your 
machine learning code much easier.