# Productionalize with CI/CD/CT


## Using Git Ops
In many production settings it is undesirable to have all developers accessing 
and running on the production environments. Instead, this is usually centralized
through the means of git ops. This same principle can be easily used for 
pipeline deployments using ZenML. [Here](https://github.com/zenml-io/zenml-gitflow)
is an example repository that shows how. The following architecture diagram
visualizes how a pipeline would be run through an automated action that is
triggered when new code is pushed to the main code repository.

![ZenML with Git Ops](../../assets/diagrams/Remote\_with\_git\_ops.png)