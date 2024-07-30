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
# example command for version 0.63.0
helm install my-zenml oci://public.ecr.aws/zenml/zenml --version 0.63.0
```

Note: Ensure you have OCI support enabled in your Helm client and that you are authenticated with Amazon ECR.

## Configuration

This chart offers a multitude of configuration options. For detailed
information, check the default [`values.yaml`](values.yaml) file. For full
details of the configuration options, refer to the [ZenML documentation](https://docs.zenml.io/getting-started/deploying-zenml/deploy-with-helm).

## Telemetry

The ZenML server collects anonymous usage data to help us improve the product. You can opt out by setting `zenml.analyticsOptIn` to false.

## Contributing

Feel free to [submit issues or pull requests](https://github.com/zenml-io/zenml) if you would like to improve the chart.

## License

[This project is licensed](https://github.com/zenml-io/zenml/blob/main/LICENSE) under the terms of the Apache-2.0 license.

## Further Reading

- [ZenML Documentation](https://docs.zenml.io)
- [ZenML Source Code](https://github.com/zenml-io/zenml)
