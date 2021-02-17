import base64
import json

import requests
import tensorflow as tf


def prepare_tfexample():
    """
    Prepares a TF Example.
    """

    feature = {
        'times_pregnant': tf.train.Feature(
            int64_list=tf.train.Int64List(value=[6])),
        'pgc': tf.train.Feature(int64_list=tf.train.Int64List(value=[148])),
        'dbp': tf.train.Feature(int64_list=tf.train.Int64List(value=[72])),
        'tst': tf.train.Feature(int64_list=tf.train.Int64List(value=[35])),
        'insulin': tf.train.Feature(int64_list=tf.train.Int64List(value=[0])),
        'bmi': tf.train.Feature(float_list=tf.train.FloatList(value=[33.6])),
        'pedigree': tf.train.Feature(
            float_list=tf.train.FloatList(value=[0.627])),
        'age': tf.train.Feature(int64_list=tf.train.Int64List(value=[50])),
    }

    # return the TFExample
    return tf.train.Example(features=tf.train.Features(feature=feature))


def make_predict(json_request):
    headers = {
        'Content-Type': 'application/json',
    }

    data = json.dumps(json_request)

    response = requests.post('http://35.226.91.12/zenml-classifier',
                             headers=headers, data=data)
    print(response.text)


example = prepare_tfexample()
instance = {
    "examples": {
        "b64": base64.b64encode(example.SerializeToString()).decode("utf-8")
    }
}
make_predict(instance)

# import json
# import base64
#
# e =
# 'CosBCg8KA2JtaRIIEgYKBGZmBkIKDAoDZGJwEgUaAwoBSAoQCgdpbnN1bGluEgUaAwoBAAoUCghwZWRpZ3JlZRIIEgYKBBKDID8KDAoDYWdlEgUaAwoBMgoMCgN0c3QSBRoDCgEjCg0KA3BnYxIGGgQKApQBChcKDnRpbWVzX3ByZWduYW50EgUaAwoBBg=='
# t = base64.b64decode(e)
# print(t)
