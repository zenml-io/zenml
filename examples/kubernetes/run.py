from pipelines.parallelizable_pipeline import parallelizable_pipeline
from steps import evaluator, importer, skew_comparison, svc_trainer

if __name__ == "__main__":
    parallelizable_pipeline(
        importer=importer(),
        trainer=svc_trainer(),
        evaluator=evaluator(),
        skew_comparison=skew_comparison(),
    ).run()
