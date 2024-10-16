---
description: >
  Learn about how to use the ZenML Pro API programmatically.
---

# Using the ZenML Pro API

ZenML Pro offers a powerful API that allows you to interact with your ZenML resources programmatically. Whether you're using the [SaaS version](https://cloud.zenml.io) or a self-hosted ZenML Pro instance, you can leverage this API to manage tenants, organizations, users, roles, and more.

Note, the SaaS version of ZenML Pro API is hosted [here](https://cloudapi.zenml.io)

## API Overview

The ZenML Pro API is a RESTful API that follows OpenAPI 3.1.0 specifications. It provides endpoints for various resources and operations, including:

- Tenant management
- Organization management
- User management
- Role-based access control (RBAC)
- Authentication and authorization

## Authentication

To use the ZenML Pro API, you need to authenticate your requests. The API supports OAuth 2.0 authentication with multiple flows:

1. Client Credentials flow
2. Authorization Code flow

For programmatic access, you'll typically use the Client Credentials flow. Here's how to obtain an access token:

1. Create a service account in your ZenML Pro instance.
2. Use the `/auth/login` endpoint to obtain an access token:

```bash
curl -X POST 'https://cloudapi.zenml.io/auth/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=client_credentials&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET'
```

3. The response will contain an `access_token` which you can use for subsequent API calls.

## Making API Requests

Once you have an access token, you can make API requests by including it in the `Authorization` header:

```bash
curl -X GET 'https://cloudapi.zenml.io/tenants' \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN'
```

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

## Working with Resources

When working with resources like tenants or organizations, you'll typically perform CRUD (Create, Read, Update, Delete) operations. Here's an example of creating a new tenant:

```bash
curl -X POST 'https://cloudapi.zenml.io/tenants' \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "My New Tenant",
    "description": "A tenant for my team",
    "organization_id": "YOUR_ORGANIZATION_ID"
  }'
```

## Error Handling

The API uses standard HTTP status codes to indicate the success or failure of requests. In case of errors, the response body will contain more details about the error, including a message and sometimes additional information.

## Rate Limiting

Be aware that the ZenML Pro API may have rate limiting in place to ensure fair usage. If you exceed the rate limit, you may receive a 429 (Too Many Requests) status code. Implement appropriate backoff and retry logic in your applications to handle this scenario.

Remember to refer to the complete API documentation available at `https://cloudapi.zenml.io` for detailed information about all available endpoints, request/response schemas, and additional features.