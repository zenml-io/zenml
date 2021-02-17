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

        # decode base64
        results = self.client.predict(payload, model_name)
        return {"output": results}
