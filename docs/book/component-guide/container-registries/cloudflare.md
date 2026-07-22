---
description: Storing container images in the Cloudflare container registry.
---

# Cloudflare Container Registry

The Cloudflare container registry is a [Container Registry](README.md) flavor (`cloudflare`) that stores Docker images in the [Cloudflare managed registry](https://developers.cloudflare.com/containers/platform-details/image-management/) at `registry.cloudflare.com`. It is a thin wrapper around a standard Docker registry and is useful when you build images for workloads that run on the Cloudflare platform alongside a [Cloudflare R2 Artifact Store](../artifact-stores/cloudflare-r2.md).

### When would you want to use it?

You should use the Cloudflare Container Registry when you push images that will run on Cloudflare's container platform, or when you simply want your image registry to live next to the rest of your Cloudflare infrastructure. Otherwise, one of the other [container registry flavors](README.md) is likely a better fit.

### How do you deploy it?

The Cloudflare container registry ships with the `cloudflare` integration:

```shell
zenml integration install cloudflare -y
```

You also need a Cloudflare account and to be authenticated with the registry via Docker (for example using `wrangler` or `docker login registry.cloudflare.com`). Images in the Cloudflare registry are namespaced by account.

### How do you configure it?

The registry `uri` is `registry.cloudflare.com/<account_id>`:

```shell
zenml container-registry register cloudflare_registry \
    --flavor=cloudflare \
    --uri=registry.cloudflare.com/<CLOUDFLARE_ACCOUNT_ID>

zenml stack register cloudflare_stack -c cloudflare_registry ... --set
```

For full configuration reference, run `zenml flavor describe <flavor-name>` or browse the source under `src/zenml/integrations/cloudflare/`.
