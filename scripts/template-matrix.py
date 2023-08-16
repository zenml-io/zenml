import json
import os
import sys

from zenml.cli.base import ZENML_PROJECT_TEMPLATES

if sys.argv[1] == "generate":
    print(
        json.dumps(
            [
                (
                    template,
                    ZENML_PROJECT_TEMPLATES[template].github_url,
                    ZENML_PROJECT_TEMPLATES[template].github_tag,
                )
                for template in ZENML_PROJECT_TEMPLATES
            ]
        )
    )
if sys.argv[1] == "parse":
    env_file = os.getenv("GITHUB_ENV")
    data = json.loads(sys.argv[2])

    with open(env_file, "a") as myfile:
        myfile.write(f"ZENML_PROJECT_TEMPLATE={data[0]}")
        myfile.write(f"ZENML_PROJECT_GITHUB_URL={data[1]}")
        myfile.write(f"ZENML_PROJECT_GITHUB_TAG={data[2]}")
