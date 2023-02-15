- terraform modules folder needs to be included in the pulled recipe
- recipe deployment will result in the creation of a stack with the components
that the user has chosen through the tf file (locals or variables)
- there should be a way to specify what stack components to use through the deploy cli

```
zenml stack recipe deploy gcp-modular --mlflow --seldon
```

this would also mean that some validation needs to be done either at the recipe level or the cli level for components that won't work together=> mostly everything works with each other

mlflow and zenml tls only works with nginx ingress and not with istio
for now, we can keep it as it is but we need to make sure that the user is aware of this. plus this should be fixed with the ticket on updating existing stack recipes in the next sprint.
