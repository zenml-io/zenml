---
description: Methods for deploying ZenML stacks on cloud platforms
---

# Deployment

ZenML provides multiple ways to deploy stacks on cloud platforms like AWS, Azure, and GCP. This page describes the different deployment methods and their pros and cons.

## Deployment Options Overview

ZenML offers three main approaches to deploy cloud stacks:

1. **1-Click Deployment**: A guided, automated deployment for quickly setting up fully functional stacks
2. **Stack Wizard**: A tool to create stacks from existing cloud resources
3. **Terraform Deployment**: Infrastructure-as-code deployment for more customization and control

Each method has different levels of automation, customization, and complexity, allowing you to choose the approach that best fits your needs.

## 1-Click Deployment

The 1-Click Deployment feature automates the provisioning of all necessary cloud resources to run ZenML pipelines. It's the fastest way to get a production-ready stack up and running without manual configuration.

### How It Works

1. ZenML provisions the necessary resources on your cloud platform
2. Configures these resources to work together
3. Registers the necessary stack components
4. Creates a new stack with these components

### Usage

From the CLI:

```bash
# For AWS
zenml deploy aws --region us-west-2 --bucket-name my-zenml-artifacts

# For Azure
zenml deploy azure --resource-group zenml-stack --location eastus

# For GCP
zenml deploy gcp --project my-project --region us-central1
```

From the dashboard:
- Navigate to **Stacks** → **New Stack** → **Deploy new Cloud**
- Follow the guided wizard to configure your deployment

### Best For

- Getting started quickly with cloud stacks
- Development and testing environments
- Users who want minimal configuration overhead

## Stack Wizard

The Stack Wizard helps you create a stack from existing cloud resources. It scans available resources through a service connector and lets you select which ones to use for each stack component.

### How It Works

1. Connect to your cloud provider using a service connector
2. The wizard discovers available resources (storage buckets, container registries, etc.)
3. You select which resources to use for each component
4. The wizard registers the components and creates a stack

### Usage

From the CLI:

```bash
# Start the wizard for a specific cloud provider
zenml stack register my-stack -p aws
zenml stack register my-stack -p azure
zenml stack register my-stack -p gcp
```

From the dashboard:
- Navigate to **Stacks** → **New Stack** → **Use existing Cloud**
- Follow the guided interface to select resources and create your stack

### Best For

- Using existing cloud resources
- Organizations with established cloud infrastructure
- Customizing which resources to use for each component

## Terraform Deployment

Terraform deployment provides infrastructure-as-code capabilities for deploying ZenML stacks. This approach gives you complete control over your infrastructure and enables version control, collaboration, and reproducibility.

### How It Works

1. ZenML provides Terraform modules for different cloud providers
2. You configure variables to customize the deployment
3. Terraform provisions the resources based on your configuration
4. You register stack components using the outputs from Terraform

### Usage

```bash
# Clone the ZenML repository
git clone https://github.com/zenml-io/zenml.git
cd zenml/terraform/aws  # or azure, gcp

# Initialize Terraform
terraform init

# Configure and apply
terraform apply -var="region=us-west-2" -var="prefix=zenml"

# Register components and stack using outputs
# (See cloud-specific guides for detailed instructions)
```

### Best For

- Production environments
- Infrastructure-as-code workflows
- DevOps teams
- Custom infrastructure requirements
- Compliance and governance requirements

## Comparing Deployment Methods

| Feature | 1-Click Deployment | Stack Wizard | Terraform |
|---------|-------------------|--------------|-----------|
| **Setup Speed** | Fastest | Medium | Slower |
| **Customization** | Limited | Medium | High |
| **Learning Curve** | Low | Medium | Higher |
| **Infrastructure Control** | Minimal | Medium | Complete |
| **Best For** | Quick starts | Existing resources | Production |
| **Version Control** | No | No | Yes |
| **Reproducibility** | Limited | Medium | High |

## Post-Deployment Steps

After deploying your stack, regardless of the method used:

1. **Set as active**: `zenml stack set STACK_NAME`
2. **Verify the stack**: `zenml stack describe`
3. **Run a test pipeline** to ensure everything works correctly
4. **Set up CI/CD** for automated pipeline runs (optional)

## Best Practices

- **Start small**: Begin with a minimal stack and add components as needed
- **Use descriptive names** for stacks and components
- **Document your deployment** process and configurations
- **Use separate stacks** for development, staging, and production
- **Regularly update** your stack components to get the latest features and security updates
- **Monitor costs** of cloud resources to avoid unexpected expenses

## Troubleshooting

Common deployment issues include:

- **Permission errors**: Ensure your credentials have the necessary permissions
- **Resource limits**: Check if you've hit cloud provider quotas or limits
- **Network issues**: Verify connectivity between resources
- **Configuration errors**: Double-check component settings

Most deployment methods provide detailed logs to help diagnose issues.

## Next Steps

- Learn about specific cloud provider integrations:
  - [AWS](aws.md)
  - [Azure](azure.md)
  - [GCP](gcp.md)
- Explore [Service Connectors](service_connectors.md) for authentication
- Understand [Stack Components](stack_components.md) in more detail 