---
description: How to choose the right orchestration environment
icon: server
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Choosing the right Orchestration Environment

When embarking on a machine learning project, one of the most critical early decisions is where to run your pipelines. This choice impacts development speed, costs, and the eventual path to production. In this post, we'll explore the most common environments for running initial ML experiments, helping you make an informed decision based on your specific needs.

### Local Environment

The local environment — your laptop or desktop computer - is where most ML projects begin their journey.

<table>
<tr>
<td>

### Pros:

- **Zero setup time**: Start coding immediately without provisioning remote resources
- **No costs**: Uses hardware you already own
- **Low latency**: No network delays when working with data
- **Works offline**: Develop on planes, in cafes, or anywhere without internet
- **Complete control**: Easy access to logs, files, and debugging capabilities
- **Simplicity**: No need to interact with cloud configurations or container orchestration

</td>
<td>

### Cons:

- **Environment inconsistency**: "Works on my machine" problems
- **Limited resources**: RAM, CPU, and GPU constraints
- **Poor scalability**: Difficult to process large datasets
- **Limited parallelization**: Running multiple experiments simultaneously is challenging

</td>
</tr>
</table>

### Ideal for:

- Quick proof-of-concepts with small datasets
- Early-stage algorithm development and debugging
- Small datasets, low compute requirements
- Small teams with standardized development environments
- Projects with minimal computational requirements

### Cloud VMs/Serverless Functions

When local resources become insufficient, cloud virtual machines (VMs) or serverless functions offer the next step up.

<table>
<tr>
<td>

### Pros:

- **Scalable resources**: Access to powerful CPUs/GPUs as needed
- **Pay-per-use**: Only pay for what you consume
- **Flexibility**: Choose the right instance type for your workload
- **No hardware management**: Leave infrastructure concerns to the provider
- **Easy snapshots**: Create machine images to replicate environments
- **Global accessibility**: Access your work from anywhere

</td>
<td>

### Cons:

- **Costs can accumulate**: Easy to forget running instances
- **Setup complexity**: Requires cloud provider knowledge (if not using ZenML)
- **Security considerations**: Data must leave your local network
- **Dependency management**: Need to configure environments properly
- **Network dependency**: Requires internet connection for access

</td>
</tr>
</table>

### Ideal for:

- Larger datasets that won't fit in local memory
- Projects requiring specific hardware (like GPUs)
- Teams working remotely across different locations
- Experiments that run for hours or days
- Projects transitioning from development to small-scale production

### Kubernetes

Kubernetes provides a platform for automating the deployment, scaling, and operations of application containers.

<table>
<tr>
<td>

### Pros:

- **Containerization**: Ensures consistency across environments
- **Resource optimization**: Efficient allocation of compute resources
- **Horizontal scaling**: Easily scale out experiments across nodes
- **Orchestration**: Automated management of your workloads
- **Reproducibility**: Consistent environments for all team members
- **Production readiness**: Similar environment for both experiments and production

</td>
<td>

### Cons:

- **Steep learning curve**: Requires Kubernetes expertise
- **Complex setup**: Significant initial configuration
- **Overhead**: May be overkill for simple experiments
- **Resource consumption**: Kubernetes itself consumes resources
- **Maintenance burden**: Requires ongoing cluster management

</td>
</tr>
</table>

### Ideal for:

- Teams already using Kubernetes for production
- Experiments that need to be distributed across machines
- Projects requiring strict environment isolation
- ML workflows that benefit from a microservices architecture
- Organizations with dedicated DevOps support

### Databricks

Databricks provides a unified analytics platform designed specifically for big data processing and machine learning.

<table>
<tr>
<td>

### Pros:

- **Optimized for Spark**: Excellent for large-scale data processing
- **Collaborative notebooks**: Built-in collaboration features
- **Managed infrastructure**: Minimal setup required
- **Integrated MLflow**: Built-in experiment tracking
- **Auto-scaling**: Dynamically adjusts cluster size
- **Delta Lake integration**: Reliable data lake operations
- **Enterprise security**: Compliance and governance features

</td>
<td>

### Cons:

- **Cost**: Typically more expensive than raw cloud resources
- **Vendor lock-in**: Some features are Databricks-specific
- **Learning curve**: New interface and workflows to learn
- **Less flexibility**: Some customizations are more difficult
- **Not ideal for small data**: Overhead for tiny datasets

</td>
</tr>
</table>

### Ideal for:

- Data science teams in large enterprises
- Projects involving both big data processing and ML
- Teams that need collaboration features built-in
- Organizations already using Spark
- Projects requiring end-to-end governance and security
