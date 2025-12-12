#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Pydantic models for Kubernetes Gateway API resources.

This module provides type-safe models for Gateway API resources (Gateway and
HTTPRoute) to replace untyped Dict[str, Any] access patterns with validated
attribute access.

Gateway API is the newer Kubernetes standard for ingress/routing, using:
- Gateway: Entry point with listeners (replaces LoadBalancer/NodePort exposure)
- HTTPRoute: Routing rules that attach to Gateways (replaces Ingress)

Note:
    The Kubernetes Python client library does not include typed models for
    Gateway API resources because Gateway API is a CRD-based extension, not
    part of core Kubernetes. These models provide the type safety needed for
    the fields we use in URL building.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class HTTPPathMatch(BaseModel):
    """Path match configuration for HTTPRoute.

    Attributes:
        value: Path value to match (e.g., "/api/v1").
        type: Match type - "Exact", "PathPrefix", or "RegularExpression".
    """

    value: str = "/"
    type: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class HTTPRouteMatch(BaseModel):
    """Match criteria for HTTPRoute rule.

    Attributes:
        path: Optional path match configuration.
    """

    path: Optional[HTTPPathMatch] = None

    model_config = ConfigDict(populate_by_name=True)


class BackendRef(BaseModel):
    """Backend reference in HTTPRoute rule.

    Attributes:
        name: Name of the backend service.
        namespace: Namespace of the backend service.
        port: Port number on the backend service.
        weight: Traffic weight for load balancing.
    """

    name: str
    namespace: Optional[str] = None
    port: Optional[int] = None
    weight: Optional[int] = None

    model_config = ConfigDict(populate_by_name=True)


class HTTPRouteRule(BaseModel):
    """Routing rule in HTTPRoute.

    Attributes:
        matches: List of match conditions for this rule.
        backend_refs: List of backend services to route traffic to.
    """

    matches: List[HTTPRouteMatch] = Field(default_factory=list)
    backend_refs: List[BackendRef] = Field(
        default_factory=list, alias="backendRefs"
    )

    model_config = ConfigDict(populate_by_name=True)


class ParentReference(BaseModel):
    """Reference to parent Gateway.

    Attributes:
        name: Name of the parent Gateway.
        namespace: Namespace of the parent Gateway.
        section_name: Name of specific Gateway listener to attach to.
    """

    name: str
    namespace: Optional[str] = None
    section_name: Optional[str] = Field(None, alias="sectionName")

    model_config = ConfigDict(populate_by_name=True)


class HTTPRouteSpec(BaseModel):
    """HTTPRoute specification.

    Attributes:
        hostnames: List of hostnames this route matches.
        parent_refs: List of parent Gateways this route attaches to.
        rules: List of routing rules with match conditions and backends.
    """

    hostnames: List[str] = Field(default_factory=list)
    parent_refs: List[ParentReference] = Field(
        default_factory=list, alias="parentRefs"
    )
    rules: List[HTTPRouteRule] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


# Gateway Models


class GatewayListener(BaseModel):
    """Gateway listener configuration.

    Attributes:
        name: Unique name for this listener.
        protocol: Protocol - "HTTP", "HTTPS", "TLS", "TCP", or "UDP".
        port: Port number the listener binds to.
        hostname: Hostname the listener accepts.
    """

    name: str
    protocol: str
    port: Optional[int] = None
    hostname: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class GatewayStatus(BaseModel):
    """Gateway status information.

    Attributes:
        listeners: List of listener configurations and their status.
        addresses: List of addresses where the Gateway is accessible.
    """

    listeners: List[GatewayListener] = Field(default_factory=list)
    addresses: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)
