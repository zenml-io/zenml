# Reference environment variables in configurations

To make your configurations in code as well as in configuration files more flexible, ZenML allows you to reference environment variables
by using the following placeholder syntax in your configuration: `${ENV_VARIABLE_NAME}`

## In-code

```python
from zenml import step

@step(extra={"value_from_environment": "${ENV_VAR}"})
def my_step() -> None:
    ...
```

# In a configuration file

```yaml
extra:
  value_from_environment: ${ENV_VAR}
  combined_value: prefix_${ENV_VAR}_suffix
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
