import json

from google.cloud import aiplatform

PROJECT_ID = "your-project-id"  # <---CHANGE THIS
REGION = "your-region"  # <---CHANGE THIS
PIPELINE_ROOT = "your-cloud-storage-pipeline-root"  # <---CHANGE THIS


def trigger_vertex_job(request):
    """Processes the incoming HTTP request.

    Args:
      request (flask.Request): HTTP request object.

    Returns:
      The response text or any set of values that can be turned into a Response
      object using `make_response
      <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """

    # decode http request payload and translate into JSON object
    request_str = request.data.decode("utf-8")
    request_json = json.loads(request_str)

    pipeline_spec_uri = request_json["pipeline_spec_uri"]
    parameter_values = request_json["parameter_values"]

    aiplatform.init(
        project=PROJECT_ID,
        location=REGION,
    )

    job = aiplatform.PipelineJob(
        display_name=f"hello-world-cloud-function-pipeline",
        template_path=pipeline_spec_uri,
        pipeline_root=PIPELINE_ROOT,
        enable_caching=False,
        parameter_values=parameter_values,
    )
    run = aiplatform.PipelineJob(
        display_name=pipeline_name,
        template_path=pipeline_file_path,
        job_id=job_id,
        pipeline_root=self._pipeline_root,
        parameter_values=None,
        enable_caching=False,
        encryption_spec_key_name=self.config.encryption_spec_key_name,
        labels=settings.labels,
        credentials=credentials,
        project=self.config.project,
        location=self.config.location,
    )
    run.submit()
    job.submit()
    return "Job submitted"
