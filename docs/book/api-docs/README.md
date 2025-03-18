---
description: The ZenML API Documentation
---

# About

## ZenML API Documentation

Welcome to the ZenML API documentation. This guide provides information about both the open-source (OSS) and Pro API endpoints available in the ZenML platform.

### Getting Started

To begin using the ZenML Server API, follow these simple steps:

1. **Setup**: Ensure you have an active ZenML server or workspace configured.
2. **Authentication**: Obtain an API token from your service account, as detailed in our core documentation.
3. **API Access**: Use the token to authenticate and start interacting with the API endpoints.

### Authentication

For OSS API:
- Obtain an API token from your service account
- Include the token in the authorization header: `Authorization: Bearer YOUR_API_TOKEN`

For Pro API:
- Use your Pro API key in the authorization header: `Authorization: Bearer YOUR_API_KEY`

### API Endpoints Overview

The API provides several endpoints to facilitate different operations such as:

* **Pipelines**: Create, list, and manage your pipelines.
* **Stacks**: Access and configure stack components, such as orchestrators, artifact stores, and more.
* **Monitoring**: Retrieve logs and metrics to monitor the health of your operations.
* **Pro Features**: For Pro users, access extended capabilities like organizations, tenants, and enterprise features.

### Use Cases

While the ZenML Python SDK covers most workflow requirements, the Server API offers additional utility for:

* Automated scaling of operations in production environments.
* Integration with external monitoring and logging systems.
* Programmatic management and audit of resources and configurations.
* Enterprise team management and access control (Pro).

By leveraging the ZenML API, users can enhance the robustness and control of their machine learning workflows, ensuring operations are both efficient and scalable.

***

For detailed information on each endpoint and further usage examples, please refer to the specific API documentation sections. 