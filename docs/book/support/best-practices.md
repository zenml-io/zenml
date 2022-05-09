# Best Practices


## Pass requirements to pipeline even if using default orchestrator
## Nest `p.run()` in `if __name__ == "__main__"`
## Use `zenml GROUP explain`
## Don't share metadata stores across artifact stores
## Never call the pipeline instance `pipeline` or a step instance `step`
## Recommended Repository Structure
## Use profiles to manage stacks
## Use unique pipeline names across projects, especially if used with the same metadata store
## run zenml stack up after switching stacks (but this is also enforced by validations that check if the stack is up)
## Check which integrations are required for registering a stack component by running zenml <component-type> flavor list and install the integration(s) if missing with zenml integration install
## Initialize the zenml repository in the root of the source code tree of a project, even if it's optional
## Put your runners in the root of the repository
## enable cache explicitly for steps that have a `context` argument, if they don't invalidate the caching behavior

For a practical example on all the above, please check out [ZenFiles](https://github.com/zenml-io/zenfiles), practical end-to-end projects using ZenML.