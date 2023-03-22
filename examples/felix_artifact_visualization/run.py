from steps.drift_detection import drift_detector
from steps.image_loader import image_loader
from steps.image_to_df import image_to_df

from zenml.pipelines import pipeline


@pipeline
def artifact_visualization_pipeline(
    image_loader_1,
    image_loader_2,
    image_to_df_1,
    image_to_df_2,
    drift_detector,
):
    image1 = image_loader_1()
    image2 = image_loader_2()
    df1 = image_to_df_1(image1)
    df2 = image_to_df_2(image2)
    drift_detector(
        reference_dataset=df1,
        comparison_dataset=df2,
    )


def main():
    pip = artifact_visualization_pipeline(
        image_loader_1=image_loader(),
        image_loader_2=image_loader(name="image_loader_2"),
        image_to_df_1=image_to_df(),
        image_to_df_2=image_to_df(name="image_to_df_2"),
        drift_detector=drift_detector,
    )
    pip.configure(enable_cache=False)
    pip.run()


if __name__ == "__main__":
    main()
