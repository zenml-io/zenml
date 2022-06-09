"""Spin up a MySQL database in a Kubernetes pod."""

import argparse

from zenml.integrations.kubernetes.orchestrators.kube_utils import (
    create_mysql_deployment,
    create_namespace,
    make_core_v1_api,
)


def parse_args() -> argparse.Namespace:
    """Parse arguments.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--deployment_name", type=str, required=False, default="mysql"
    )
    parser.add_argument(
        "--namespace", type=str, required=False, default="default"
    )
    parser.add_argument(
        "--storage_capacity", type=str, required=False, default="10Gi"
    )
    return parser.parse_args()


def main() -> None:
    """Spin up a MySQL database in a Kubernetes pod."""
    args = parse_args()
    core_api = make_core_v1_api()
    create_namespace(core_api=core_api, namespace=args.namespace)
    create_mysql_deployment(
        core_api=core_api,
        namespace=args.namespace,
        storage_capacity=args.storage_capacity,
        deployment_name=args.deployment_name,
        service_name=args.deployment_name,
    )


if __name__ == "__main__":
    main()
