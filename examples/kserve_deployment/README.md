# 🚀 Pytorch Models Deployment with KServe and TorchServe 

As Pytorch becomes more of a standard framework for writing Computer Vision
and Natural Language Processing models, especially in the research domain,
it is becoming more and more important to have a robust and easy to not only 
[build ML pipelines with Pytorch](../pytorch/) but also to deploy the models built with it.

[KServe](https://kserve.github.io/website) is a Kubernetes-based Model inference platform
built for highly scalable deployment use cases, it provides a standardized inference protocol 
across ML frameworks while supporting a serverless architecture with Autoscaling including Scale to Zero on GPU.
KServe Uses a simple and pluggable production serving for production ML serving that includes 
prediction, pre/post-processing, monitoring and explainability.

[TorchServe](https://torchserve.github.io/website) is an open-source model serving framework for PyTorch
that makes it easy to deploy Pytorch models at a production scale with low latency and high throughput.
it provides default handlers for the most common applications such as object detection and text classification, 
so you can write as little code as possible to deploy your custom models.

This example shows how we can use ZenML integrations to build a pipeline that trains a model, deploys it to
Kubernetes with KServe and TorchServe as the Model Serving Runtime, and then runs a prediction on the deployed model.


