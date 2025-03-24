# OSS API

The ZenML OSS server is a FastAPI application, therefore the OpenAPI-compliant docs are available at `/docs` or `/redoc`\
of your ZenML server:

{% hint style="info" %}
In the local case (i.e. using `zenml login --local`, the docs are available on `http://127.0.0.1:8237/docs`)
{% endhint %}

![ZenML API docs](../../../.gitbook/assets/zenml_api_docs.png)

![ZenML API Redoc](../../../.gitbook/assets/zenml_api_redoc.png)

## Accessing the ZenML OSS API

If you are using the ZenML OSS server API using the methods displayed above, it is enough to be logged in to your ZenML account in the same browser session. However, in order to do this programmatically, you can use one of the methods documented in the following sections.

### Using a short-lived API token

You can generate a short-lived (1 hour) API token from your ZenML dashboard. This is useful when you need a fast way to make authenticated HTTP requests to the ZenML API endpoints and you don't need a long-term solution.

1. Generate a short-lived API token through the API Tokens page under your ZenML dashboard server settings, as documented in the [Using an API token](../../../how-to/manage-zenml-server/connecting-to-zenml/connect-with-an-api-token.md) guide.
2. Use the API token as the bearer token in your HTTP requests. For example, you can use the following command to check your current user:
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
         headers={"Authorization": f"Bearer YOUR_API_TOKEN"}
       )
       print(response.json())
       ```

{% hint style="info" %}
**Important Notes**

* API tokens expire after 1 hour and cannot be retrieved after the initial generation
* Tokens are scoped to your user account and inherit your permissions
* For long-term programmatic access, it is recommended to [set up a service account and an API key](./#using-a-service-account-and-an-api-key) instead
{% endhint %}

### Using a service account and an API key

You can use a service account's API key to obtain short-lived API tokens for programmatic access to the ZenML server's REST API. This is particularly useful when you need a long-term, secure way to make authenticated HTTP requests to the ZenML API endpoints.

1.  Create a [service account](https://docs.zenml.io/how-to/manage-zenml-server/connecting-to-zenml/connect-with-a-service-account):

    ```shell
    zenml service-account create myserviceaccount
    ```

This will print out the `<ZENML_API_KEY>`, you can use in the next steps.

2. To obtain an API token using your API key, send a POST request to the `/api/v1/login` endpoint. Here are examples using common HTTP clients:
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

{% hint style="info" %}
**Important notes**

* API tokens are scoped to the service account that created them and inherit their permissions
* Tokens are temporary and will expire after a configured duration (typically 1 hour, but it depends on how the server is configured)
* You can request a new token at any time using the same API key
* For security reasons, you should handle API tokens carefully and never share them
* If your API key is compromised, you can rotate it using the ZenML dashboard or by running the `zenml service-account api-key <SERVICE_ACCOUNT_NAME> rotate` command
{% endhint %}

## Getting Started

To begin using the ZenML Server API, follow these simple steps:

{% stepper %}
{% step %}
#### Setup

Ensure you have an active ZenML server or workspace configured.
{% endstep %}

{% step %}
#### Authentication

Obtain an API token from your service account, as detailed in our core documentation.

{% tabs %}
{% tab title="OSS API" %}
* Obtain an API token from your service account
* Include the token in the authorization header: `Authorization: Bearer YOUR_API_TOKEN`
{% endtab %}

{% tab title="Pro API" %}
Use your Pro API key in the authorization header: `Authorization: Bearer YOUR_API_KEY`
{% endtab %}
{% endtabs %}
{% endstep %}

{% step %}
#### **API Access**

Use the token to authenticate and start interacting with the API endpoints.
{% endstep %}
{% endstepper %}
