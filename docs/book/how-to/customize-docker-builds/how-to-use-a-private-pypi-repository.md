---
description: How to use a private PyPI repository.
---

# How to use a private PyPI repository

For packages that require authentication, you may need to take additional steps:

1. Use environment variables to store credentials securely.
2. Configure pip or poetry to use these credentials when installing packages.
3. Consider using custom Docker images that have the necessary authentication setup.

Here's an example of how you might set up authentication using environment variables:

```python
import os

from my_simple_package import important_function
from zenml.config import DockerSettings
from zenml import step, pipeline

docker_settings = DockerSettings(
    requirements=["my-simple-package==0.1.0"],
    environment={'PIP_EXTRA_INDEX_URL': f"https://{os.environ.get('PYPI_TOKEN', '')}@my-private-pypi-server.com/{os.environ.get('PYPI_USERNAME', '')}/"}
)

@step
def my_step():
    return important_function()

@pipeline(settings={"docker": docker_settings})
def my_pipeline():
    my_step()

if __name__ == "__main__":
    my_pipeline()
```

Note: Be cautious with handling credentials. Always use secure methods to manage
and distribute authentication information within your team.
<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


