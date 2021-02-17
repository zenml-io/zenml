import tensorflow as tf


# The following functions can be used to convert a value to a type compatible
# with tf.train.Example.

def _bytes_feature(value):
    """Returns a bytes_list from a string / byte."""
    if isinstance(value, type(tf.constant(0))):
        value = value.numpy()  # BytesList won't unpack a string from an
        # EagerTensor.
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))


def _float_feature(value):
    """Returns a float_list from a float / double."""
    return tf.train.Feature(float_list=tf.train.FloatList(value=[value]))


def _int64_feature(value):
    """Returns an int64_list from a bool / enum / int / uint."""
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))


def prepare_tf_example(raw_dict):
    feature = {}
    for k, v in raw_dict.items():
        if type(v) == int:
            feature[k] = _int64_feature(v)
        elif type(v) == float:
            feature[k] = _float_feature(v)
        else:
            feature[k] = _bytes_feature(str(v).encode())

    # return the TFExample
    return tf.train.Example(features=tf.train.Features(feature=feature))


class TensorFlowPredictor:
    def __init__(self, tensorflow_client, config):
        print("Got config to be %s" % str(config))
        self.client = tensorflow_client
        self.model_path = config['model_artifact']

    def predict(self, payload, query_params):
        print("Got payload to be %s" % str(payload))
        print("Got query_params to be %s" % str(query_params))

        model_name = None
        if 'model' in query_params:
            model_name = query_params['model']

        # Convert to TFExample because we used the TensorflowTrainer
        tf_example = prepare_tf_example(payload)
        model_input = {
            "examples": [tf_example.SerializeToString()]
        }
        # do a forward pass with the model
        return self.client.predict(model_input, model_name)
