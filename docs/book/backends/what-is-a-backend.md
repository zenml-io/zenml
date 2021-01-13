# What is a backend?
Production-ready backends when you want to scale

ZenML backends define `how` and `where` ZenML pipelines are run. They are broadly split into three categories:

* `orchestrator`: Orchestrator backends manage the running of each step of the pipeline
* `processing`: Processing backends defines the environment in which each step executes its workload
* `training`: Training backends are special and meant only for [Training Pipelines.](../pipelines/training-pipeline.md) They define the environment in which the training happens

By separating backends from the actual pipeline logic, ZenML achieves a [Terraform](https://www.terraform.io/)-like scalability, extensibility and reproducibility for all its pipelines.

Backends too are split into `standard` and `custom` categories. The standard ones can be found at: `zenml.core.backends.*` . 

## Create your own backend
The API to create custom backends is still under active development. Please see this space for updates.

If you would like to see this functionality earlier, please let us know via our [Slack Channel](https://zenml.io/slack-invite/) 
or [create an issue on GitHub](https://https://github.com/maiot-io/zenml).