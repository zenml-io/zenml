# Deployment Options for finetuned LLMs

Deploying your finetuned LLM is a critical step in bringing your custom
finetuned model into a place where it can be used as part of a real-world use
case. This process involves careful planning and consideration of various
factors to ensure optimal performance, reliability, and cost-effectiveness. In
this section, we'll explore the key aspects of LLM deployment and discuss
different options available to you.

## Deployment Considerations

Before diving into specific deployment options, you should understand the
various factors that influence the deployment process. One of the primary
considerations is the memory and machine requirements for your finetuned model.
LLMs
are typically resource-intensive, requiring substantial RAM, processing power
and specialised hardware. This choice of hardware can significantly impact both
performance and cost, so it's crucial to strike the right balance based on your
specific use case.

Real-time considerations play a vital role in deployment planning, especially
for applications that require immediate responses. This includes preparing for
potential failover scenarios if your finetuned model encounters issues,
conducting thorough benchmarks and load testing, and modelling expected user
load and usage patterns. Additionally, you'll need to decide between streaming
and non-streaming approaches, each with its own set of trade-offs in terms of
latency and resource utilisation.

Optimisation techniques, such as quantisation, can help reduce the resource
footprint of your model. However, these optimisations often come with additional
steps in your workflow and require careful evaluation to ensure they don't
negatively impact model performance. [Rigorous evaluation](./evaluation-for-finetuning.md)
becomes crucial in quantifying the extent to which you can optimise without
compromising accuracy or functionality.

## Deployment Options and Trade-offs

When it comes to deploying your finetuned LLM, several options are available,
each with its own set of advantages and challenges:

1. **Roll Your Own**: This approach involves setting up and managing your own
   infrastructure. While it offers the most control and customisation, it also
   requires expertise and resources to maintain. For this, you'd
   usually create some kind of Docker-based service (a FastAPI endpoint, for
   example) and deploy this on your infrastructure, with you taking care of all
   of the steps along the way.
2. **Serverless Options**: Serverless deployments can provide scalability and
   cost-efficiency, as you only pay for the compute resources you use. However,
   be aware of the "cold start" phenomenon, which can introduce latency for
   infrequently accessed models.
3. **Always-On Options**: These deployments keep your model constantly running
   and ready to serve requests. While this approach minimises latency, it can be
   more costly as you're paying for resources even during idle periods.
4. **Fully Managed Solutions**: Many cloud providers and AI platforms offer
   managed services for deploying LLMs. These solutions can simplify the
   deployment process but may come with less flexibility and potentially higher
   costs.

When choosing a deployment option, consider factors such as your team's
expertise, budget constraints, expected load patterns, and specific use case
requirements like speed, throughput, and accuracy needs.

## Deployment with vLLM and ZenML

[vLLM](https://github.com/vllm-project/vllm) is a fast and easy-to-use library
for running large language models (LLMs) at high throughputs and low latency.
ZenML comes with a [vLLM integration](../../../component-guide/model-deployers/vllm.md)
that makes it easy to deploy your finetuned model using vLLM. You can use a
pre-built step that exposes a `VLLMDeploymentService` that can be used as part of
your deployment pipeline.

```python

from zenml import pipeline
from typing import Annotated
from steps.vllm_deployer import vllm_model_deployer_step
from zenml.integrations.vllm.services.vllm_deployment import VLLMDeploymentService


@pipeline()
def deploy_vllm_pipeline(
    model: str,
    timeout: int = 1200,
) -> Annotated[VLLMDeploymentService, "my_finetuned_llm"]:
   # ...
   # assume we have previously trained and saved our model
   service = vllm_model_deployer_step(
      model=model,
      timeout=timeout,
   )
   return service
```

In this code snippet, the `model` argument can be a path to a local model or it
can be a model ID on the Hugging Face Hub. This will then deploy the model
locally using vLLM and you can then use the `VLLMDeploymentService` for batch
inference requests using the OpenAI-compatible API.

For more details on how to use this deployer, see the [vLLM integration documentation](../../../component-guide/model-deployers/vllm.md).

## Cloud-Specific Deployment Options

For AWS deployments, Amazon SageMaker stands out as a fully managed machine
learning platform that offers deployment of LLMs with options for
real-time inference endpoints and automatic scaling. If you prefer a serverless
approach, combining AWS Lambda with API Gateway can host your model and trigger
it for real-time responses, though be mindful of potential cold start issues.
For teams seeking more control over the runtime environment while still
leveraging AWS's managed infrastructure, Amazon ECS or EKS with Fargate provides
an excellent container orchestration solution, though do note that with all of
these options you're taking on a level of complexity that might become costly to
manage in-house.

On the GCP side, Google Cloud AI Platform offers similar capabilities to
SageMaker, providing managed ML services including model deployment and
prediction. For a serverless option, Cloud Run can host your containerized LLM
and automatically scale based on incoming requests. Teams requiring more
fine-grained control over compute resources might prefer Google Kubernetes
Engine (GKE) for deploying containerized models.

## Architectures for Real-Time Customer Engagement

Ensuring your system can engage with customers in real-time, for example, requires careful
architectural consideration. One effective approach is to deploy your model
across multiple instances behind a load balancer, using auto-scaling to
dynamically adjust the number of instances based on incoming traffic. This setup
provides both responsiveness and scalability.

To further enhance performance, consider implementing a caching layer using
solutions like Redis. This can store frequent responses, reducing the load on
your model and improving response times for common queries. For complex queries
that may take longer to process, an asynchronous architecture using message
queues (such as Amazon SQS or Google Cloud Pub/Sub) can manage request backlogs
and prevent timeouts, ensuring a smooth user experience even under heavy load.

For global deployments, edge computing services like [AWS Lambda@Edge](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-at-the-edge.html?tag=soumet-20) or
[CloudFront Functions](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cloudfront-functions.html?tag=soumet-20) can be invaluable. These allow you to deploy lighter
versions of your model closer to end-users, significantly reducing latency for
initial responses and improving the overall user experience.

## Reducing Latency and Increasing Throughput

Optimizing your deployment for low latency and high throughput is crucial for
real-time engagement. Start by focusing on model optimization techniques such as
quantization to reduce model size and inference time. You might also explore
distillation techniques to create smaller, faster models that approximate the
performance of larger ones without sacrificing too much accuracy.

Hardware acceleration can provide a significant performance boost. Leveraging
GPU instances for inference, particularly for larger models, can dramatically
reduce processing time.

Implementing request batching allows you to process multiple inputs in a single
forward pass, increasing overall throughput. This can be particularly effective
when combined with parallel processing techniques, utilizing multi-threading or
multi-processing to handle multiple requests concurrently. This would make sense
if you were operating at serious scale, but this is probably unlikely in the
short-term when you are just getting started.

Finally, implement detailed monitoring and use profiling tools to identify
bottlenecks in your inference pipeline. This ongoing process of measurement and
optimization will help you continually refine your deployment, ensuring it meets
the evolving demands of your users.

By thoughtfully implementing these strategies and maintaining a focus on
continuous improvement, you can create a robust, scalable system that provides
real-time engagement with low latency and high throughput, regardless of whether
you're deploying on AWS, GCP, or a multi-cloud environment.

## Monitoring and Maintenance

Once your finetuned LLM is deployed, ongoing monitoring and maintenance become
crucial. Key areas to watch include:

1. **Evaluation Failures**: Regularly run your model through evaluation sets to
   catch any degradation in performance.
2. **Latency Metrics**: Monitor response times to ensure they meet your
   application's requirements.
3. **Load and Usage Patterns**: Keep an eye on how users interact with your model
   to inform scaling decisions and potential optimisations.
4. **Data Analysis**: Regularly analyse the inputs and outputs of your model to
   identify trends, potential biases, or areas for improvement.

It's also important to consider privacy and security when capturing and logging
responses. Ensure that your logging practices comply with relevant data
protection regulations and your organisation's privacy policies.

By carefully considering these deployment options and maintaining vigilant
monitoring practices, you can ensure that your finetuned LLM performs optimally
and continues to meet the needs of your users and organisation.
