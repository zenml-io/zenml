import importlib.util

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
                     "tfx==0.25.0",
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
GCP_REQUIREMENTS = ["apache-beam[gcp]==2.26.0",
                    "apache-beam==2.26.0",
                    "google-apitools==0.5.31"]

AWS_INTEGRATION = 'aws'
AWS_REQUIREMENTS = []

AZURE_INTEGRATION = 'azure'
AZURE_REQUIREMENTS = []

###################
# EXTRAS: TOOLING #
###################
PYTORCH_INTEGRATION = 'pytorch'
PYTORCH_REQUIREMENTS = ['torch']

###############
# EXTRAS: ALL #
###############
ALL_INTEGRATION = 'all'
ALL_REQUIREMENTS = BASE_REQUIREMENTS + \
                   GCP_REQUIREMENTS + \
                   PYTORCH_REQUIREMENTS + \
                   AZURE_REQUIREMENTS + \
                   AWS_REQUIREMENTS

EXTRAS_REQUIRE = {GCP_INTEGRATION: GCP_REQUIREMENTS,
                  AWS_INTEGRATION: AWS_REQUIREMENTS,
                  # AZURE_INTEGRATION: AZURE_REQUIREMENTS,
                  PYTORCH_INTEGRATION: PYTORCH_REQUIREMENTS,
                  ALL_INTEGRATION: ALL_REQUIREMENTS}


##################
# UTIL FUNCTIONS #
##################
def check_integration(integration):
    # Get the required extra packages for the integration
    assert integration in EXTRAS_REQUIRE, \
        f'There is no integration for {integration}. Possible integration ' \
        f'for ZenML include: {list(EXTRAS_REQUIRE.keys())}.'

    specs = EXTRAS_REQUIRE[integration]

    for s in specs:
        # Decouple from the version
        s = s.split('==')[0]

        # Search for the extra package
        x = importlib.util.find_spec(s)
        # TODO: We can also validate the version
        if x is None:
            raise AssertionError(f"{integration} integration not installed. "
                                 f"Please install zenml[{integration}] via "
                                 f"`pip install zenml[{integration}]`")
