---
icon: person-from-portal
---

# Getting Started

The ZenML OSS server is a FastAPI application, therefore the OpenAPI-compliant docs are available at `/docs` or `/redoc` of your ZenML server:

{% hint style="info" %}
In the local case (i.e. using `zenml login --local`, the docs are available on `http://127.0.0.1:8237/docs`)
{% endhint %}

![ZenML API docs](../../../.gitbook/assets/zenml_api_docs.png)

{% hint style="info" %}
**Difference between OpenAPI docs and ReDoc**

The OpenAPI docs (`/docs`) provide an interactive interface where you can try out the API endpoints directly from the browser. It is useful for testing and exploring the API functionalities.

ReDoc (`/redoc`), on the other hand, offers a more static and visually appealing documentation. It is designed for better readability and is ideal for understanding the API structure and reference.
{% endhint %}

![ZenML API Redoc](../../../.gitbook/assets/zenml_api_redoc.png)

## Accessing the ZenML OSS API

**For OSS users**: The `server_url` is the root URL of your ZenML server deployment.

If you are using the ZenML OSS server API using the methods displayed above, it is enough to be logged in to your ZenML account in the same browser session. However, in order to do this programmatically, you can use one of the methods documented in the following sections.

{% hint style="info" %}
Choosing a method:

- Humans at the CLI: use [interactive login](https://docs.zenml.io/how-to/manage-zenml-server/connecting-to-zenml/connect-in-with-your-user-interactive).
- CI/CD and automation: use [service accounts + API keys](https://docs.zenml.io/how-to/manage-zenml-server/connecting-to-zenml/connect-with-a-service-account).
{% endhint %}

### Using a service account and an API key

You can use a service account's API key to authenticate to the ZenML server's REST API programmatically. This is particularly useful when you need a long-term, secure way to make authenticated HTTP requests to the ZenML API endpoints.

Start by [creating a service account and an API key](https://docs.zenml.io/how-to/manage-zenml-server/connecting-to-zenml/connect-with-a-service-account), e.g.:

    ```shell
    zenml service-account create myserviceaccount
    ```

Then, there are two methods to authenticate with the API using the API key - one is simpler but less secure, the other is secure and recommended but more complex:

{% tabs %}
{% tab title="Direct API key authentication" %}

{% hint style="warning" %}
This approach, albeit simple, is not recommended because the long-lived API key is exposed with every API request, which makes it easier to be compromised. Use it only in low-risk circumstances.
{% endhint %}

Use the API key directly to authenticate your API requests by including it in the `Authorization` header. For example, you can use the following command to check your current user:

   *   using curl:

       ```bash
       curl -H "Authorization: Bearer YOUR_API_KEY" https://your-zenml-server/api/v1/current-user
       ```
   *   using wget:

       ```bash
       wget -qO- --header="Authorization: Bearer YOUR_API_KEY" https://your-zenml-server/api/v1/current-user
       ```
   *   using python:

       ```python
       import requests

       response = requests.get(
           "https://your-zenml-server/api/v1/current-user",
           headers={"Authorization": f"Bearer {YOUR_API_KEY}"}
       )

       print(response.json())
       ```

{% endtab %}

{% tab title="Token exchange authentication" %}

Reduce the risk of API key exposure by periodically exchanging the API key for a short-lived API token.

1. To obtain an API access token using your API key, send a POST request to the `/api/v1/login` endpoint. Here are examples using common HTTP clients:
   *   using curl:

       ```bash
       curl -X POST -d "password=<YOUR_API_KEY>" https://your-zenml-server/api/v1/login
       ```
   *   using wget:

       ```bash
       wget -qO- --post-data="password=<YOUR_API_KEY>" \
           --header="Content-Type: application/x-www-form-urlencoded" \
           https://your-zenml-server/api/v1/login
       ```
   *   using python:

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

This will return a response like this (the short-lived API token is the `access_token` field):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3MGJjZTg5NC1hN2VjLTRkOTYtYjE1Ny1kOTZkYWY5ZWM2M2IiLCJpc3MiOiJmMGQ5NjI1Ni04YmQyLTQxZDctOWVjZi0xMmYwM2JmYTVlMTYiLCJhdWQiOiJmMGQ5NjI1Ni04YmQyLTQxZDctOWVjZi0xMmYwM2JmYTVlMTYiLCJleHAiOjE3MTk0MDk0NjAsImFwaV9rZXlfaWQiOiIzNDkyM2U0NS0zMGFlLTRkMjctODZiZS0wZGRhNTdkMjA5MDcifQ.ByB1ngCPtBenGE6UugsWC6Blga3qPqkAiPJUSFDR-u4",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": null,
  "scope": null
}
```

2. Once you have obtained a short-lived API token, you can use it to authenticate your API requests by including it in the `Authorization` header. When the short-lived API token expires, simply repeat the steps above to obtain a new one. For example, you can use the following command to check your current user:
   *   using curl:

       ```bash
       curl -H "Authorization: Bearer YOUR_API_TOKEN" https://your-zenml-server/api/v1/current-user
       ```
   *   using wget:

       ```bash
       wget -qO- --header="Authorization: Bearer YOUR_API_TOKEN" https://your-zenml-server/api/v1/current-user
       ```
   *   using python:

       ```python
       import requests

       response = requests.get(
           "https://your-zenml-server/api/v1/current-user",
           headers={"Authorization": f"Bearer {YOUR_API_TOKEN}"}
       )

       print(response.json())
       ```

{% endtab %}
{% endtabs %}

{% hint style="info" %}
**Important notes**

* Short-lived API tokens are scoped to the service account that created them and inherit their permissions
* Tokens are temporary and will expire after a configured duration (typically 1 hour, but it depends on how the server is configured)
* You can request a new short-lived API token at any time using the same API key
* For security reasons, you should handle short-lived API tokens carefully and never share them
* If your API key is compromised, you can rotate it using the ZenML dashboard or by running the `zenml service-account api-key <SERVICE_ACCOUNT_NAME> rotate` command
{% endhint %}
