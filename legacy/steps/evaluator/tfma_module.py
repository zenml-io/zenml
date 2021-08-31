from typing import Dict, Optional, Text, List

import apache_beam as beam
import tensorflow_model_analysis as tfma
from tensorflow_model_analysis import config
from tensorflow_model_analysis import constants
from tensorflow_model_analysis import model_util
from tensorflow_model_analysis import types
from tensorflow_model_analysis.extractors import extractor
from tfx_bsl.tfxio import tensor_adapter

BATCHED_PREDICT_EXTRACTOR_STAGE_NAME = 'ExtractBatchPredictions'


def custom_extractors(eval_config,
                      eval_shared_model,
                      tensor_adapter_config
                      ) -> List[tfma.extractors.Extractor]:
    return tfma.default_extractors(
        eval_config=eval_config,
        eval_shared_model=eval_shared_model,
        tensor_adapter_config=tensor_adapter_config,
        custom_predict_extractor=BatchedPredictExtractor(eval_config,
                                                         eval_shared_model,
                                                         tensor_adapter_config
                                                         ))


def BatchedPredictExtractor(
        eval_config: config.EvalConfig,
        eval_shared_model: types.MaybeMultipleEvalSharedModels,
        tensor_adapter_config: Optional[
            tensor_adapter.TensorAdapterConfig] = None,
) -> extractor.Extractor:
    eval_shared_models = model_util.verify_and_update_eval_shared_models(
        eval_shared_model)

    return extractor.Extractor(
        stage_name=BATCHED_PREDICT_EXTRACTOR_STAGE_NAME,
        ptransform=_ExtractBatchedPredictions(
            eval_config=eval_config,
            eval_shared_models={m.model_name: m for m in eval_shared_models},
            tensor_adapter_config=tensor_adapter_config))


@beam.ptransform_fn
@beam.typehints.with_input_types(types.Extracts)
@beam.typehints.with_output_types(types.Extracts)
def _ExtractBatchedPredictions(
        extracts: beam.pvalue.PCollection,
        eval_config: config.EvalConfig,
        eval_shared_models: Dict[Text, types.EvalSharedModel],
        tensor_adapter_config: Optional[
            tensor_adapter.TensorAdapterConfig] = None,
) -> beam.pvalue.PCollection:
    signature_names = {}
    for spec in eval_config.model_specs:
        model_name = '' if len(eval_config.model_specs) == 1 else spec.name
        signature_names[model_name] = [spec.signature_name]

    return (extracts
            | 'Predict' >> beam.ParDo(
                model_util.ModelSignaturesDoFn(
                    eval_config=eval_config,
                    eval_shared_models=eval_shared_models,
                    signature_names={
                        constants.PREDICTIONS_KEY: signature_names},
                    prefer_dict_outputs=True,
                    tensor_adapter_config=tensor_adapter_config)))
