#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from typing import List, Text

import numpy as np
import tensorflow as tf
import tensorflow_transform as tft
from joblib import dump
from sklearn import svm
from sklearn.metrics import classification_report, confusion_matrix

from zenml.steps.trainer import BaseTrainerStep
from zenml.steps.trainer import utils as trainer_utils
from zenml.utils import naming_utils
from zenml.utils import path_utils
from zenml.utils.post_training.post_training_utils import \
    convert_raw_dataset_to_pandas


class MyScikitTrainer(BaseTrainerStep):
    """
    Scikit trainer to train a scikit-learn based classifier model.
    """

    def __init__(self, C: float = 1.0, kernel: Text = 'rbf', **kwargs):
        self.C = C
        self.kernel = kernel

        super(MyScikitTrainer, self).__init__(
            C=self.C,
            kernel=self.kernel,
            **kwargs
        )

    def run_fn(self):
        tf_transform_output = tft.TFTransformOutput(self.transform_output)

        X_train, y_train = self.input_fn(self.train_files, tf_transform_output)
        X_eval, y_eval = self.input_fn(self.eval_files, tf_transform_output)

        clf = svm.SVC(C=self.C, kernel=self.kernel)
        clf.fit(X_train, y_train)

        y_pred = clf.predict(X_eval)

        print("*********EVALUATION START******************")
        print(confusion_matrix(y_eval, y_pred))
        print(classification_report(y_eval, y_pred))
        print("*********EVALUATION DONE******************")

        # Save to serving_model_dir
        dump(clf, self.serving_model_dir)

        # for model agnostic evaluator
        test_results = self.test_fn(clf, X_eval, y_eval)
        trainer_utils.save_test_results(test_results, self.test_results)

    def input_fn(self,
                 file_pattern: List[Text],
                 tf_transform_output: tft.TFTransformOutput):
        """
        Load TFRecords on disk to pandas dataframe.

        Args:
            file_pattern: File pattern matching saved TFRecords on disk.
            tf_transform_output: Output of the preceding Transform /
             Preprocessing component.

        Returns:
            dataset: tf.data.Dataset created out of the input files.
        """
        xf_feature_spec = tf_transform_output.transformed_feature_spec()

        root_path = [x.replace("*", "") for x in file_pattern][0]
        dataset = tf.data.TFRecordDataset(
            path_utils.list_dir(root_path),  # a bit ugly
            compression_type='GZIP')
        df = convert_raw_dataset_to_pandas(dataset, xf_feature_spec, 100000)

        # Separate labels
        X = df[[x for x in df.columns if
                naming_utils.check_if_transformed_feature(x)]]
        y = df[[x for x in df.columns if
                naming_utils.check_if_transformed_label(x)]]
        return X, y

    def test_fn(self, model, X_eval, y_eval):
        label_name = y_eval.columns[0]
        y_pred = model.predict(X_eval)

        out_dict = {
            label_name: y_eval.values,
            naming_utils.output_name(label_name): y_pred,
        }
        out_dict.update({k: np.array(v) for k, v
                         in X_eval.to_dict(orient='list').items()})
        return out_dict
