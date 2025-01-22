---
description: >
  Learn how to use the ZenML Pro API.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Using the ZenML Pro API

ZenML Pro offers a powerful API that allows you to interact with your ZenML resources. Whether you're using the [SaaS version](https://cloud.zenml.io) or a self-hosted ZenML Pro instance, you can leverage this API to manage tenants, organizations, users, roles, and more.

The SaaS version of ZenML Pro API is hosted at [https://cloudapi.zenml.io](https://cloudapi.zenml.io).

## API Overview

The ZenML Pro API is a RESTful API that follows OpenAPI 3.1.0 specifications. It provides endpoints for various resources and operations, including:

- Tenant management
- Organization management
- User management
- Role-based access control (RBAC)
- Authentication and authorization

## Authentication

To use the ZenML Pro API, you need to authenticate your requests. If you are logged in to your ZenML Pro account,
you can use the same browser window to authenticate requests to your ZenML Pro API, directly in the OpenAPI docs. 

For example, for the SaaS variant, you can access the docs here: https://cloudapi.zenml.io. You can make requests
by being logged into ZenML Pro at https://cloud.zenml.io.

Programmatic access is not possible at the moment.

## Key API Endpoints

Here are some important endpoints you can use with the ZenML Pro API:

### Tenant Management

- List tenants: `GET /tenants`
- Create a tenant: `POST /tenants`
- Get tenant details: `GET /tenants/{tenant_id}`
- Update a tenant: `PATCH /tenants/{tenant_id}`

### Organization Management

- List organizations: `GET /organizations`
- Create an organization: `POST /organizations`
- Get organization details: `GET /organizations/{organization_id}`
- Update an organization: `PATCH /organizations/{organization_id}`

### User Management

- List users: `GET /users`
- Get current user: `GET /users/me`
- Update user: `PATCH /users/{user_id}`

### Role-Based Access Control

- Create a role: `POST /roles`
- Assign a role: `POST /roles/{role_id}/assignments`
- Check permissions: `GET /permissions`

## Error Handling

The API uses standard HTTP status codes to indicate the success or failure of requests. In case of errors, the response body will contain more details about the error, including a message and sometimes additional information.

## Rate Limiting

Be aware that the ZenML Pro API may have rate limiting in place to ensure fair usage. If you exceed the rate limit, you may receive a 429 (Too Many Requests) status code. Implement appropriate backoff and retry logic in your applications to handle this scenario.

Remember to refer to the complete API documentation available at `https://cloudapi.zenml.io` for detailed information about all available endpoints, request/response schemas, and additional features.
<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


