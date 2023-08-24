<!-- Remove these comments -->
<!-- markdown-link-check-disable -->

# 💫 Bringing all MLOps stack components together to build an end-to-end data product with ZenML
ZenML is an extensible, open-source MLOps framework for creating portable, production-ready machine learning pipelines. By decoupling infrastructure from code, ZenML enables developers across your organization to collaborate more effectively as they develop to production.

While [extensive documentation of ZenML](https://docs.zenml.io/getting-started/introduction) is a great support for exploring specific components and integrations, seeing the big picture of all components integrated and working together is not usually covered by any documentation. This example comes in handy to fill this gap!

It demonstrates how the most important steps of the ML Production Lifecycle can be implemented in a reusable way remaining agnostic to the underlying infrastructure, and how to integrate them into pipelines serving Training and Batch Inference purposes.

This example was deprecated in favor of the project template implementation. Our project templates are always up-to-date and tested along with new ZenML releases, to ensure nothing breaks!
To start with End-to-End example with Batch Scoring, Hyperparameter tuning, Model Version Promotion, and many more just hit the command below in an empty directory:

```bash
zenml init --template e2e_batch --template-with-defaults
```

More details about project templates can be found in [ZenML Documentation](https://docs.zenml.io/user-guide/starter-guide/using-project-templates)
