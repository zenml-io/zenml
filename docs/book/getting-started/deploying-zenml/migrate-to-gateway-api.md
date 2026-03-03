---
description: Migrate ZenML Helm deployments from Ingress to Kubernetes Gateway API.
---

# Migrate to Gateway API

Gateway API is the Kubernetes networking successor to the legacy Ingress model. If you currently expose ZenML through `zenml.ingress`, this guide shows how to migrate to `zenml.gateway` with minimal downtime.

## Why migrate

- Gateway API is the long-term Kubernetes direction for north-south traffic.
- It provides clearer separation between shared infrastructure ownership (`Gateway`) and app routing ownership (`HTTPRoute`).
- It maps well to multi-tenant environments where platform teams manage shared gateways and application teams manage routes.

## Prerequisites

- Kubernetes 1.26+
- A Gateway API implementation installed in the cluster (Envoy Gateway, Istio, NGINX Gateway Fabric, GKE Gateway)
- A `Gateway` resource already provisioned and reachable
- DNS access for cutover planning

## Migration overview

1. Install or verify your Gateway API implementation.
2. Create a shared `Gateway` (platform-managed).
3. Update ZenML Helm values from `ingress` to `gateway`.
4. Deploy and verify `HTTPRoute` status and application health.
5. Perform DNS cutover (if using a new load balancer).
6. Keep rollback path available until stabilization completes.

## Helm values migration

### Before (Ingress)

```yaml
zenml:
  ingress:
    enabled: true
    host: zenml.example.com
```

### After (Gateway API)

```yaml
zenml:
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

> `ingress.enabled` and `gateway.enabled` are mutually exclusive. Helm rendering fails if both are `true`.

## Gateway implementation examples

### Envoy Gateway

Use a shared `GatewayClass` and `Gateway`, then attach ZenML `HTTPRoute` resources via `parentRefs`.

### Istio

Use Istio's Gateway API support (managed Gateway + HTTPRoute) and keep ZenML route ownership in tenant namespaces.

### NGINX Gateway Fabric

Deploy NGINX Gateway Fabric and configure a shared `Gateway` listener; point ZenML `gatewayRef` to that shared gateway.

### GKE Gateway

Create a GKE-managed `Gateway` and map your external DNS hostnames to the provisioned load balancer.

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

1. Repoint DNS to the previous load balancer.
2. Set Helm values back to ingress mode:

```yaml
zenml:
  ingress:
    enabled: true
    host: zenml.example.com
  gateway:
    enabled: false
```

3. Re-deploy and verify `/health` and login.

Keep both infrastructure paths available during stabilization to ensure a low-risk rollback.
