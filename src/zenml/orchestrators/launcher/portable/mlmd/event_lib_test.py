# Copyright 2020 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for tfx.orchestration.portable.mlmd.event_lib."""

import tensorflow as tf
from tfx.orchestration.portable.mlmd import event_lib

from google.protobuf import text_format
from ml_metadata.proto import metadata_store_pb2


class EventLibTest(tf.test.TestCase):

  def testIsDesiredOutputEvent(self):
    output_event = text_format.Parse(
        """
        type: OUTPUT
        path {
          steps {
            key: 'right_key'
          }
          steps {
            index: 1
          }
        }
        """, metadata_store_pb2.Event())
    declared_output_event = text_format.Parse(
        """
        type: DECLARED_OUTPUT
        path {
          steps {
            key: 'right_key'
          }
          steps {
            index: 1
          }
        }
        """, metadata_store_pb2.Event())
    internal_output_event = text_format.Parse(
        """
        type: INTERNAL_OUTPUT
        path {
          steps {
            key: 'right_key'
          }
          steps {
            index: 1
          }
        }
        """, metadata_store_pb2.Event())
    input_event = text_format.Parse(
        """
        type: INPUT
        path {
          steps {
            key: 'right_key'
          }
          steps {
            index: 1
          }
        }
        """, metadata_store_pb2.Event())
    empty_event = text_format.Parse('type: OUTPUT', metadata_store_pb2.Event())

    self.assertTrue(
        event_lib.is_valid_output_event(output_event, 'right_key'))
    self.assertTrue(
        event_lib.is_valid_output_event(declared_output_event, 'right_key'))
    self.assertTrue(
        event_lib.is_valid_output_event(internal_output_event, 'right_key'))
    self.assertFalse(
        event_lib.is_valid_output_event(output_event, 'wrong_key'))
    self.assertFalse(
        event_lib.is_valid_output_event(input_event, 'right_key'))
    self.assertFalse(event_lib.is_valid_output_event(empty_event, 'right_key'))
    self.assertTrue(event_lib.is_valid_output_event(empty_event))

  def testIsDesiredInputEvent(self):
    output_event = metadata_store_pb2.Event()
    text_format.Parse(
        """
        type: OUTPUT
        path {
          steps {
            key: 'right_key'
          }
          steps {
            index: 1
          }
        }
        """, output_event)
    input_event = metadata_store_pb2.Event()
    text_format.Parse(
        """
        type: INPUT
        path {
          steps {
            key: 'right_key'
          }
          steps {
            index: 1
          }
          steps {
            key: 'another_right_key'
          }
          steps {
            index: 1
          }
        }
        """, input_event)
    empty_event = metadata_store_pb2.Event()
    text_format.Parse('type: INPUT', empty_event)

    self.assertTrue(
        event_lib.is_valid_input_event(input_event, 'right_key'))
    self.assertTrue(
        event_lib.is_valid_input_event(input_event, 'another_right_key'))
    self.assertFalse(
        event_lib.is_valid_input_event(input_event, 'wrong_key'))
    self.assertFalse(
        event_lib.is_valid_input_event(output_event, 'right_key'))
    self.assertFalse(event_lib.is_valid_input_event(empty_event, 'right_key'))
    self.assertTrue(event_lib.is_valid_input_event(empty_event))

  def testGenerateEvent(self):
    self.assertProtoEquals(
        """
        type: INPUT
        path {
          steps {
            key: 'key'
          }
          steps {
            index: 1
          }
        }
        artifact_id: 2
        execution_id: 3
        """,
        event_lib.generate_event(
            event_type=metadata_store_pb2.Event.INPUT,
            key='key',
            index=1,
            artifact_id=2,
            execution_id=3))


if __name__ == '__main__':
  tf.test.main()
