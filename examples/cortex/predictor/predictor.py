class PythonPredictor:
    def __init__(self, config):
        # Initialize your model here
        print("Got config to be %s" % str(config))
        self.model_path = config['model_artifact']

    def predict(self, payload):
        # Payload is the request your endpoint receives
        prediction = self.model
        return prediction
