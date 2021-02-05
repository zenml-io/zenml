import re

import subprocess
import sys

########
# BASE #
########
BASE_REQUIREMENTS = ["absl-py==0.10.0",
                     "pip-check-reqs>=2.0.1,<3",
                     "click>=7.0,<8",
                     "setuptools>=38.4.0",
                     "nbformat>=5.0.4",
                     "panel==0.8.3",
                     "plotly==4.0.0",
                     "tabulate==0.8.7",
                     "numpy==1.18.0",
                     "httplib2==0.17.0",
                     "tfx==0.26.1",
                     "fire==0.3.1",
                     "gitpython==3.1.11",
                     "analytics-python==1.2.9",
                     "distro==1.5.0",
                     "tensorflow>=2.3.0,<2.4.0",
                     "tensorflow-serving-api==2.3.0"]

#####################
# EXTRAS: PROVIDERS #
#####################
GCP_INTEGRATION = 'gcp'
GCP_REQUIREMENTS = ["apache-beam[gcp]==2.27.0",
                    "apache-beam==2.27.0",
                    "google-apitools==0.5.31"]

AWS_INTEGRATION = 'aws'
AWS_REQUIREMENTS = []

AZURE_INTEGRATION = 'azure'
AZURE_REQUIREMENTS = []

###################
# EXTRAS: TOOLING #
###################
PYTORCH_INTEGRATION = 'pytorch'
PYTORCH_REQUIREMENTS = ['torch==1.7.0']

# CORTEX_INTEGRATION = 'cortex'
# CORTEX_REQUIREMENTS = ['cortex==0.27.0']
###############
# EXTRAS: ALL #
###############
ALL_INTEGRATION = 'all'
ALL_REQUIREMENTS = BASE_REQUIREMENTS + \
                   GCP_REQUIREMENTS + \
                   PYTORCH_REQUIREMENTS + \
                   AZURE_REQUIREMENTS + \
                   AWS_REQUIREMENTS
                   # CORTEX_REQUIREMENTS

EXTRAS_REQUIRE = {GCP_INTEGRATION: GCP_REQUIREMENTS,
                  AWS_INTEGRATION: AWS_REQUIREMENTS,
                  # AZURE_INTEGRATION: AZURE_REQUIREMENTS,
                  PYTORCH_INTEGRATION: PYTORCH_REQUIREMENTS,
                  # CORTEX_INTEGRATION: CORTEX_REQUIREMENTS,
                  ALL_INTEGRATION: ALL_REQUIREMENTS}


##################
# UTIL FUNCTIONS #
##################
def check_integration(integration):
    # Get the installed packages
    reqs = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])
    installed_packages = [r.decode().split('==')[0] for r in reqs.split()]

    # Get the required extra packages for the integration
    assert integration in EXTRAS_REQUIRE, \
        f'At this moment, there is no integration for {integration}. ' \
        f'Possible integrations for ZenML ' \
        f'include: {list(EXTRAS_REQUIRE.keys())}.'

    specs = EXTRAS_REQUIRE[integration]

    for s in specs:
        # Decouple from the version
        pattern = r"([a-zA-Z0-9\-]+)(\[.+\])*(.*)"
        s = re.search(pattern, s)[1]

        # TODO: We can also validate the version
        if s not in installed_packages:
            raise AssertionError(f"{integration} integration not installed. "
                                 f"Please install zenml[{integration}] via "
                                 f"`pip install zenml[{integration}]`")
