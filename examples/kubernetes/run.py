from pipelines.parallelizable_pipeline import parallelizable_pipeline
from steps import evaluator, importer, svc_trainer, skew_comparison

if __name__ == "__main__":
    parallelizable_pipeline(
        importer=importer(),
        trainer=svc_trainer(),
        evaluator=evaluator(),
        skew_comparison=skew_comparison()
    ).run()
