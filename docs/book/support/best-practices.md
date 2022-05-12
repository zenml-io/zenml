# Best Practices, Recommendations, and Tips

# Recommended Repository Structure

```
├── pipelines
│   ├── controller
│   │   ├── **/*.css
│   ├── views
│   ├── model
│   ├── index.js
├── steps
│   ├── css
│   │   ├── **/*.css
│   ├── images
│   ├── js
│   ├── index.html
├── steps
│   ├── css
│   │   ├── **/*.css
│   ├── images
│   ├── js
│   ├── index.html
├── Dockerfile
├── .Dockerignore
├── gitignore
└── .zen
```

# Best Practices

# Best Practices and Tips
## Pass requirements to pipeline even if using default orchestrator
## Nest `p.run()` in `if __name__ == "__main__"`
## Don't share metadata stores across artifact stores
## Never call the pipeline instance `pipeline` or a step instance `step`
## Use profiles to manage stacks
## Use unique pipeline names across projects, especially if used with the same metadata store
## Check which integrations are required for registering a stack component by running zenml <component-type> flavor list and install the integration(s) if missing with zenml integration install
## Initialize the zenml repository in the root of the source code tree of a project, even if it's optional
## Put your runners in the root of the repository
## enable cache explicitly for steps that have a `context` argument, if they don't invalidate the caching behavior
## include a .dockerignore in the zenml repository to exclude files and folders from the container images built by ZenML for containerized environments, like Kubeflow and some step operators
## use get_pipeline_run(RUN_NAME) instead of indexing ([-1]) into the full list of pipeline runs
## Explicitly disable caching when loading data from fs or external APIs
## Have your imports relative to your .zen directory OR have your imports relative to the root of your repository in cases when you dont have a .zen directory (=> which means to have the runner at the root of your repository)

# Tips

## Use `zenml GROUP explain` to explain what everything is

## run `zenml stack up` after switching stacks (but this is also enforced by validations that check if the stack is up)

For a practical example on all the above, please check out [ZenFiles](https://github.com/zenml-io/zenfiles), practical end-to-end projects using ZenML.