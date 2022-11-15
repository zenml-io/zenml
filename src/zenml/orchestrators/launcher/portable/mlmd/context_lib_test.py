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
"""Tests for tfx.orchestration.portable.mlmd.context_lib."""
import os
import tensorflow as tf

from tfx.orchestration import metadata
from tfx.orchestration.portable.mlmd import context_lib
from tfx.proto.orchestration import pipeline_pb2
from tfx.utils import test_case_utils
from ml_metadata.proto import metadata_store_pb2


class ContextLibTest(test_case_utils.TfxTest):

  def setUp(self):
    super().setUp()
    self._connection_config = metadata_store_pb2.ConnectionConfig()
    self._connection_config.sqlite.SetInParent()
    self._testdata_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'testdata')

  def testRegisterContexts(self):
    node_contexts = pipeline_pb2.NodeContexts()
    self.load_proto_from_text(
        os.path.join(self._testdata_dir, 'node_context_spec.pbtxt'),
        node_contexts)
    with metadata.Metadata(connection_config=self._connection_config) as m:
      context_lib.prepare_contexts(
          metadata_handler=m, node_contexts=node_contexts)
      # Duplicated call should succeed.
      contexts = context_lib.prepare_contexts(
          metadata_handler=m, node_contexts=node_contexts)

      got_context_type_one = m.store.get_context_type('my_context_type_one')
      got_context_type_one.ClearField('id')
      self.assertProtoEquals(
          """
          name: 'my_context_type_one'
          """, got_context_type_one)
      got_context_type_two = m.store.get_context_type('my_context_type_two')
      got_context_type_two.ClearField('id')

      self.assertProtoEquals(
          """
          name: 'my_context_type_two'
          """, got_context_type_two)
      self.assertEqual(
          contexts[0],
          m.store.get_context_by_type_and_name('my_context_type_one',
                                               'my_context_one'))
      self.assertEqual(
          contexts[1],
          m.store.get_context_by_type_and_name('my_context_type_one',
                                               'my_context_two'))
      self.assertEqual(
          contexts[2],
          m.store.get_context_by_type_and_name('my_context_type_two',
                                               'my_context_three'))
      self.assertEqual(contexts[0].custom_properties['property_a'].int_value, 1)
      self.assertEqual(contexts[1].custom_properties['property_a'].int_value, 2)
      self.assertEqual(contexts[2].custom_properties['property_a'].int_value, 3)
      self.assertEqual(contexts[2].custom_properties['property_b'].string_value,
                       '4')

  def testRegisterContextByTypeAndName(self):
    with metadata.Metadata(connection_config=self._connection_config) as m:
      context_lib.register_context_if_not_exists(
          metadata_handler=m,
          context_type_name='my_context_type',
          context_name='my_context')
      # Duplicated call should succeed.
      context = context_lib.register_context_if_not_exists(
          metadata_handler=m,
          context_type_name='my_context_type',
          context_name='my_context')

      got_context_type = m.store.get_context_type('my_context_type')
      got_context_type.ClearField('id')
      self.assertProtoEquals(
          """
          name: 'my_context_type'
          """, got_context_type)
      self.assertEqual(
          context,
          m.store.get_context_by_type_and_name('my_context_type', 'my_context'))

  def testPutParentContextIfNotExists(self):
    with metadata.Metadata(connection_config=self._connection_config) as m:
      parent_context = context_lib.register_context_if_not_exists(
          metadata_handler=m,
          context_type_name='my_context_type',
          context_name='parent_context_name')
      child_context = context_lib.register_context_if_not_exists(
          metadata_handler=m,
          context_type_name='my_context_type',
          context_name='child_context_name')
      context_lib.put_parent_context_if_not_exists(m,
                                                   parent_id=parent_context.id,
                                                   child_id=child_context.id)
      # Duplicated call should succeed.
      context_lib.put_parent_context_if_not_exists(m,
                                                   parent_id=parent_context.id,
                                                   child_id=child_context.id)


if __name__ == '__main__':
  tf.test.main()
