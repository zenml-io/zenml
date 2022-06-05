#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from typing import Any, ClassVar, Dict, List, Optional

import hvac 
import re
from zenml.exceptions import SecretDoesNotExistError, SecretExistsError
from zenml.integrations.gcp_secrets_manager import VAULT_SECRETS_MANAGER_FLAVOR
from zenml.logger import get_logger
from zenml.secret.base_secret import BaseSecretSchema
from zenml.secret.secret_schema_class_registry import SecretSchemaClassRegistry
from zenml.secrets_managers.base_secrets_manager import BaseSecretsManager

logger = get_logger(__name__)

ZENML_SCHEMA_NAME = "zenml-schema-name"
ZENML_PATH = "zenml"


def sanitize_secret_name(secret_name: str) -> str:
    """Sanitize the secret name to be used in Vault."""
    return re.sub(r"[^0-9a-zA-Z_\.]+", "_", secret_name).strip(
                "-_."
            )
    
def prepend_secret_schema_to_secret_name(secret: BaseSecretSchema) -> str:
    """This function adds the secret group name to the keys of each
    secret key-value pair to allow using the same key across multiple
    secrets.

    Args:
        secret: The ZenML Secret schema
    """
    secret_name = sanitize_secret_name(secret.name)
    secret_schema_name = secret.__name__
    return f"{secret_schema_name}-{secret_name}"


def remove_secret_schema_name(combined_secret_name: str) -> str:
    """
    """
    if "-" in combined_secret_name:
        return combined_secret_name.split("-")[1]
    else:
        raise RuntimeError(
            f"Secret name `{combined_secret_name}` does not have a "
            f"Secret_schema name on it."
        )

def get_secret_schema_name(combined_secret_name: str) -> str:
    """
    """
    if "-" in combined_secret_name:
        return combined_secret_name.split("-")[0]
    else:
        raise RuntimeError(
            f"Secret name `{combined_secret_name}` does not have a "
            f"Secret_schema name on it."
        )

class VaultSecretsManager(BaseSecretsManager):
    """Class to interact with the GCP secrets manager.

    Attributes:
        project_id:  This is necessary to access the correct GCP project.
                     The project_id of your GCP project space that contains
                     the Secret Manager.
    """
    
    # Class configuration
    FLAVOR: ClassVar[str] = "vault"

    url: Optional[str]
    token: Optional[str]
    cert: Optional[str]
    verify: Optional[str]
    namespace: Optional[str]
    mount_point: Optional[str] = "secret"

    #private attribute 
    _client: Optional[hvac.Client] = None


    @property
    def hvac_client(self) -> hvac.Client:
        """ 
        
        """
        if not self._client:
            self._client = hvac.Client(
                url=self.url,
                token=self.token,
            )

        return self._client
                
             
        
    def register_secret(self, secret: BaseSecretSchema) -> None:
        """Registers a new secret.

        Args:
            secret: The secret to register.
        """
        if not self._client.is_authenticated():
            raise RuntimeError("Vault client is not authenticated.")

        secret_name = prepend_secret_schema_to_secret_name(secret=secret)
        
        if secret_name in self.get_all_secret_keys():
            raise SecretExistsError(
                f"A Secret with the name '{secret_name}' already exists."
            )

        self._client.secrets.kv.v2.create_or_update_secret(
            path=f"{ZENML_PATH}/{secret_name}",
            secret=secret.content.items(),
            )
        
        logger.debug("Created created secret: %s", f"{ZENML_PATH}/{secret_name}")
        logger.debug("Added value to secret.")
       
    def get_secret(self, secret_name: str) -> BaseSecretSchema:
        """Gets the value of a secret.

        Args:
            secret_name: The name of the secret to get.
        """
        # 
        secrets_keys = self.get_all_secret_keys()

        for secret_key in secrets_keys:
            if sanitize_secret_name(secret_name) == remove_secret_schema_name(secret_key):    
                try : 
                    secret_items = self._client.secrets.kv.v2.read_secret_version(
                        path=f"{ZENML_PATH}/{secret_key}",mount_point=self.mount_point
                    ).get("data", {}).get("data", {})
                except hvac.exceptions.InvalidPath:
                    raise (
                        f"The secret {secret_name} does not exist."
                    )
                    secret_schema = SecretSchemaClassRegistry.get_class(
                        secret_schema=get_secret_schema_name(secret_key)
                    )
                    return secret_schema(**secret_items)
        return(
                f"the secret {secret_name} does not exist."
            )    
        

    def get_all_secret_keys(self) -> List[str]:
        """Get all secret keys."""

        if not self._client.is_authenticated():
            raise RuntimeError("Vault client is not authenticated.")

        set_of_secrets = set()
        try:
            secrets = self._client.secrets.kv.v2.list_secrets(path=ZENML_PATH, mount_point=self.mount_point)
        except hvac.exceptions.InvalidPath:
            return(
                f"There are no secrets created within the path `{ZENML_PATH}` "
            )
        
        secrets_keys = secrets.get("data", {}).get("keys", [])
        for secret_key in secrets_keys:
            secret_key = remove_secret_schema_name(secret_key)
            set_of_secrets.add(secret_key)
        return list(set_of_secrets)


    def update_secret(self, secret: BaseSecretSchema) -> None:
        """Update an existing secret.

        Args:
            secret: The secret to update.
        """
        if not self._client.is_authenticated():
            raise RuntimeError("Vault client is not authenticated.")

        if secret.name in self.get_all_secret_keys():
            raise SecretDoesNotExistError(
                f"A Secret with the name '{secret.name}' does not exist."
            )
        
        self._client.secrets.kv.v2.create_or_update_secret(
            path=f"{ZENML_PATH}/{secret.name}",
            secret=secret.content.items(),
            )
        
        logger.debug("Updated secret: %s", f"{ZENML_PATH}/{secret.name}")
        logger.debug("Added value to secret.")
        

    def delete_secret(self, secret_name: str) -> None:
        """Delete an existing secret.

        Args:
            secret_name: The name of the secret to delete.
        """
        if not self._client.is_authenticated():
            raise RuntimeError("Vault client is not authenticated.")

        if secret_name in self.get_all_secret_keys():
            raise SecretDoesNotExistError(
                f"A Secret with the name '{secret_name}' does not exist."
            )
        
        self._client.secrets.kv.v2.delete_secret_versions(
            path=f"{ZENML_PATH}/{secret_name}",
            )
        
        logger.debug("Deleted secret: %s", f"{ZENML_PATH}/{secret_name}")
    

    def delete_all_secrets(self, force: bool = False) -> None:
        """Delete all existing secrets.

        Args:
            force: Whether to force deletion of secrets.
        """
        
        for secret_name in self.get_all_secret_keys():
            self.delete_secret(secret_name=secret_name)
        
