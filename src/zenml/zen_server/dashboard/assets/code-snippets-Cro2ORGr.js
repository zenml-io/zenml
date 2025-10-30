function e(t){return`from zenml.client import Client

artifact = Client().get_artifact_version("${t}")
data = artifact.load()`}function n(t){return`from zenml.client import Client

step = Client().get_run_step("${t}")
config = step.config`}function i(t){return`from zenml.client import Client

run = Client().get_pipeline_run("${t}")
config = run.config`}function r(t){return`from zenml.client import Client

secret = Client().get_secret("${t}")
`}export{e as a,n as b,r as c,i as g};
