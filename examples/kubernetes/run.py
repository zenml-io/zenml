from pipelines.digits_pipeline import digits_pipeline
from steps import evaluator, importer, svc_trainer

if __name__ == "__main__":
    digits_pipeline(
        importer=importer(),
        trainer=svc_trainer(),
        evaluator=evaluator(),
    ).run()
