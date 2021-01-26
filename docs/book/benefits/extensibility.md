# Extensibility in ZenML
ZenML is designed with extensibility in mind. This means that the goal of ZenML is to be able to work with any 
ML tool in the eco-system seamlessly. There are multiple ways to use ZenML with other libraries.

## Integrations
ZenML uses the `extra_requires` field provided in Python [setuptools](https://setuptools.readthedocs.io/en/latest/setuptools.html) 
which allows for defining plugin-like dependencies for integrations. These integrations can then accessed via pip at installation time 
with the `[]` operators. E.g.

```bash
pip install zenml[pytorch]
```

Will unlock the `pytorch` integration for ZenML, allowing users to use the `PyTorchTrianerStep` for example.

In order to see the full list of integrations available, see the [setup.py on GitHub](https://github.com/maiot-io/zenml/blob/main/setup.py).

We would be happy to see [your contributions for more integrations](https://github.com/maiot-io/zenml/) if the ones we have currently support 
not fulfil your requirements. Also let us know via [slack](https://zenml.io/slack-invite) what integrations to add!

## Other libraries
If the integrations above do not fulfill your requirements and more dependencies are required, then there is always the option to simply 
install the dependencies alongside ZenML in your repository, and then create [custom steps](../steps/what-is-a-step.md) for your logic. 

If going down this route, one must ensure that the added dependencies do not clash with any [dependency bundled with ZenML](https://github.com/maiot-io/zenml/blob/main/setup.py). 
A good way to check is to [create a custom Docker image](../backends/using-docker.md) with the ZenML base image and then run a simple pipeline to make sure everything works.
