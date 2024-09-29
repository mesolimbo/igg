import json
import os

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from _typeshed import SupportsRead, SupportsWrite

import boto3
from botocore.exceptions import ClientError

import generate_markov_models

def lambda_handler(event, _):
    s3 = boto3.client('s3')

    # Get the bucket and key from the event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    # Only process CSV files
    if not key.lower().endswith('.csv'):
        print(f"File {key} is not a CSV. Skipping.")
        return

    # Convert the CSV file into a Markov model
    model_key = process_model(s3, bucket, key)

    # Add new models to the main index
    update_index(s3, bucket, model_key)


def process_model(s3, bucket, key):
    # Download the CSV file to /tmp directory
    download_path = os.path.join('/tmp', os.path.basename(key))
    s3.download_file(bucket, key, download_path)

    # Generate the model JSON filename (same as CSV but with .json extension)
    model_key = os.path.splitext(key)[0] + '.json'
    json_path = os.path.join('/tmp', os.path.basename(model_key))

    # Convert the CSV file into a JSON model using the generate function
    generate_markov_models.generate(download_path, json_path)

    # Upload the JSON file back to S3
    s3.upload_file(json_path, bucket, model_key)
    print(f"Processed {key} and uploaded {model_key} to {bucket}")
    return model_key


def update_index(s3, bucket, model_key):
    # Update the index.json file
    index_key = 'index.json'  # Adjust the path if necessary
    index_path = os.path.join('/tmp', 'index.json')

    try:
        # Download the current index.json
        s3.download_file(bucket, index_key, index_path)

        # Read the existing index.json
        fr: SupportsRead[str]
        with open(index_path, 'r') as fr:
            index_data = json.load(fr)
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            # index.json does not exist, create a new one
            index_data = {'models': []}
        else:
            # Other errors
            print(f"Error downloading index.json: {e}")
            raise e

    # Add the new model JSON path to the index
    if model_key not in index_data['models']:
        index_data['models'].append(model_key)

    # Save the updated index.json
    fw: SupportsWrite[str]
    with open(index_path, 'w') as fw:
        json.dump(index_data, fw)

    # Upload the updated index.json to S3
    s3.upload_file(index_path, bucket, index_key)

    print(f"Updated index.json with {model_key}")
