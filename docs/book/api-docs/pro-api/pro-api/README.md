# Pro API

The ZenML Pro API extends the open-source API with additional features designed for enterprise users, including:

- Enhanced team collaboration features
- Advanced role-based access control
- Enterprise-grade security features

### Accessing the ZenML Pro API

The ZenML Pro API is distinct from the OSS server API:

- The SaaS version of ZenML Pro API is hosted at [https://cloudapi.zenml.io](https://cloudapi.zenml.io)
- You can access the API docs directly at [https://cloudapi.zenml.io](https://cloudapi.zenml.io)
- If you're logged into your ZenML Pro account at [https://cloud.zenml.io](https://cloud.zenml.io), you can use the same browser session to authenticate requests directly in the OpenAPI docs

### Pro API Authentication

To programmatically access the ZenML Pro API:

1. Navigate to the organization settings page in your ZenML Pro dashboard
2. Select "API Tokens" from the left sidebar
3. Click the "Create new token" button to generate a new API token
4. Use the API token as the bearer token in your HTTP requests:

```bash
# Example of accessing the Pro API
curl -H "Authorization: Bearer YOUR_API_TOKEN" https://cloudapi.zenml.io/users/me
```

Note that for workspace programmatic access, you can use the same methods described below for the OSS API (temporary API tokens or service accounts).

For full details on using the ZenML Pro API, including available endpoints and features, see the [Pro API guide](https://docs.zenml.io/pro/deployments/pro-api).