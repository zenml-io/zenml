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

These models provide type-safe access to Gateway API resources (Gateway,
HTTPRoute) without relying on error-prone dictionary `.get()` chains.

Gateway API is the newer Kubernetes standard for ingress/routing, replacing
Ingress with a more expressive and extensible model.

Reference: https://gateway-api.sigs.k8s.io/
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# HTTPRoute Models
# =============================================================================


class HTTPRoutePathMatch(BaseModel):
    """Path matching configuration for HTTPRoute rules.

    Attributes:
        type: Match type (Exact, PathPrefix, RegularExpression).
        value: The path value to match against.
    """

    model_config = ConfigDict(extra="ignore")

    type: str = "PathPrefix"
    value: str = "/"


class HTTPRouteMatch(BaseModel):
    """Match conditions for an HTTPRoute rule.

    Attributes:
        path: Path matching configuration.
        headers: Header matching conditions (not modeled in detail).
        queryParams: Query parameter matching (not modeled in detail).
    """

    model_config = ConfigDict(extra="ignore")

    path: Optional[HTTPRoutePathMatch] = None


class BackendRef(BaseModel):
    """Reference to a backend service for routing.

    Attributes:
        name: Name of the Kubernetes Service.
        namespace: Namespace of the Service (defaults to HTTPRoute's namespace).
        port: Port number on the Service.
        weight: Traffic weight for load balancing.
    """

    model_config = ConfigDict(extra="ignore")

    name: str
    namespace: Optional[str] = None
    port: Optional[int] = None
    weight: Optional[int] = None


class HTTPRouteRule(BaseModel):
    """A single routing rule in an HTTPRoute.

    Attributes:
        matches: Conditions that must be met for this rule to apply.
        backendRefs: Services to route matching requests to.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    matches: List[HTTPRouteMatch] = Field(default_factory=list)
    backend_refs: List[BackendRef] = Field(
        default_factory=list, alias="backendRefs"
    )


class ParentRef(BaseModel):
    """Reference to a parent Gateway resource.

    Attributes:
        name: Name of the Gateway.
        namespace: Namespace of the Gateway.
        sectionName: Specific listener on the Gateway to attach to.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: str
    namespace: Optional[str] = None
    section_name: Optional[str] = Field(default=None, alias="sectionName")


class HTTPRouteSpec(BaseModel):
    """Specification for an HTTPRoute resource.

    Attributes:
        hostnames: Hostnames this route applies to.
        parentRefs: Gateways this route is attached to.
        rules: Routing rules.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    hostnames: List[str] = Field(default_factory=list)
    parent_refs: List[ParentRef] = Field(
        default_factory=list, alias="parentRefs"
    )
    rules: List[HTTPRouteRule] = Field(default_factory=list)


class HTTPRoute(BaseModel):
    """Kubernetes Gateway API HTTPRoute resource.

    HTTPRoute defines HTTP routing rules that map to backend services.
    It's the Gateway API equivalent of path-based routing in Ingress.

    Attributes:
        spec: The HTTPRoute specification.
    """

    model_config = ConfigDict(extra="ignore")

    spec: HTTPRouteSpec = Field(default_factory=HTTPRouteSpec)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HTTPRoute":
        """Create HTTPRoute from a dictionary (e.g., from Kubernetes API).

        Args:
            data: Dictionary representation of the HTTPRoute.

        Returns:
            Parsed HTTPRoute model.
        """
        return cls.model_validate(data)


# =============================================================================
# Gateway Models
# =============================================================================


class GatewayListener(BaseModel):
    """A listener on a Gateway that accepts traffic.

    Attributes:
        name: Unique name of the listener within the Gateway.
        protocol: Protocol the listener accepts (HTTP, HTTPS, TLS, TCP, UDP).
        port: Port the listener binds to.
    """

    model_config = ConfigDict(extra="ignore")

    name: str
    protocol: str = "HTTP"
    port: Optional[int] = None


class GatewayStatus(BaseModel):
    """Status of a Gateway resource.

    Attributes:
        listeners: Status of each listener on the Gateway.
    """

    model_config = ConfigDict(extra="ignore")

    listeners: List[GatewayListener] = Field(default_factory=list)


class Gateway(BaseModel):
    """Kubernetes Gateway API Gateway resource.

    Gateway represents an instance of a load balancer or proxy that handles
    traffic for a set of HTTPRoutes.

    Attributes:
        status: Current status of the Gateway.
    """

    model_config = ConfigDict(extra="ignore")

    status: Optional[GatewayStatus] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Gateway":
        """Create Gateway from a dictionary (e.g., from Kubernetes API).

        Args:
            data: Dictionary representation of the Gateway.

        Returns:
            Parsed Gateway model.
        """
        return cls.model_validate(data)

