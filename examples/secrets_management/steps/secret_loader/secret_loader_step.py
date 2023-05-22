#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from rich import print

from zenml import step
from zenml.client import Client

SECRET_NAME = "example-secret"
SECRET_KEY = "example_secret_key"


@step
def secret_loader() -> None:
    """Load the example secret from the secrets store."""
    client = Client()

    try:
        secret = client.get_secret(
            name_id_or_prefix=SECRET_NAME,
        )
    except KeyError:
        print(
            f"Could not find secret `{SECRET_NAME}`. "
            f"Please run `zenml secrets create` to create it."
        )
        return

    # Load specific secret value from the secret using the secret key
    print(
        f"The secret `{SECRET_NAME}` contains the following key-value pair "
        f"{{{SECRET_KEY}: {secret.secret_values}}}"
    )
    return
