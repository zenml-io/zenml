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
"""SMTP Email integration for alerter components."""

from typing import List, Type

from zenml.enums import StackComponentType
from zenml.integrations.constants import SMTP_EMAIL
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

SMTP_EMAIL_ALERTER_FLAVOR = "smtp_email"

__all__ = ["SMTPEmailIntegration", "SMTP_EMAIL_ALERTER_FLAVOR"]


class SMTPEmailIntegration(Integration):
    """Definition of SMTP Email integration for ZenML.

    Implemented using the standard `smtplib` module from the Python standard
    library.
    """

    NAME = SMTP_EMAIL
    REQUIREMENTS = []  # No extra requirements as smtplib is part of standard library

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the SMTP Email integration.

        Returns:
            List of new flavors defined by the SMTP Email integration.
        """
        from zenml.integrations.smtp_email.flavors import SMTPEmailAlerterFlavor

        return [SMTPEmailAlerterFlavor]
