---
description: >-
  To help you figure out what you can put in your configuration file, simply
  autogenerate a template.
---

# Autogenerate a template yaml file

If you want to generate a template yaml file of your specific pipeline, you can do so by using the `.write_run_configuration_template()` method. This will generate a yaml file with all options commented out. This way you can pick and choose the settings that are relevant to you.

```python
from zenml import pipeline
...

@pipeline(enable_cache=True) # set cache behavior at step level
def simple_ml_pipeline(parameter: int):
    dataset = load_data(parameter=parameter)
    train_model(dataset)

simple_ml_pipeline.write_run_configuration_template(path="<Insert_path_here>")
```

<details>

<summary>An example of a generated YAML configuration template</summary>

```yaml
build: Union[PipelineBuildBase, UUID, NoneType]
enable_artifact_metadata: Optional[bool]
enable_artifact_visualization: Optional[bool]
enable_cache: Optional[bool]
enable_step_logs: Optional[bool]
extra: Mapping[str, Any]
model:
  audience: Optional[str]
  description: Optional[str]
  ethics: Optional[str]
  license: Optional[str]
  limitations: Optional[str]
  name: str
  save_models_to_registry: bool
  suppress_class_validation_warnings: bool
  tags: Optional[List[str]]
  trade_offs: Optional[str]
  use_cases: Optional[str]
  version: Union[ModelStages, int, str, NoneType]
parameters: Optional[Mapping[str, Any]]
run_name: Optional[str]
schedule:
  catchup: bool
  cron_expression: Optional[str]
  end_time: Optional[datetime]
  interval_second: Optional[timedelta]
  name: Optional[str]
  run_once_start_time: Optional[datetime]
  start_time: Optional[datetime]
settings:
  docker:
    apt_packages: List[str]
    build_context_root: Optional[str]
    build_options: Mapping[str, Any]
    copy_files: bool
    copy_global_config: bool
    dockerfile: Optional[str]
    dockerignore: Optional[str]
    environment: Mapping[str, Any]
    install_stack_requirements: bool
    parent_image: Optional[str]
    python_package_installer: PythonPackageInstaller
    replicate_local_python_environment: Union[List[str], PythonEnvironmentExportMethod,
     NoneType]
    required_integrations: List[str]
    requirements: Union[NoneType, str, List[str]]
    skip_build: bool
    prevent_build_reuse: bool
    allow_including_files_in_images: bool
    allow_download_from_code_repository: bool
    allow_download_from_artifact_store: bool
    target_repository: str
    user: Optional[str]
  resources:
    cpu_count: Optional[PositiveFloat]
    gpu_count: Optional[NonNegativeInt]
    memory: Optional[ConstrainedStrValue]
steps:
  load_data:
    enable_artifact_metadata: Optional[bool]
    enable_artifact_visualization: Optional[bool]
    enable_cache: Optional[bool]
    enable_step_logs: Optional[bool]
    experiment_tracker: Optional[str]
    extra: Mapping[str, Any]
    failure_hook_source:
      attribute: Optional[str]
      module: str
      type: SourceType
    model:
      audience: Optional[str]
      description: Optional[str]
      ethics: Optional[str]
      license: Optional[str]
      limitations: Optional[str]
      name: str
      save_models_to_registry: bool
      suppress_class_validation_warnings: bool
      tags: Optional[List[str]]
      trade_offs: Optional[str]
      use_cases: Optional[str]
      version: Union[ModelStages, int, str, NoneType]
    name: Optional[str]
    outputs:
      output:
        default_materializer_source:
          attribute: Optional[str]
          module: str
          type: SourceType
      materializer_source: Optional[Tuple[Source, ...]]
    parameters: {}
    settings:
      docker:
        apt_packages: List[str]
        build_context_root: Optional[str]
        build_options: Mapping[str, Any]
        copy_files: bool
        copy_global_config: bool
        dockerfile: Optional[str]
        dockerignore: Optional[str]
        environment: Mapping[str, Any]
        install_stack_requirements: bool
        parent_image: Optional[str]
        python_package_installer: PythonPackageInstaller
        replicate_local_python_environment: Union[List[str], PythonEnvironmentExportMethod,
         NoneType]
        required_integrations: List[str]
        requirements: Union[NoneType, str, List[str]]
        skip_build: bool
        prevent_build_reuse: bool
        allow_including_files_in_images: bool
        allow_download_from_code_repository: bool
        allow_download_from_artifact_store: bool
        target_repository: str
        user: Optional[str]
      resources:
        cpu_count: Optional[PositiveFloat]
        gpu_count: Optional[NonNegativeInt]
        memory: Optional[ConstrainedStrValue]
    step_operator: Optional[str]
    success_hook_source:
      attribute: Optional[str]
      module: str
      type: SourceType
  train_model:
    enable_artifact_metadata: Optional[bool]
    enable_artifact_visualization: Optional[bool]
    enable_cache: Optional[bool]
    enable_step_logs: Optional[bool]
    experiment_tracker: Optional[str]
    extra: Mapping[str, Any]
    failure_hook_source:
      attribute: Optional[str]
      module: str
      type: SourceType
    model:
      audience: Optional[str]
      description: Optional[str]
      ethics: Optional[str]
      license: Optional[str]
      limitations: Optional[str]
      name: str
      save_models_to_registry: bool
      suppress_class_validation_warnings: bool
      tags: Optional[List[str]]
      trade_offs: Optional[str]
      use_cases: Optional[str]
      version: Union[ModelStages, int, str, NoneType]
    name: Optional[str]
    outputs: {}
    parameters: {}
    settings:
      docker:
        apt_packages: List[str]
        build_context_root: Optional[str]
        build_options: Mapping[str, Any]
        copy_files: bool
        copy_global_config: bool
        dockerfile: Optional[str]
        dockerignore: Optional[str]
        environment: Mapping[str, Any]
        install_stack_requirements: bool
        parent_image: Optional[str]
        python_package_installer: PythonPackageInstaller
        replicate_local_python_environment: Union[List[str], PythonEnvironmentExportMethod,
         NoneType]
        required_integrations: List[str]
        requirements: Union[NoneType, str, List[str]]
        skip_build: bool
        prevent_build_reuse: bool
        allow_including_files_in_images: bool
        allow_download_from_code_repository: bool
        allow_download_from_artifact_store: bool
        target_repository: str
        user: Optional[str]
      resources:
        cpu_count: Optional[PositiveFloat]
        gpu_count: Optional[NonNegativeInt]
        memory: Optional[ConstrainedStrValue]
    step_operator: Optional[str]
    success_hook_source:
      attribute: Optional[str]
      module: str
      type: SourceType

```

</details>

{% hint style="info" %}
When you want to configure your pipeline with a certain stack in mind, you can do so as well: \`...write\_run\_configuration\_template(stack=\<Insert\_stack\_here>)
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
