from typing import List

import tensorflow_model_analysis as tfma
from tensorflow_model_analysis import model_agnostic_eval as ma_eval
from tensorflow_model_analysis import types
from tensorflow_model_analysis.extractors import slice_key_extractor
from tensorflow_model_analysis.slicer import slicer_lib as slicer


def custom_extractors(eval_config,
                      eval_shared_model,
                      tensor_adapter_config
                      ) -> List[tfma.extractors.Extractor]:
    return [
        ma_eval.model_agnostic_extractor.ModelAgnosticExtractor(
            model_agnostic_config=eval_config, desired_batch_size=3),
        slice_key_extractor.SliceKeyExtractor([slicer.SingleSliceSpec()])]


def custom_eval_shared_model(eval_saved_model_path,
                             model_name,
                             eval_config,
                             **kwargs) -> tfma.EvalSharedModel:
    return types.EvalSharedModel(
        add_metrics_callbacks=list(),
        construct_fn=ma_eval.model_agnostic_evaluate_graph.make_construct_fn(
            add_metrics_callbacks=list(),
            config=eval_config))


