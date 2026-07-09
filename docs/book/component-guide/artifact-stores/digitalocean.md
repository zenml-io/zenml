---
description: Storing artifacts in a DigitalOcean Spaces bucket.
---

# DigitalOcean Spaces

The DigitalOcean Spaces Artifact Store is an [Artifact Store](./) flavor provided with the DigitalOcean ZenML integration that uses [DigitalOcean Spaces](https://www.digitalocean.com/products/spaces) to store ZenML artifacts. Spaces exposes an [S3-compatible API](https://docs.digitalocean.com/products/spaces/reference/s3-compatibility/), so this flavor reuses ZenML's S3 implementation under the hood and only adds a `region` setting from which the Spaces endpoint URL is derived at runtime.

### When would you want to use it?

Running ZenML pipelines with [the local Artifact Store](local.md) is usually sufficient if you just want to evaluate ZenML or get started quickly. However, the local Artifact Store becomes insufficient once you want to share pipeline results with teammates, run other stack components remotely (e.g. an orchestrator on DigitalOcean Kubernetes), or run production-grade pipelines at scale.

You should use the DigitalOcean Spaces Artifact Store when your infrastructure runs on DigitalOcean and you want your ZenML artifacts co-located with it — for example next to a DOKS cluster running the [Kubernetes orchestrator](https://docs.zenml.io/stacks/orchestrators/kubernetes). Because the integration speaks the S3-compatible Spaces API, you get the same workflow as the [S3 Artifact Store](s3.md) without managing any additional tooling. Consider one of the other [Artifact Store flavors](./#artifact-store-flavors) if you don't use DigitalOcean.

### How do you deploy it?

The DigitalOcean Spaces Artifact Store flavor is provided by the DigitalOcean ZenML integration. Install it on your local machine to be able to register the artifact store and add it to your stack:

```shell
zenml integration install digitalocean -y
```

You will also need a Space (bucket) and a set of Spaces access keys:

1. **Create a Space.** In the [DigitalOcean control panel](https://cloud.digitalocean.com/), go to **Spaces Object Storage** and create a bucket. Note the bucket name (this becomes the `s3://<bucket-name>` path used by ZenML) and the region slug shown in the bucket's endpoint (e.g. `nyc3`, `ams3`, `fra1`).
2. **Generate Spaces access keys.** Go to **API > Spaces Keys** and generate a new key pair. Spaces keys are separate credentials from your DigitalOcean API token; copy both the access key and the secret when they are displayed.

### How do you use it?

Register the artifact store with the bucket path (using the `s3://` scheme, since Spaces speaks the S3 API) and the region slug:

```shell
zenml artifact-store register do_spaces \
    --flavor=digitalocean_spaces \
    --path=s3://my-space \
    --region=fra1

# Register and set a stack that uses the new artifact store
zenml stack register do_stack -a do_spaces ... --set
```

The Spaces endpoint URL (`https://<region>.digitaloceanspaces.com`) is derived from the `region` at runtime and is not persisted in the component configuration. If you need to address a different endpoint (for example a custom domain), pass it explicitly instead — an explicit endpoint always takes precedence over the region-derived one:

```shell
zenml artifact-store register do_spaces \
    --flavor=digitalocean_spaces \
    --path=s3://my-space \
    --client_kwargs='{"endpoint_url": "https://fra1.digitaloceanspaces.com"}'
```

To authenticate, store the Spaces access keys in a [ZenML Secret](https://docs.zenml.io/getting-started/deploying-zenml/secret-management) and reference them on registration:

```shell
zenml secret create spaces_secret \
    --access_key_id='<YOUR_SPACES_ACCESS_KEY>' \
    --secret_access_key='<YOUR_SPACES_SECRET_KEY>'

zenml artifact-store register do_spaces \
    --flavor=digitalocean_spaces \
    --path=s3://my-space \
    --region=fra1 \
    --key='{{spaces_secret.access_key_id}}' \
    --secret='{{spaces_secret.secret_access_key}}'
```

All other configuration options of the [S3 Artifact Store](s3.md) (`client_kwargs`, `config_kwargs`, `s3_additional_kwargs`) are available on this flavor as well and are passed through to the underlying S3-compatible filesystem.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
