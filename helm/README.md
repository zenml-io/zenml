# ZenML Helm Chart

![ZenML Logo](https://raw.githubusercontent.com/zenml-io/zenml/main/docs/book/.gitbook/assets/zenml_logo.png)

## Overview

ZenML is an open-source MLOps framework designed to help you create robust, maintainable, and production-ready machine learning pipelines.

## Features

- Easy deployment of ZenML server on Kubernetes.
- Various authentication schemes including OAuth2 and HTTP Basic.
- Highly configurable via Helm values.
- Supports multiple secrets store backends like AWS Secrets Manager, GCP Secrets Manager, and Azure Key Vault.

## Quickstart

### Install the Chart

To install the ZenML chart directly from Amazon ECR, use the following command:

```bash
# example command for version 0.80.0
helm install my-zenml oci://public.ecr.aws/zenml/zenml --version 0.80.0
```

Note: Ensure you have OCI support enabled in your Helm client and that you are authenticated with Amazon ECR.

## Configuration

This chart offers a multitude of configuration options. For detailed
information, check the default [`values.yaml`](values.yaml) file. For full
details of the configuration options, refer to the [ZenML documentation](https://docs.zenml.io/getting-started/deploying-zenml/deploy-with-helm).

### Custom CA Certificates

If you need to connect to services using HTTPS with certificates signed by custom Certificate Authorities (e.g., self-signed certificates), you can configure custom CA certificates. There are two ways to provide custom CA certificates:

1. Direct injection in values.yaml:
```yaml
zenml:
  certificates:
    customCAs:
      - name: "my-custom-ca"
        certificate: |
          -----BEGIN CERTIFICATE-----
          MIIDXTCCAkWgAwIBAgIJAJC1HiIAZAiIMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNV
          ...
          -----END CERTIFICATE-----
```

2. Reference existing Kubernetes secrets:
```yaml
zenml:
  certificates:
    secretRefs:
      - name: "my-secret"
        key: "ca.crt"
```

The certificates will be installed in the server container, allowing it to securely connect to services using these custom CA certificates.

### HTTP Proxy Configuration

If your environment requires a proxy for external connections, you can configure it using:

```yaml
zenml:
  proxy:
    enabled: true
    httpProxy: "http://proxy.example.com:8080"
    httpsProxy: "http://proxy.example.com:8080"
    # Additional hostnames/domains/IPs/CIDRs to exclude from proxying
    additionalNoProxy:
      - "internal.example.com"
      - "10.0.0.0/8"
```

By default, the following hostnames/domains are excluded from proxying:
- `localhost`, `127.0.0.1`, `::1` (IPv4 and IPv6 localhost)
- `fe80::/10` (IPv6 link-local addresses)
- `.svc` and `.svc.cluster.local` (Kubernetes service DNS domains)
- The hostname from `zenml.serverURL` if configured
- The ingress hostname (`zenml.ingress.host`) if configured
- Internal service names used for communication between components

You can add additional exclusions using the `additionalNoProxy` list. The NO_PROXY environment variable accepts:
- Hostnames (e.g., "zenml.example.com")
- Domain names with leading dot for wildcards (e.g., ".example.com")
- IPv4 addresses (e.g., "10.0.0.1")
- IPv4 ranges in CIDR notation (e.g., "10.0.0.0/8")
- IPv6 addresses (e.g., "::1")
- IPv6 ranges in CIDR notation (e.g., "fe80::/10")

## Telemetry

The ZenML server collects anonymous usage data to help us improve the product. You can opt out by setting `zenml.analyticsOptIn` to false.

## Contributing

Feel free to [submit issues or pull requests](https://github.com/zenml-io/zenml) if you would like to improve the chart.

## License

[This project is licensed](https://github.com/zenml-io/zenml/blob/main/LICENSE) under the terms of the Apache-2.0 license.

## Further Reading

- [ZenML Documentation](https://docs.zenml.io)
- [ZenML Source Code](https://github.com/zenml-io/zenml)
