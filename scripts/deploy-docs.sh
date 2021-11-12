#!/bin/sh -e
set -x
set -e

DOCS_PATH=${1:-"docs/sphinx_docs/_build/html"}

export ZENML_DEBUG=1
cd $DOCS_PATH && html-minifier --collapse-whitespace --remove-comments --remove-optional-tags --remove-redundant-attributes --remove-script-type-attributes --remove-tag-whitespace --use-short-doctype --minify-css true --minify-js true; cd ../
aws s3 sync $DOCS_PATH s3://$AWS_BUCKET --region eu-central-1 --delete
aws s3 website s3://$AWS_BUCKET --index-document index.html --error-document 404.html  --region eu-central-1
aws cloudfront create-invalidation --distribution-id $CLOUDFRONT_DISTRIBUTION_ID --paths "/*"
