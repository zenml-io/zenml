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

import tensorflow as tf
import tensorflow_transform as tft
from joblib import dump
from sklearn import svm
from sklearn.metrics import classification_report, confusion_matrix

from zenml.core.steps.trainer.base_trainer import BaseTrainerStep
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

        xf_feature_spec = {x: xf_feature_spec[x]
                           for x in xf_feature_spec
                           if x.endswith('_xf')}

        root_path = [x.replace("*", "") for x in file_pattern][0]
        dataset = tf.data.TFRecordDataset(
            path_utils.list_dir(root_path),  # a bit ugly
            compression_type='GZIP')
        df = convert_raw_dataset_to_pandas(dataset, xf_feature_spec, 100000)

        # Seperate labels
        X = df[[x for x in df.columns if 'label_' not in x]]
        y = df[[x for x in df.columns if 'label_' in x]]
        return X, y
