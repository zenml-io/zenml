# Core Concepts
At its core, ZenML will orchestrate your experiment pipelines from **sourcing data** to **splitting, preprocessing, training**, all the way to the 
**evaluation of results** and even **serving**.

While there are other pipelining solutions for Machine Learning experiments, ZenML is focussed on two unique approaches:

* [Reproducibility](core-concepts.md#reproducibility). 
* [Integrations](core-concepts.md#integrations).

Let us introduce some of the concepts we use to make this focus a reality.

## Reproducibility

ZenML is built with reproducibility in mind. Reproducibility is a core motivation of DevOps methodologies: Builds need to be reproducible. Commonly, this is achieved by version control of code, version pinning of dependencies, and automation of workflows. ZenML bundles these practices into a coherent framework for Machine Learning. Machine Learning brings an added level of complexity to version control, beyond versioning code: Data is inherently hard to version.

