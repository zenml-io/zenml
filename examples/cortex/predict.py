import json
import os

import requests

CORTEX_ENDPOINT = os.getenv('CORTEX_ENV_ENDPOINT')
CORTEX_MODEL_NAME = os.getenv('CORTEX_MODEL_NAME')
assert CORTEX_ENDPOINT
assert CORTEX_MODEL_NAME

ENDPOINT = f'{CORTEX_ENDPOINT}/{CORTEX_MODEL_NAME}'


def make_predict(json_request):
    headers = {
        'Content-Type': 'application/json',
    }
    data = json.dumps(json_request)
    response = requests.post(ENDPOINT, headers=headers, data=data)
    return response.json()


def main():
    data = {
        "times_pregnant": 1,
        "pgc": 148,
        "dbp": 72,
        "tst": 35,
        "insulin": 100,
        "bmi": 33.6,
        "pedigree": 0.627,
        "age": 50,
    }
    response = make_predict(data)
    print(
        f'The probability of this person to have diabetes: '
        f'{response["has_diabetes"][0]}')


if __name__ == '__main__':
    main()
