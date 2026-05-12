---
description: Migrate ZenML Helm deployments from Ingress to Kubernetes Gateway API.
---

# Migrate to Gateway API

Gateway API is the Kubernetes networking successor to the legacy Ingress model. If you currently expose ZenML through `server.ingress`, this guide shows how to migrate to `server.gateway` with minimal downtime.

## Why migrate

- Gateway API is the long-term Kubernetes direction for north-south traffic.
- It provides clearer separation between shared infrastructure ownership (`Gateway`) and app routing ownership (`HTTPRoute`).
- It maps well to multi-tenant environments where platform teams manage shared gateways and application teams manage routes.

## Prerequisites

- Kubernetes 1.26+
- A Gateway API implementation with `v1` CRDs available (for example, `gateway.networking.k8s.io/v1` for `Gateway` and `HTTPRoute`; Envoy Gateway, Istio, NGINX Gateway Fabric, GKE Gateway)
- A `Gateway` resource already provisioned and reachable using the installed Gateway API `v1` CRDs
- DNS access for cutover planning

> ZenML renders `HTTPRoute` resources with `apiVersion: gateway.networking.k8s.io/v1`. Clusters that only have older Gateway API CRDs installed (for example, `v1beta1`) must upgrade those CRDs before enabling `server.gateway`.

## Migration overview

1. Install or verify your Gateway API implementation.
2. Create a shared `Gateway` (platform-managed).
3. Enable `server.gateway` in ZenML Helm values (alongside existing `server.ingress` for zero-downtime migration).
4. Deploy and verify `HTTPRoute` status and application health.
5. Perform DNS cutover (if using a new load balancer).
6. Disable `server.ingress` after stabilization.

## Helm values migration

### Step 1: Enable both (parallel period)

Both `server.ingress.enabled` and `server.gateway.enabled` can be `true` simultaneously. The chart renders both an Ingress and an HTTPRoute. Kubernetes controllers only act on resources they own — an ingress controller ignores HTTPRoutes and a Gateway controller ignores Ingresses — so enabling both creates no conflict.

```yaml
server:
  ingress:
    enabled: true              # keep Ingress active during migration
    host: zenml.example.com
  gateway:
    enabled: true              # also create HTTPRoute
    gatewayRef:
      name: zenml-gateway
      namespace: gateway-infra
    sectionName: https-backend
    host: zenml.example.com
    path: /
```

At this point, traffic still flows through the ingress controller (DNS points to its load balancer). The HTTPRoute is ready on the Gateway side but idle.

### Step 2: DNS cutover

Update DNS to point to the Gateway's load balancer. Both the Ingress and HTTPRoute exist, so the transition is seamless — the ingress controller handles traffic until DNS propagates, then the Gateway takes over.

### Step 3: Disable Ingress (cleanup)

After DNS is stable and traffic is flowing through the Gateway, disable Ingress:

```yaml
server:
  ingress:
    enabled: false
  gateway:
    enabled: true
    gatewayRef:
      name: zenml-gateway
      namespace: gateway-infra
    sectionName: https-backend
    host: zenml.example.com
    path: /
```

## Gateway implementation examples

### Envoy Gateway

Use a shared `GatewayClass` and `Gateway`, then attach ZenML `HTTPRoute` resources via `parentRefs`.

### Istio

Use Istio's Gateway API support (managed Gateway + HTTPRoute) and keep ZenML route ownership in tenant namespaces.

### NGINX Gateway Fabric

Deploy NGINX Gateway Fabric and configure a shared `Gateway` listener; point ZenML `gatewayRef` to that shared gateway.

### GKE Gateway

Create a GKE-managed `Gateway` and map your external DNS hostnames to the provisioned load balancer.

## Custom annotations

You can add custom annotations to the `HTTPRoute` resource:

```yaml
server:
  gateway:
    enabled: true
    annotations:
      my-annotation: my-value
    gatewayRef:
      name: zenml-gateway
      namespace: gateway-infra
```

This is useful for attaching Envoy-specific policies, adding metadata for service mesh integration, or custom routing labels.

## TLS options

You can terminate TLS in one of two common ways:

- **Gateway-managed TLS** (e.g. cert-manager certificate references in gateway listeners)
- **Cloud load balancer TLS termination** (e.g. ACM on AWS NLB) with HTTP forwarded to Gateway listeners

Choose the model that matches your platform standards. ZenML only needs the correct external hostname and reachable `Gateway` listener.

## Validation checklist

- `kubectl get gateway -A` shows the target gateway as accepted/programmed
- `kubectl get httproute -A` shows ZenML routes attached/accepted
- `curl https://<zenml-host>/health` returns success
- Optional: test large uploads and UI/API login flows

## DNS cutover

If migration introduces a new load balancer:

1. Lower DNS TTL (for example 60s) before cutover.
2. Update CNAME/A records to the new load balancer.
3. Monitor health, latency, and error rate.
4. Restore normal TTL after stabilization.

## Rollback

Since both Ingress and Gateway can be enabled simultaneously, rollback during the parallel period is simply a DNS change — point DNS back to the ingress controller's load balancer. No Helm changes needed.

If you've already disabled Ingress (Step 3), re-enable it:

```yaml
server:
  ingress:
    enabled: true
    host: zenml.example.com
  gateway:
    enabled: false
```

Re-deploy, repoint DNS to the ingress controller's load balancer, and verify `/health` and login.

Keep both infrastructure paths available during stabilization to ensure a low-risk rollback.
