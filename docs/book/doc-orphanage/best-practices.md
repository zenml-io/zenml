---
description: Best practices, recommendations, and tips from the ZenML team
---

# Best Practices

* [ ] I believe this page should go to the end of the started guide or the beginning of the advanced guide

### Best Practices and Tips

#### Enable cache explicitly for steps that have a `context` argument, if they don't invalidate the caching behavior

Cache is implicitly disabled for steps that have a [context](../../old\_book/advanced-guide/pipelines/step-metadata.md) argument, because it is assumed that you might use the step context to retrieve artifacts from the artifact store that are unrelated to the current step. However, if that is not the case, and your step logic doesn't invalidate the caching behavior, it would be better to explicitly enable the cache for your step.

#### Check which integrations are required for registering a stack component

You can do so by running `zenml flavor list` and installing the missing integration(s) with `zenml integration install`.

### Tips

* Use `zenml GROUP explain` to explain what everything is

For a practical example on all of the above, please check out [ZenML Projects](https://github.com/zenml-io/zenml-projects) which are practical end-to-end projects built using ZenML.
