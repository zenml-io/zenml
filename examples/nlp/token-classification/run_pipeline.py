from pipeline import (
    train_eval_pipeline, 
    data_importer, 
    DatasetMaterializer,
    tokenization,
    trainer, 
    HFModelMaterializer,
    evaluator,
    TokenClassificationConfig)

train_eval_pipeline(importer=data_importer().with_return_materializers(DatasetMaterializer),
                       tokenizer=tokenization().with_return_materializers(DatasetMaterializer),
               trainer=trainer(TokenClassificationConfig(num_train_epochs=1)).with_return_materializers(HFModelMaterializer),
               evaluator=evaluator()).run()