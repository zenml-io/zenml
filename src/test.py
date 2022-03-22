import json

import boto3 as boto3

SSNAME = 'default'

session = boto3.session.Session()
client = session.client(
    service_name="secretsmanager", region_name="us-east-1"
)

secret_value = json.dumps({'c': 'd'})
try:
    kwargs = {"Name": SSNAME, "SecretString": secret_value}
    response = client.create_secret(**kwargs)
except:
    kwargs = {"SecretId": SSNAME, "SecretString": secret_value}
    response = client.put_secret_value(**kwargs)

get_secret_value_response = client.get_secret_value(
    SecretId=SSNAME
)

print(get_secret_value_response['SecretString'])
# from click.testing import CliRunner
#
# from zenml.cli.secret import secret
#
# runner = CliRunner()
# result = runner.invoke(secret, ['register',
#                                 'saffive',
#                                 '--secret=aws'])


# # Use this code snippet in your app.
# # If you need more information about configurations or implementing the sample code, visit the AWS docs:
# # https://aws.amazon.com/developers/getting-started/python/
#
# import boto3
# import base64
# from botocore.exceptions import ClientError
#
# secret_name = "SecretSecret"
# region_name = "us-east-1"
#
# # Create a Secrets Manager client
# session = boto3.session.Session()
# client = session.client(
#     service_name='secretsmanager',
#     region_name=region_name
# )
#
# # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
# # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
# # We rethrow the exception by default.
#
# try:
#     get_secret_value_response = client.get_secret_value(
#         SecretId=secret_name
#     )
# except ClientError as e:
#     if e.response['Error']['Code'] == 'DecryptionFailureException':
#         # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
#         # Deal with the exception here, and/or rethrow at your discretion.
#         raise e
#     elif e.response['Error']['Code'] == 'InternalServiceErrorException':
#         # An error occurred on the server side.
#         # Deal with the exception here, and/or rethrow at your discretion.
#         raise e
#     elif e.response['Error']['Code'] == 'InvalidParameterException':
#         # You provided an invalid value for a parameter.
#         # Deal with the exception here, and/or rethrow at your discretion.
#         raise e
#     elif e.response['Error']['Code'] == 'InvalidRequestException':
#         # You provided a parameter value that is not valid for the current state of the resource.
#         # Deal with the exception here, and/or rethrow at your discretion.
#         raise e
#     elif e.response['Error']['Code'] == 'ResourceNotFoundException':
#         # We can't find the resource that you asked for.
#         # Deal with the exception here, and/or rethrow at your discretion.
#         raise e
# else:
#     # Decrypts secret using the associated KMS key.
#     # Depending on whether the secret is a string or binary, one of these fields will be populated.
#     if 'SecretString' in get_secret_value_response:
#         secret = get_secret_value_response['SecretString']
#
#         print(secret)
#     else:
#         decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
#
#         print(decoded_binary_secret)
