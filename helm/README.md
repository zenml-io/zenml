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
# example command for version 0.95.1
helm install my-zenml oci://public.ecr.aws/zenml/zenml --version 0.95.1
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
server:
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
server:
  certificates:
    secretRefs:
      - name: "my-secret"
        key: "ca.crt"
```

The certificates will be installed in the server container, allowing it to securely connect to services using these custom CA certificates.

### HTTP Proxy Configuration

If your environment requires a proxy for external connections, you can configure it using:

```yaml
server:
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
- The hostname from `server.serverURL` if configured
- The ingress hostname (`server.ingress.host`) if configured
- Internal service names used for communication between components

You can add additional exclusions using the `additionalNoProxy` list. The NO_PROXY environment variable accepts:
- Hostnames (e.g., "zenml.example.com")
- Domain names with leading dot for wildcards (e.g., ".example.com")
- IPv4 addresses (e.g., "10.0.0.1")
- IPv4 ranges in CIDR notation (e.g., "10.0.0.0/8")
- IPv6 addresses (e.g., "::1")
- IPv6 ranges in CIDR notation (e.g., "fe80::/10")

### Database Persistence

When using database persistence with a local SQLite database, the chart automatically configures the necessary permissions. The `podSecurityContext.fsGroup` is set to 1000 by default to ensure the ZenML container (running as UID 1000) can write to the persistent volume.

Example configuration:

```yaml
server:
  database:
    persistence:
      enabled: true
      size: "10Gi"
      # storageClassName: ""  # Optional: use default storage class if not specified

# podSecurityContext.fsGroup is set to 1000 by default
# This ensures the container can write to the persistent volume
```

If you override `podSecurityContext`, ensure that `fsGroup: 1000` is set when using persistent volumes, otherwise the container will not be able to write to the mounted volume and will crash.

### Server Observability

You can configure server log output and OpenTelemetry export through
`server.environment`:

```yaml
server:
  environment:
    ZENML_CONSOLE_LOGGING_FORMAT: "<console|json>" # default is console
    ZENML_LOGGING_COLORS_DISABLED: "<true|false>" # default is false
    ZENML_SERVER_OTEL_EXPORTER_OTLP_ENDPOINT: "http://otel-collector:4318"
    ZENML_SERVER_OTEL_SERVICE_NAME: "zenml-server" # default is zenml-server
    ZENML_SERVER_OTEL_TRACES_ENABLED: "<true|false>" # default is true
    ZENML_SERVER_OTEL_METRICS_ENABLED: "<true|false>" # default is true
    ZENML_SERVER_OTEL_LOGS_ENABLED: "<true|false>" # default is true
```

`ZENML_CONSOLE_LOGGING_FORMAT` controls the server container stdout/stderr output. It can be set to `console`, `json`, or a valid Python `%`-style logging format string. The older `ZENML_LOGGING_FORMAT` environment variable is still supported as a deprecated alias but will be removed in a future version.

OpenTelemetry export is configured separately with `ZENML_SERVER_OTEL_EXPORTER_OTLP_ENDPOINT` and exports traces, metrics, and logs using OTLP/HTTP transport. Each signal is enabled by default and can be disabled individually with `ZENML_SERVER_OTEL_TRACES_ENABLED`, `ZENML_SERVER_OTEL_METRICS_ENABLED`, and `ZENML_SERVER_OTEL_LOGS_ENABLED`.

The standard `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable is also supported as a fallback.

Standard per-signal OTLP/HTTP endpoint variables such as `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`, `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`, and `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT` are supported too, along with matching `ZENML_SERVER_OTEL_EXPORTER_OTLP_<SIGNAL>_ENDPOINT` names.

Standard OTLP headers, timeout, and compression variables are handled by the OpenTelemetry Python exporters. OTLP/gRPC protocol variables are not supported because the server configures OTLP/HTTP exporters directly. You can read more about the OpenTelemetry environment variables and SDK configuration [here](https://opentelemetry.io/docs/languages/sdk-configuration/).

## Backwards Compatibility

The top-level `zenml:` values key has been renamed to `server:`. Existing
values files using `zenml:` continue to work — the chart deep-merges both
keys. We recommend using only one key; if both are provided, `zenml:` values
take precedence for overlapping keys. The `zenml:` key is deprecated and will
be removed in a future release.

## Telemetry

The ZenML server collects anonymous usage data to help us improve the product. You can opt out by setting `server.analyticsOptIn` to false.

## Contributing

Feel free to [submit issues or pull requests](https://github.com/zenml-io/zenml) if you would like to improve the chart.

## License

[This project is licensed](https://github.com/zenml-io/zenml/blob/main/LICENSE) under the terms of the Apache-2.0 license.

## Further Reading

- [ZenML Documentation](https://docs.zenml.io)
- [ZenML Source Code](https://github.com/zenml-io/zenml)
