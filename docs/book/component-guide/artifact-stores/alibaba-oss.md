---
description: Storing artifacts in Alibaba Cloud Object Storage Service (OSS).
---

# Alibaba Cloud OSS

[Alibaba Cloud Object Storage Service (OSS)](https://www.alibabacloud.com/product/object-storage-service) is an S3-compatible object storage service. Since OSS provides an S3-compatible API, you can use ZenML's S3 Artifact Store integration to connect to [Alibaba Cloud](https://www.alibabacloud.com) OSS.

{% hint style="warning" %}
**Important:** When using Alibaba Cloud OSS, you must set the following `config_kwargs`:

```json
{"signature_version": "s3", "s3": {"addressing_style": "virtual"}}
```

This is required for proper compatibility with Alibaba Cloud OSS's S3 API implementation.
{% endhint %}

### When would you want to use it?

You should use the Alibaba Cloud OSS Artifact Store when:

* Your infrastructure is already deployed on Alibaba Cloud and you want to maintain data locality
* You require artifact storage in specific geographic regions served by Alibaba Cloud (China, Asia-Pacific, Europe, Middle East)
* You need S3-compatible object storage with Alibaba Cloud's pricing model and service level agreements
* Compliance requirements mandate data residency in Alibaba Cloud regions

### How do you deploy it?

Since Alibaba Cloud OSS is S3-compatible, you'll use the S3 integration. First, install it:

```shell
zenml integration install s3 -y
```

You'll also need to create an OSS bucket and obtain your access credentials from the Alibaba Cloud console.

### How do you configure it?

To use Alibaba Cloud OSS with ZenML, you need to configure the S3 Artifact Store with specific settings for OSS compatibility:

{% hint style="info" %}  
Alibaba Cloud OSS does not support ZenML Service Connectors. Use ZenML Secrets to securely store and reference your Alibaba Cloud credentials.  
{% endhint %} 

{% tabs %}
{% tab title="Using a ZenML Secret (recommended)" %}

First, create a ZenML secret with your Alibaba Cloud credentials:

```shell
zenml secret create alibaba_secret \
    --access_key_id='<YOUR_ALIBABA_ACCESS_KEY_ID>' \
    --secret_access_key='<YOUR_ALIBABA_SECRET_ACCESS_KEY>'
```

Then register the artifact store with the required OSS configuration:

```shell
zenml artifact-store register alibaba_store -f s3 \
    --path='s3://your-bucket-name' \
    --authentication_secret=alibaba_secret \
    --client_kwargs='{"endpoint_url": "https://oss-<region>.aliyuncs.com"}' \
    --config_kwargs='{"signature_version": "s3", "s3": {"addressing_style": "virtual"}}'
```
{% endtab %}
{% endtabs %}

Replace `<region>` with your OSS region (e.g., `eu-central-1`, `cn-hangzhou`, `ap-southeast-1`). You can find the list of available regions and their endpoints in the [Alibaba Cloud OSS documentation](https://www.alibabacloud.com/help/en/oss/user-guide/regions-and-endpoints).

Finally, add the artifact store to your stack:

```shell
zenml stack register custom_stack -a alibaba_store ... --set
```

### How do you use it?

Using the Alibaba Cloud OSS Artifact Store is no different from [using any other flavor of Artifact Store](./#how-to-use-it). ZenML handles the S3-compatible API translation automatically.

For more details on the S3 Artifact Store configuration options, refer to the [S3 Artifact Store documentation](s3.md).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
