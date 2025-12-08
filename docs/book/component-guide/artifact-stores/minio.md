---
description: Storing artifacts in MinIO object storage.
---

# MinIO

[MinIO](https://min.io/) is a high-performance, S3-compatible object storage system. Since MinIO provides a fully S3-compatible API, you can use ZenML's S3 Artifact Store integration to connect to MinIO.

### When would you want to use it?

You should use the MinIO Artifact Store when:

* You require self-hosted object storage for data sovereignty or compliance requirements
* Your MLOps infrastructure runs on-premises or in a private cloud environment
* You need S3-compatible storage co-located with your Kubernetes-based ZenML deployment
* You want to eliminate cloud vendor dependencies while maintaining S3 API compatibility
* You're developing locally and need a lightweight S3-compatible storage backend for testing

### How do you deploy it?

Since MinIO is S3-compatible, you'll use the S3 integration. First, install it:

```shell
zenml integration install s3 -y
```

You'll also need a running MinIO instance. MinIO can be deployed in various ways:

* **Docker**: `docker run -p 9000:9000 -p 9001:9001 minio/minio server /data --console-address ":9001"`
* **Kubernetes**: Using the [MinIO Operator](https://min.io/docs/minio/kubernetes/upstream/)
* **Binary**: Download from [MinIO's website](https://min.io/download)

### How do you configure it?

To use MinIO with ZenML, configure the S3 Artifact Store with your MinIO endpoint:

{% tabs %}
{% tab title="Using a ZenML Secret (recommended)" %}

First, create a ZenML secret with your MinIO credentials:

```shell
zenml secret create minio_secret \
    --access_key_id='<YOUR_MINIO_ACCESS_KEY>' \
    --secret_access_key='<YOUR_MINIO_SECRET_KEY>'
```

Then register the artifact store:

```shell
zenml artifact-store register minio_store -f s3 \
    --path='s3://your-bucket-name' \
    --authentication_secret=minio_secret \
    --client_kwargs='{"endpoint_url": "http://minio.example.com:9000"}'
```
{% endtab %}
{% endtabs %}

Replace `http://minio.example.com:9000` with your actual MinIO endpoint. If you're running MinIO locally for development, this might be `http://localhost:9000`.

{% hint style="info" %}
If your MinIO instance uses HTTPS with a self-signed certificate, you may need to configure SSL verification. Consult the [S3 Artifact Store documentation](s3.md#advanced-configuration) for advanced configuration options.
{% endhint %}

Finally, add the artifact store to your stack:

```shell
zenml stack register custom_stack -a minio_store ... --set
```

### How do you use it?

Using the MinIO Artifact Store is no different from [using any other flavor of Artifact Store](./#how-to-use-it). ZenML handles the S3-compatible API translation automatically.

For more details on the S3 Artifact Store configuration options, refer to the [S3 Artifact Store documentation](s3.md).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
