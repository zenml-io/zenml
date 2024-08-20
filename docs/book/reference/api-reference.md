---
description: See the ZenML API reference.
---

# 👀 API reference

The ZenML server is a FastAPI application, therefore the OpenAPI-compliant docs are available at `/docs` or `/redoc`
of your ZenML server:

{% hint style="info" %}
In the local case (i.e. using `zenml up`, the docs are available on `http://127.0.0.1:8237/docs`)
{% endhint %}

![ZenML API docs](../.gitbook/assets/zenml_api_docs.png)

![ZenML API Redoc](../.gitbook/assets/zenml_api_redoc.png)

## Using a bearer token to access the API programmatically

If you are using the ZenML server API using the above pages, it is enough to be logged in to your ZenML
account in the same browser session. However, in order to do this programmatically, the following steps
need to be followed:

1. Create a [service account](../how-to/connecting-to-zenml/connect-with-a-service-account.md):

```shell
zenml service-account create myserviceaccount
```

This will print out the `<ZENML_API_KEY>`, you can use in the next command.

2. Get an access token by using the `/api/v1/login` endpoint:

```shell

curl -X 'POST' \
  '<YOUR_ZENML_SERVER_URL>/api/v1/login' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=zenml-api-key&username=&password=<ZENML_API_KEY>'\''&client_id=&device_code='
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

3. Use the access token to make subsequent curl commands:

```shell
curl -X 'GET' \
  '<YOUR_ZENML_SERVER_URL>/api/v1/pipelines?hydrate=false&name=training' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <ACCESS_TOKEN>'
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
