import json
import os
import csv
import boto3
import re
from io import StringIO
from typing import Dict, List, Any
import logging
from collections import defaultdict, Counter

import pandas as pd
import nltk

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')

# Initialize NLTK (Lambda-friendly paths)
nltk.data.path.append("/tmp")
nltk.download('punkt', download_dir='/tmp', quiet=True)
nltk.download('punkt_tab', download_dir='/tmp', quiet=True)


# Markov chain generation functions (from existing generate_markov_models.py)
def normalize(counter):
    """Function to normalize counts to probabilities."""
    total = sum(counter.values())
    return {k: v / total for k, v in counter.items()}


def preprocess_text(text):
    """Function to preprocess text."""
    # Remove non-alphanumeric characters (keep letters and numbers)
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    # Strip leading and trailing whitespace
    text = text.strip()
    return text


def extract_phrases(end_words, lengths, phrases, start_words, transitions):
    """Extract phrases and build transition data."""
    for phrase in phrases:
        # Preprocess the phrase
        clean_phrase = preprocess_text(phrase)

        # Tokenize the phrase into words
        tokens = nltk.word_tokenize(clean_phrase)
        lengths.append(len(tokens))

        if tokens:
            # Count the start word
            start_words[tokens[0]] += 1
            # Count the end word
            end_words[tokens[-1]] += 1

            # Build transitions
            for i in range(len(tokens) - 1):
                transitions[tokens[i]][tokens[i + 1]] += 1


def extract_columns(df):
    """Extract Markov models from DataFrame columns."""
    markov_models = []

    # Process each column
    for col in df.columns:
        phrases = df[col].dropna().astype(str).tolist()
        transitions = defaultdict(Counter)
        start_words = Counter()
        end_words = Counter()
        lengths = []

        extract_phrases(end_words, lengths, phrases, start_words, transitions)

        # Normalize the counts
        transitions_prob = {k: normalize(v) for k, v in transitions.items()}
        start_words_prob = normalize(start_words)
        end_words_prob = normalize(end_words)
        lengths_counts = Counter(lengths)
        lengths_prob = normalize(lengths_counts)

        # Store the model for the column
        column_model = {
            'column_index': col,
            'transitions': transitions_prob,
            'start_words': start_words_prob,
            'end_words': end_words_prob,
            'lengths': lengths_prob
        }
        markov_models.append(column_model)

    return markov_models


def lambda_handler(event, context):
    """
    Lambda handler for processing CSV files uploaded to S3.
    Converts CSV files to JSON models and updates index.json.
    """
    bucket_name = os.environ['BUCKET_NAME']
    index_file = os.environ.get('INDEX_FILE', 'index.json')
    
    try:
        for record in event['Records']:
            # Get the uploaded file details
            s3_event = record['s3']
            key = s3_event['object']['key']
            
            logger.info(f"Processing file: {key}")
            
            # Skip if not a CSV file
            if not key.lower().endswith('.csv'):
                logger.info(f"Skipping non-CSV file: {key}")
                continue
            
            # Download and process the CSV file
            csv_content = download_file(bucket_name, key)
            json_data = process_csv(csv_content, key)
            
            # Generate output JSON file path (same path, .json extension)
            json_key = key.rsplit('.', 1)[0] + '.json'
            
            # Upload the JSON file
            upload_json(bucket_name, json_key, json_data)
            
            # Update the index
            update_index(bucket_name, index_file, json_key, json_data)
            
            logger.info(f"Successfully processed {key} -> {json_key}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully processed {len(event["Records"])} files'
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing files: {str(e)}")
        raise


def download_file(bucket_name: str, key: str) -> str:
    """Download file content from S3."""
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        return response['Body'].read().decode('utf-8')
    except Exception as e:
        logger.error(f"Error downloading {key}: {str(e)}")
        raise


def process_csv(csv_content: str, filename: str) -> Dict[str, Any]:
    """Process CSV content and convert to Markov chain models."""
    try:
        # Read CSV into pandas DataFrame (matching original generate_markov_models.py)
        df = pd.read_csv(StringIO(csv_content), header=None)
        
        # Generate Markov models using existing logic
        markov_models = extract_columns(df)
        
        # Create JSON structure with metadata and Markov chains
        json_data = {
            'metadata': {
                'source_file': filename,
                'column_count': len(df.columns),
                'row_count': len(df),
                'model_type': 'markov_chain',
                'generated_at': context.aws_request_id if 'context' in globals() else 'unknown'
            },
            'markov_models': markov_models
        }
        
        return json_data
        
    except Exception as e:
        logger.error(f"Error processing CSV {filename}: {str(e)}")
        raise


def upload_json(bucket_name: str, key: str, data: Dict[str, Any]) -> None:
    """Upload JSON data to S3."""
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=json.dumps(data, indent=2),
            ContentType='application/json'
        )
    except Exception as e:
        logger.error(f"Error uploading {key}: {str(e)}")
        raise


def update_index(bucket_name: str, index_key: str, new_file_key: str, file_data: Dict[str, Any]) -> None:
    """Update the index.json file with information about the new JSON file."""
    try:
        # Try to get existing index
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=index_key)
            index_data = json.loads(response['Body'].read().decode('utf-8'))
        except s3_client.exceptions.NoSuchKey:
            # Create new index if it doesn't exist
            index_data = {
                'files': [],
                'last_updated': None,
                'total_files': 0
            }
        
        # Update or add file entry
        file_entry = {
            'path': new_file_key,
            'model_type': file_data['metadata'].get('model_type', 'markov_chain'),
            'column_count': file_data['metadata'].get('column_count', 0),
            'row_count': file_data['metadata'].get('row_count', 0),
            'model_count': len(file_data.get('markov_models', [])),
            'last_modified': context.aws_request_id if 'context' in globals() else 'unknown'
        }
        
        # Remove existing entry if it exists, then add new one
        index_data['files'] = [f for f in index_data.get('files', []) if f.get('path') != new_file_key]
        index_data['files'].append(file_entry)
        
        # Update metadata
        index_data['total_files'] = len(index_data['files'])
        index_data['last_updated'] = file_entry['last_modified']
        
        # Upload updated index
        s3_client.put_object(
            Bucket=bucket_name,
            Key=index_key,
            Body=json.dumps(index_data, indent=2),
            ContentType='application/json'
        )
        
    except Exception as e:
        logger.error(f"Error updating index {index_key}: {str(e)}")
        # Don't raise - index update failure shouldn't fail the whole process
        pass
