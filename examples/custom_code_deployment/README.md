# 🚀 Custom Deployment Example - Seldon Core and KServe 🚀

Both pre and post-processing are very essential to the model deployment process since the majority of the models require a specific input format which requires transforming the data before it is passed to the model and after it is returned from the model. with ZenML 0.13 we can now ship the model with the pre-processing and post-processing code to run within the deployment environment.
The custom code deployment is only supported for the KServe and Seldon Core model deployer integrations at the moment.

Note: As this example can be considered an advanced feature of the deployment process, it is recommended to go through the [KServe deployment example](https://github.com/zenml-io/zenml/tree/main/examples/kserve_deployment) and/or the [Seldon Core deployment example](https://github.com/zenml-io/zenml/tree/main/examples/seldon_deployment) before trying this example. Those examples are more focused on the deployment process and are easier to understand, while also providing a guide on how to install and setup each of the deployment integrations.
## 🗺 Overview

This is a quite extended example that uses the [digits dataset](https://keras.io/api/datasets/mnist/) 
to train a classifier using both [TensorFlow](https://www.tensorflow.org/)
and [PyTorch](https://pytorch.org/). Then it deploys the trained model with additional pre-processing and post-processing code to both KServe and Seldon Core.

Based on which model deployment you are using in your stack, there is a specific run file for it.
(e.g for KServe you will need to run the `run_kserve.py` file and also specify which model flavor you want to deploy `python run_kserve.py -m pytorch `).



## 🧽 Clean up

To stop any prediction servers running in the background, use the `zenml model-server list`
and `zenml model-server delete <uuid>` CLI commands.:

```shell
zenml model-deployer models delete 62aac6aa-88fd-4eb7-a753-b46f1658775c
```

Then delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```

# 📜 Learn more

Our docs regarding the KServe deployment integration can be found [here](https://docs.zenml.io/mlops-stacks/model-deployers/kserve).

If you want to learn more about deployment in ZenML in general or about how to build your own deployer steps in ZenML
check out our [docs](https://docs.zenml.io/mlops-stacks/model-deployers/custom).
