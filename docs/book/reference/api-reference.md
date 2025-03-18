---
icon: ruler
description: See the ZenML API reference.
---

# API reference

The ZenML server is a FastAPI application, therefore the OpenAPI-compliant docs are available at `/docs` or `/redoc`
of your ZenML server:

{% hint style="info" %}
In the local case (i.e. using `zenml login --local`, the docs are available on `http://127.0.0.1:8237/docs`)
{% endhint %}

![ZenML API docs](../.gitbook/assets/zenml_api_docs.png)

![ZenML API Redoc](../.gitbook/assets/zenml_api_redoc.png)

ZenML provides comprehensive API documentation for both the open-source and Pro versions:

* **OSS API Documentation**: [https://docs.zenml.io/api-reference/oss-api/oss-api](https://docs.zenml.io/api-reference/oss-api/oss-api) - Live API documentation for the open-source ZenML API.
* **Pro API Documentation**: [https://docs.zenml.io/api-reference/pro-api/pro-api](https://docs.zenml.io/api-reference/pro-api/pro-api) - Live API documentation for ZenML Pro API with additional enterprise features.

## ZenML Pro API

The ZenML Pro API extends the open-source API with additional features designed for enterprise users, including:

- Enhanced team collaboration features
- Advanced role-based access control
- Enterprise-grade security features

To access the Pro API, you need a ZenML Pro license. Refer to the [Pro API documentation](https://docs.zenml.io/api-reference/pro-api/pro-api) for detailed information on the available endpoints and features.

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

For full details on using the ZenML Pro API, including available endpoints and features, see the [Pro API guide](../getting-started/zenml-pro/pro-api.md).

## Accessing the ZenML OSS API

If you are using the ZenML OSS server API using the methods displayed above, it is enough to be logged in to your ZenML account in the same browser session. However, in order to do this programmatically, you can use one of the methods documented in the following sections.

### Using a short-lived API token

You can generate a short-lived (1 hour) API token from your ZenML dashboard. This is useful when you need a fast way to make authenticated HTTP requests to the ZenML API endpoints and you don't need a long-term solution.

1. Generate a short-lived API token through the API Tokens page under your ZenML dashboard server settings, as documented in the [Using an API token](../how-to/manage-zenml-server/connecting-to-zenml/connect-with-an-api-token.md) guide.

2. Use the API token as the bearer token in your HTTP requests. For example, you can use the following command to check your current user:
    * using curl:
      ```bash
      curl -H "Authorization: Bearer YOUR_API_TOKEN" https://your-zenml-server/api/v1/current-user
      ```
    * using wget:
      ```bash
      wget -qO- --header="Authorization: Bearer YOUR_API_TOKEN" https://your-zenml-server/api/v1/current-user
      ```
    * using python:
      ```python
      import requests

      response = requests.get(
        "https://your-zenml-server/api/v1/current-user",
        headers={"Authorization": f"Bearer YOUR_API_TOKEN"}
      )
      print(response.json())
      ```

{% hint style="info" %}
**Important Notes**

- API tokens expire after 1 hour and cannot be retrieved after the initial generation
- Tokens are scoped to your user account and inherit your permissions
- For long-term programmatic access, it is recommended to [set up a service account and an API key](#using-a-service-account-and-an-api-key) instead
{% endhint %}


### Using a service account and an API key

You can use a service account's API key to obtain short-lived API tokens for programmatic access to the ZenML server's REST API. This is particularly useful when you need a long-term, secure way to make authenticated HTTP requests to the ZenML API endpoints.

1. Create a [service account](../how-to/manage-zenml-server/connecting-to-zenml/connect-with-a-service-account.md):
    ```shell
    zenml service-account create myserviceaccount
    ```

This will print out the `<ZENML_API_KEY>`, you can use in the next steps.

2. To obtain an API token using your API key, send a POST request to the `/api/v1/login` endpoint. Here are examples using common HTTP clients:
    * using curl:
      ```bash
      curl -X POST -d "password=<YOUR_API_KEY>" https://your-zenml-server/api/v1/login
      ```
    * using wget:
      ```bash
      wget -qO- --post-data="password=<YOUR_API_KEY>" \
          --header="Content-Type: application/x-www-form-urlencoded" \
          https://your-zenml-server/api/v1/login
      ```
    * using python:
      ```python
      import requests
      import json

      response = requests.post(
          "https://your-zenml-server/api/v1/login",
          data={"password": "<YOUR_API_KEY>"},
          headers={"Content-Type": "application/x-www-form-urlencoded"}
      )

      print(response.json())
      ```

This will return a response like this:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3MGJjZTg5NC1hN2VjLTRkOTYtYjE1Ny1kOTZkYWY5ZWM2M2IiLCJpc3MiOiJmMGQ5NjI1Ni04YmQyLTQxZDctOWVjZi0xMmYwM2JmYTVlMTYiLCJhdWQiOiJmMGQ5NjI1Ni04YmQyLTQxZDctOWVjZi0xMmYwM2JmYTVlMTYiLCJleHAiOjE3MTk0MDk0NjAsImFwaV9rZXlfaWQiOiIzNDkyM2U0NS0zMGFlLTRkMjctODZiZS0wZGRhNTdkMjA5MDcifQ.ByB1ngCPtBenGE6UugsWC6Blga3qPqkAiPJUSFDR-u4",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": null,
  "scope": null
}
```

3. Once you have obtained an API token, you can use it to authenticate your API requests by including it in the `Authorization` header. For example, you can use the following command to check your current user:
    * using curl:
      ```bash
      curl -H "Authorization: Bearer YOUR_API_TOKEN" https://your-zenml-server/api/v1/current-user
      ```
    * using wget:
      ```bash
      wget -qO- --header="Authorization: Bearer YOUR_API_TOKEN" https://your-zenml-server/api/v1/current-user
      ```
    * using python:
      ```python
      import requests

      response = requests.get(
          "https://your-zenml-server/api/v1/current-user",
          headers={"Authorization": f"Bearer {YOUR_API_TOKEN}"}
      )

      print(response.json())
      ```

{% hint style="info" %}
**Important notes**

* API tokens are scoped to the service account that created them and inherit their permissions
* Tokens are temporary and will expire after a configured duration (typically 1 hour, but it depends on how the server is configured)
* You can request a new token at any time using the same API key
* For security reasons, you should handle API tokens carefully and never share them
* If your API key is compromised, you can rotate it using the ZenML dashboard or by running the `zenml service-account api-key <SERVICE_ACCOUNT_NAME> rotate` command
{% endhint %}


<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
