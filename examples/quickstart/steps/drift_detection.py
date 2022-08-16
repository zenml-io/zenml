from zenml.integrations.evidently.steps import (
    EvidentlyProfileConfig,
    evidently_profile_step,
)

evidently_profile_config = EvidentlyProfileConfig(
    profile_sections=["datadrift"]
)
drift_detector = evidently_profile_step(
    step_name="drift_detector", config=evidently_profile_config
)
