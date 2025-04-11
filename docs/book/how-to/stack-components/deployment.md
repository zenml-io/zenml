---
description: Methods for deploying ZenML stacks on cloud platforms
icon: gear
---

# Deployment Options

Once you understand the concept of stacks, you may want to deploy them on cloud platforms to leverage more powerful resources. This page explains the different approaches to deploying ZenML stacks in cloud environments.

## Why Deploy Stacks to the Cloud?

While local stacks are great for development, cloud-based stacks offer significant advantages:

* **Scalability**: Access to virtually unlimited compute resources
* **Specialized Hardware**: Use GPUs/TPUs for model training
* **Managed Services**: Leverage cloud-native MLOps tools
* **Collaboration**: Share infrastructure with your team
* **Production Readiness**: Deploy in environments that match production
* **Cost Efficiency**: Pay only for what you use
* **Reliability**: Benefit from high-availability cloud infrastructure

## The Challenges of Stack Deployment

Deploying MLOps stacks involves several challenges:

* **Tool Requirements**: Ensuring all tool requirements are met and compatible
* **Configuration Complexity**: Determining appropriate infrastructure parameters
* **Production Readiness**: Creating secure setups with proper authentication and monitoring
* **Component Integration**: Managing permissions and connectivity between components
* **Resource Management**: Properly cleaning up resources to avoid wasted costs
* **Custom Adaptations**: Modifying standard tool installations to meet specific needs

ZenML's deployment approaches help address these challenges with varying degrees of automation and control.

## The Deployment Process

Deploying a ZenML stack to the cloud involves these general steps:

1. **Provision infrastructure** resources on a cloud platform
2. **Configure stack components** to use these resources
3. **Register these components** in ZenML
4. **Create a stack** from these components
5. **Set the stack as active** for pipeline execution

ZenML offers multiple approaches to accomplish these steps, ranging from fully automated to highly customizable.

## Deployment Approaches

ZenML provides three main approaches to deploy cloud stacks:

### 1. 1-Click Deployment

The simplest way to deploy a complete stack to a cloud provider.

**How it works**:

* ZenML automatically provisions all necessary cloud resources
* Configures them to work together
* Registers the components and creates a ready-to-use stack

**Best for**:

* Getting started quickly with cloud infrastructure
* Development and testing environments
* Users with limited cloud expertise
* Teams who want minimal configuration overhead

### 2. Stack Wizard

A guided approach to creating a stack from existing cloud resources.

**How it works**:

* Connects to your cloud provider using a service connector
* Discovers available resources (storage buckets, compute services, etc.)
* Lets you select which resources to use for each component
* Creates a stack from your selected resources

**Best for**:

* Using existing cloud infrastructure
* Organizations with established cloud resources
* Greater control over which resources are used
* Compliance with company-specific resource policies

### 3. Infrastructure as Code

An approach for maximum customization and control using tools like Terraform.

**How it works**:

* Uses Terraform to define and provision cloud resources
* Provides complete control over infrastructure configuration
* Enables version control of your infrastructure
* Supports complex, custom deployments

**Best for**:

* Production environments
* Infrastructure-as-code workflows
* DevOps-oriented teams
* Compliance and governance requirements
* Custom infrastructure requirements

## Choosing a Deployment Method

Consider these factors when selecting a deployment method:

| Factor                 | 1-Click         | Stack Wizard       | Terraform          |
| ---------------------- | --------------- | ------------------ | ------------------ |
| Setup Speed            | Fastest         | Medium             | Slower             |
| Customization          | Limited         | Medium             | High               |
| Learning Curve         | Low             | Medium             | Higher             |
| Control                | Minimal         | Medium             | Complete           |
| Security Configuration | Pre-configured  | Manual selection   | Fully customizable |
| Resource Cleanup       | Automatic       | Manual             | Defined in code    |
| Best Use Case          | Getting started | Existing resources | Production         |

## Deployment and Service Connectors

All deployment methods require authentication with cloud services. Service connectors provide the authentication layer that allows ZenML to interact with your cloud resources:

* **1-Click Deployment**: Creates service connectors automatically
* **Stack Wizard**: Uses existing service connectors to discover resources
* **Infrastructure as Code**: Requires configuring service connectors after provisioning

Understanding service connectors is crucial for successful stack deployment. See the [Service Connectors](service_connectors.md) page for more details.

## After Deployment

Once your stack is deployed:

1. **Set it as active**: `zenml stack set STACK_NAME`
2. **Verify configuration**: `zenml stack describe`
3. **Run a test pipeline** to ensure everything works
4. **Share with team members** as needed

## Best Practices

* **Start small**: Begin with minimal components and add more as needed
* **Use descriptive names** for stacks and components
* **Create separate stacks** for development, staging, and production
* **Document your infrastructure** for team knowledge sharing
* **Monitor cloud costs** to avoid unexpected expenses
* **Implement proper security measures** for production deployments

## Next Steps

* Learn how to [deploy a cloud stack with 1-click](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack)
* Register [existing cloud resources](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/register-a-cloud-stack) using the Stack Wizard
* Deploy infrastructure with [Terraform modules](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack-with-terraform)
* Understand [Service Connectors](service_connectors.md) for authentication
