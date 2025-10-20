#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Secure headers for the ZenML Server."""

from typing import Optional

import secure

from zenml.zen_server.utils import server_config

_secure_headers: Optional[secure.Secure] = None


def secure_headers() -> secure.Secure:
    """Return the secure headers component.

    Returns:
        The secure headers component.

    Raises:
        RuntimeError: If the secure headers component is not initialized.
    """
    global _secure_headers
    if _secure_headers is None:
        raise RuntimeError("Secure headers component not initialized")
    return _secure_headers


def initialize_secure_headers() -> None:
    """Initialize the secure headers component."""
    global _secure_headers

    config = server_config()

    # For each of the secure headers supported by the `secure` library, we
    # check if the corresponding configuration is set in the server
    # configuration:
    #
    # - if set to `True`, we use the default value for the header
    # - if set to a string, we use the string as the value for the header
    # - if set to `False`, we don't set the header

    server: Optional[secure.Server] = None
    if config.secure_headers_server:
        server = secure.Server()
        if isinstance(config.secure_headers_server, str):
            server.set(config.secure_headers_server)
        else:
            server.set(str(config.deployment_id))

    hsts: Optional[secure.StrictTransportSecurity] = None
    if config.secure_headers_hsts:
        hsts = secure.StrictTransportSecurity()
        if isinstance(config.secure_headers_hsts, str):
            hsts.set(config.secure_headers_hsts)

    xfo: Optional[secure.XFrameOptions] = None
    if config.secure_headers_xfo:
        xfo = secure.XFrameOptions()
        if isinstance(config.secure_headers_xfo, str):
            xfo.set(config.secure_headers_xfo)

    csp: Optional[secure.ContentSecurityPolicy] = None
    if config.secure_headers_csp:
        csp = secure.ContentSecurityPolicy()
        if isinstance(config.secure_headers_csp, str):
            csp.set(config.secure_headers_csp)

    xcto: Optional[secure.XContentTypeOptions] = None
    if config.secure_headers_content:
        xcto = secure.XContentTypeOptions()
        if isinstance(config.secure_headers_content, str):
            xcto.set(config.secure_headers_content)

    referrer: Optional[secure.ReferrerPolicy] = None
    if config.secure_headers_referrer:
        referrer = secure.ReferrerPolicy()
        if isinstance(config.secure_headers_referrer, str):
            referrer.set(config.secure_headers_referrer)

    cache: Optional[secure.CacheControl] = None
    if config.secure_headers_cache:
        cache = secure.CacheControl()
        if isinstance(config.secure_headers_cache, str):
            cache.set(config.secure_headers_cache)

    permissions: Optional[secure.PermissionsPolicy] = None
    if config.secure_headers_permissions:
        permissions = secure.PermissionsPolicy()
        if isinstance(config.secure_headers_permissions, str):
            # This one is special, because it doesn't allow setting the
            # value as a string, but rather as a list of directives, so we
            # hack our way around it by setting the private _default_value
            # attribute.
            permissions._default_value = config.secure_headers_permissions

    _secure_headers = secure.Secure(
        server=server,
        hsts=hsts,
        xfo=xfo,
        csp=csp,
        xcto=xcto,
        referrer=referrer,
        cache=cache,
        permissions=permissions,
    )
