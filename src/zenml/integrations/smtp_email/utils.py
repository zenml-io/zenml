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
"""Utilities for SMTP Email integration."""

import re

# Email validation regex pattern
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)


def validate_email(email: str) -> str:
    """Validate email address format.
    
    Args:
        email: Email address to validate.
        
    Returns:
        The validated email address.
        
    Raises:
        ValueError: If email format is invalid.
    """
    # Basic checks
    if not email or not isinstance(email, str):
        raise ValueError(
            f"Invalid email address format: {email}. "
            "Email cannot be empty."
        )
    
    # Check basic format with regex
    if not EMAIL_REGEX.match(email):
        raise ValueError(
            f"Invalid email address format: {email}. "
            "Please provide a valid email address."
        )
    
    # Additional validation
    local, domain = email.rsplit('@', 1)
    
    # Check for consecutive dots
    if '..' in email:
        raise ValueError(
            f"Invalid email address format: {email}. "
            "Email cannot contain consecutive dots."
        )
    
    # Check local part doesn't start/end with dot
    if local.startswith('.') or local.endswith('.'):
        raise ValueError(
            f"Invalid email address format: {email}. "
            "Local part cannot start or end with a dot."
        )
    
    # Check domain doesn't start/end with dot or hyphen
    if domain.startswith('.') or domain.endswith('.') or domain.startswith('-') or domain.endswith('-'):
        raise ValueError(
            f"Invalid email address format: {email}. "
            "Domain cannot start or end with a dot or hyphen."
        )
    
    return email