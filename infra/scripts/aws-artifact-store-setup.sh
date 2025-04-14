#!/usr/bin/env bash

# Exit on error
set -e

# Name used for the stack, service connector, and artifact store and as a prefix
# for all created resources
NAME="${NAME:-zenml-aws}"

# Region to create the bucket in
REGION="${REGION:-eu-central-1}"

# Generate random suffix if not externally set
if [ -z "${RANDOM_SUFFIX}" ]; then
    RANDOM_SUFFIX=$(LC_ALL=C tr -dc 'a-z0-9' < /dev/urandom | fold -w 8 | head -n 1)
fi
PREFIX="${NAME}-${RANDOM_SUFFIX}"

# Extract AWS account ID (we need this for IAM ARNs)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

BUCKET_NAME="${PREFIX}"
USER_POLICY_NAME="assume-role"
BUCKET_POLICY_NAME="s3-access"
SERVICE_CONNECTOR_NAME="${NAME}-s3"
ARTIFACT_STORE_NAME="${NAME}-s3"

# Function to print cleanup instructions
print_cleanup_instructions() {
    echo
    echo "To cleanup the stack and resources, run the following commands in the order given:"
    echo "(some commands may fail if resources don't exist)"
    echo
    echo "zenml stack delete -y $NAME"
    echo "zenml artifact-store delete $ARTIFACT_STORE_NAME"
    echo "zenml service-connector delete $SERVICE_CONNECTOR_NAME"
    echo "aws iam delete-role-policy --role-name $PREFIX --policy-name $BUCKET_POLICY_NAME"
    echo "aws iam delete-role --role-name $PREFIX"
    echo "aws iam delete-user-policy --user-name $PREFIX --policy-name $USER_POLICY_NAME"
    echo "aws iam delete-access-key --user-name $PREFIX --access-key-id $AWS_ACCESS_KEY_ID"
    echo "aws iam delete-user --user-name $PREFIX"
    echo "aws s3api delete-bucket --bucket $BUCKET_NAME"
}

# Set up trap to call cleanup instructions on script exit (success or failure)
trap print_cleanup_instructions EXIT


# Create S3 bucket
echo "Creating AWS bucket: $PREFIX"
aws s3api create-bucket \
    --bucket "$PREFIX" \
    --region "$REGION" \
    --create-bucket-configuration LocationConstraint="$REGION"

# Create IAM user and access key
echo "Creating IAM user: $PREFIX"
aws iam create-user --user-name "$PREFIX"

# Allow user to assume any role
echo "Allowing user to assume roles"
USER_POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "sts:AssumeRole",
            "Resource": "*"
        }
    ]
}
EOF
)

aws iam put-user-policy \
    --user-name "$PREFIX" \
    --policy-name "$USER_POLICY_NAME" \
    --policy-document "$USER_POLICY"

echo "Creating IAM access key for user: $PREFIX"
AWS_CREDENTIALS=$(aws iam create-access-key --user-name "$PREFIX")
AWS_ACCESS_KEY_ID=$(echo "$AWS_CREDENTIALS" | jq -r .AccessKey.AccessKeyId)
AWS_SECRET_ACCESS_KEY=$(echo "$AWS_CREDENTIALS" | jq -r .AccessKey.SecretAccessKey)

# Give AWS time to propagate the IAM credentials changes
sleep 10

# Create IAM role
echo "Creating IAM role: $PREFIX"
ASSUME_ROLE_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::${ACCOUNT_ID}:user/${PREFIX}"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
)

aws iam create-role \
    --role-name "$PREFIX" \
    --assume-role-policy-document "$ASSUME_ROLE_POLICY"

# Attach S3 bucket policy to role
BUCKET_POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:*"
            ],
            "Resource": [
                "arn:aws:s3:::${BUCKET_NAME}",
                "arn:aws:s3:::${BUCKET_NAME}/*"
            ]
        }
    ]
}
EOF
)

aws iam put-role-policy \
    --role-name "$PREFIX" \
    --policy-name "$BUCKET_POLICY_NAME" \
    --policy-document "$BUCKET_POLICY"

# Give AWS time to propagate the IAM credentials changes
sleep 10

# Create ZenML service connector
zenml service-connector register "$SERVICE_CONNECTOR_NAME" \
    --type aws \
    --auth-method iam-role \
    --resource-type s3-bucket \
    --resource-id "$BUCKET_NAME" \
    --region="$REGION" \
    --role_arn="arn:aws:iam::${ACCOUNT_ID}:role/${PREFIX}" \
    --aws_access_key_id="$AWS_ACCESS_KEY_ID" \
    --aws_secret_access_key="$AWS_SECRET_ACCESS_KEY"

# Create ZenML artifact store
zenml artifact-store register "$ARTIFACT_STORE_NAME" \
    --flavor s3 \
    --path="s3://${BUCKET_NAME}" \
    --connector "$SERVICE_CONNECTOR_NAME"

# Create ZenML stack
zenml stack register "$NAME" \
    -a "${ARTIFACT_STORE_NAME}" \
    -o default

echo "Successfully created AWS resources and ZenML stack:"
echo "- S3 bucket: $BUCKET_NAME"
echo "- IAM user: $PREFIX"
echo "- IAM role: $PREFIX"
echo "- ZenML service connector: $SERVICE_CONNECTOR_NAME"
echo "- ZenML artifact store: $ARTIFACT_STORE_NAME"
echo "- ZenML stack: $NAME"
echo
