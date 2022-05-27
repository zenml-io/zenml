from zenml.integrations.kserve.services import (
    KServeDeploymentService,
    KServeDeploymentConfig,
)
from zenml.integrations.kserve.model_deployers import KServeModelDeployer


def main():

    model_deployer = KServeModelDeployer.get_active_model_deployer()
    model_deployer.deploy_model(
        config=KServeDeploymentConfig(
            model_uri="gs://kfserving-samples/models/tensorflow/flowers",
            model_name="flower",
            predictor="tensorflow",
            resources={"requests": {"cpu": "200m"}},
        ),
        replace=True,
    )


if __name__ == "__main__":
    main()
