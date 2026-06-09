---
description: Storing artifacts in Cloudflare R2 object storage.
---

# Cloudflare R2

[Cloudflare R2](https://developers.cloudflare.com/r2/) is an S3-compatible object storage service with zero egress fees. ZenML ships a dedicated R2 Artifact Store flavor (`r2`) that reuses the battle-tested S3 filesystem stack under the hood, so it behaves just like the [S3 Artifact Store](s3.md) while pointing at the R2 S3 API endpoint.

### When would you want to use it?

You should use the Cloudflare R2 Artifact Store when:

* You already run other workloads on the Cloudflare developer platform and want artifacts co-located with them.
* You want to avoid egress fees on frequently downloaded artifacts.
* You need S3-compatible storage but prefer Cloudflare over AWS as your provider.

If you are not using Cloudflare, one of the other [artifact store flavors](README.md) is likely a better fit.

### How do you deploy it?

The R2 Artifact Store ships with the `cloudflare` integration:

```shell
zenml integration install cloudflare -y
```

You also need an R2 bucket and an [R2 API token](https://developers.cloudflare.com/r2/api/s3/tokens/) (which provides an S3-compatible Access Key ID and Secret Access Key), plus your Cloudflare account ID.

### How do you configure it?

The artifact store path uses the `r2://` scheme. The R2 S3 API endpoint is derived automatically from your account ID:

```shell
zenml artifact-store register cloudflare_store \
    --flavor=r2 \
    --path=r2://my-bucket/artifacts \
    --account_id=<CLOUDFLARE_ACCOUNT_ID> \
    --key=<R2_ACCESS_KEY_ID> \
    --secret=<R2_SECRET_ACCESS_KEY>

zenml stack register cloudflare_stack -a cloudflare_store ... --set
```

{% hint style="info" %}
The `account_id` is used to build the endpoint `https://<account_id>.r2.cloudflarestorage.com`. If you prefer, you can skip `account_id` and pass the endpoint directly via `client_kwargs`:

```shell
zenml artifact-store register cloudflare_store --flavor=r2 \
    --path=r2://my-bucket/artifacts \
    --key=<R2_ACCESS_KEY_ID> --secret=<R2_SECRET_ACCESS_KEY> \
    --client_kwargs='{"endpoint_url": "https://<account_id>.r2.cloudflarestorage.com"}'
```
{% endhint %}

Because R2 is S3-compatible, the same `client_kwargs`, `config_kwargs` and `s3_additional_kwargs` options documented for the [S3 Artifact Store](s3.md) are available here. R2 ignores the AWS region, but ZenML defaults the signing region to `auto` (the value Cloudflare documents for S3-compatible clients).

For full configuration reference, run `zenml flavor describe <flavor-name>` or browse the source under `src/zenml/integrations/cloudflare/`.
