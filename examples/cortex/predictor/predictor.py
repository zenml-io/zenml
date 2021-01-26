class TensorFlowPredictor:
    def __init__(self, tensorflow_client, config):
        print("Got config to be %s" % str(config))
        self.client = tensorflow_client
        self.model_path = config['model_artifact']

    def predict(self, payload, query_params):
        model_name = query_params["model"]
        model_input = preprocess(payload["url"])
        results = self.client.predict(model_input, model_name)
        predicted_label = postprocess(results)
        return {"label": predicted_label}
