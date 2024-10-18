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
from zenml.config import DockerSettings

os.environ['PIP_EXTRA_INDEX_URL'] = f"https://{os.environ['PYPI_USERNAME']}:{os.environ['PYPI_PASSWORD']}@your-private-pypi-server.com/simple"

docker_settings = DockerSettings(requirements=["my-private-package==1.0.0"])

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

Note: Be cautious with handling credentials. Always use secure methods to manage
and distribute authentication information within your team.
