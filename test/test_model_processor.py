import pytest
from unittest.mock import patch, MagicMock, mock_open
import pandas as pd
from collections import Counter, defaultdict
import json
from io import StringIO

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import model_processor


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing."""
    return """Hello world,Sample text
Test phrase,More data  
Another example,Final entry"""


@pytest.fixture
def sample_dataframe():
    """Sample DataFrame for testing."""
    data = {
        0: ["Hello world", "Test phrase", "Another example"],
        1: ["Sample text", "More data", "Final entry"]
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_s3_event():
    """Sample S3 event for Lambda testing."""
    return {
        'Records': [
            {
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {'key': 'test-file.csv'}
                }
            }
        ]
    }


@pytest.fixture
def sample_context():
    """Sample Lambda context for testing."""
    context = MagicMock()
    context.aws_request_id = 'test-request-id-123'
    return context


class TestMarkovFunctions:
    """Test the core Markov chain generation functions."""

    def test_normalize_converts_counts_to_probabilities(self):
        counter = Counter({'a': 2, 'b': 3, 'c': 5})
        result = model_processor.normalize(counter)
        expected = {'a': 0.2, 'b': 0.3, 'c': 0.5}
        assert result == expected

    def test_normalize_handles_empty_counter(self):
        counter = Counter()
        result = model_processor.normalize(counter)
        assert result == {}

    def test_preprocess_text_removes_non_alphanumeric(self):
        text = "Hello, world! 1-2-3"
        result = model_processor.preprocess_text(text)
        assert result == "Hello world 123"

    def test_preprocess_text_replaces_multiple_spaces(self):
        text = "Hello   world    test"
        result = model_processor.preprocess_text(text)
        assert result == "Hello world test"

    def test_preprocess_text_strips_whitespace(self):
        text = "  Hello world  "
        result = model_processor.preprocess_text(text)
        assert result == "Hello world"

    @patch('model_processor.nltk.word_tokenize')
    def test_extract_phrases_creates_transitions(self, mock_tokenize):
        mock_tokenize.side_effect = [
            ["Hello", "world"],
            ["Hello", "there"],
            ["world", "peace"]
        ]
        
        phrases = ["Hello world", "Hello there", "world peace"]
        transitions = defaultdict(Counter)
        start_words = Counter()
        end_words = Counter()
        lengths = []
        
        model_processor.extract_phrases(end_words, lengths, phrases, start_words, transitions)
        
        assert start_words["Hello"] == 2
        assert start_words["world"] == 1
        assert end_words["world"] == 1
        assert end_words["there"] == 1
        assert end_words["peace"] == 1
        assert transitions["Hello"]["world"] == 1
        assert transitions["Hello"]["there"] == 1
        assert transitions["world"]["peace"] == 1
        assert lengths == [2, 2, 2]

    @patch('model_processor.extract_phrases')
    def test_extract_columns_creates_markov_models(self, mock_extract_phrases, sample_dataframe):
        # Mock the extract_phrases function to avoid NLTK dependency in tests
        def mock_extract_side_effect(end_words, lengths, phrases, start_words, transitions):
            start_words.update({'Hello': 1, 'Test': 1})
            end_words.update({'world': 1, 'phrase': 1})
            transitions['Hello']['world'] = 1
            lengths.extend([2, 2])
        
        mock_extract_phrases.side_effect = mock_extract_side_effect
        
        result = model_processor.extract_columns(sample_dataframe)
        
        assert len(result) == 2
        assert all('column_index' in model for model in result)
        assert all('transitions' in model for model in result)
        assert all('start_words' in model for model in result)
        assert all('end_words' in model for model in result)
        assert all('lengths' in model for model in result)


class TestCSVProcessing:
    """Test CSV processing functionality."""

    @patch('model_processor.extract_columns')
    @patch('model_processor.pd.read_csv')
    def test_process_csv_creates_markov_models(self, mock_read_csv, mock_extract_columns, sample_csv_content):
        # Mock pandas read_csv
        mock_df = MagicMock()
        mock_df.columns = [0, 1]
        mock_df.__len__ = MagicMock(return_value=3)
        mock_read_csv.return_value = mock_df
        
        # Mock extract_columns
        mock_markov_models = [
            {
                'column_index': 0,
                'transitions': {'Hello': {'world': 1.0}},
                'start_words': {'Hello': 1.0},
                'end_words': {'world': 1.0},
                'lengths': {2: 1.0}
            }
        ]
        mock_extract_columns.return_value = mock_markov_models
        
        result = model_processor.process_csv(sample_csv_content, "test.csv")
        
        # Verify structure
        assert 'metadata' in result
        assert 'markov_models' in result
        assert result['metadata']['source_file'] == "test.csv"
        assert result['metadata']['column_count'] == 2
        assert result['metadata']['row_count'] == 3
        assert result['metadata']['model_type'] == 'markov_chain'
        assert result['markov_models'] == mock_markov_models
        
        # Verify pandas was called correctly
        mock_read_csv.assert_called_once()
        args, kwargs = mock_read_csv.call_args
        assert kwargs.get('header') is None


class TestS3Operations:
    """Test S3 interaction functions."""

    @patch('model_processor.s3_client')
    def test_download_file_success(self, mock_s3_client):
        mock_s3_client.get_object.return_value = {
            'Body': MagicMock(read=MagicMock(return_value=b'test,content'))
        }
        
        result = model_processor.download_file('test-bucket', 'test.csv')
        
        assert result == 'test,content'
        mock_s3_client.get_object.assert_called_once_with(Bucket='test-bucket', Key='test.csv')

    @patch('model_processor.s3_client')
    def test_download_file_handles_exception(self, mock_s3_client):
        mock_s3_client.get_object.side_effect = Exception("S3 error")
        
        with pytest.raises(Exception, match="S3 error"):
            model_processor.download_file('test-bucket', 'test.csv')

    @patch('model_processor.s3_client')
    def test_upload_json_success(self, mock_s3_client):
        test_data = {'test': 'data'}
        
        model_processor.upload_json('test-bucket', 'test.json', test_data)
        
        mock_s3_client.put_object.assert_called_once()
        args, kwargs = mock_s3_client.put_object.call_args
        assert kwargs['Bucket'] == 'test-bucket'
        assert kwargs['Key'] == 'test.json'
        assert kwargs['ContentType'] == 'application/json'
        # Verify JSON content
        uploaded_data = json.loads(kwargs['Body'])
        assert uploaded_data == test_data


class TestIndexManagement:
    """Test index.json management functionality."""

    @patch('model_processor.s3_client')
    def test_update_index_creates_new_index(self, mock_s3_client):
        # Mock S3 client to simulate missing index file
        mock_s3_client.exceptions.NoSuchKey = Exception
        mock_s3_client.get_object.side_effect = Exception("NoSuchKey")
        
        test_file_data = {
            'metadata': {
                'model_type': 'markov_chain',
                'column_count': 2,
                'row_count': 10
            },
            'markov_models': [{'test': 'model'}, {'test': 'model2'}]
        }
        
        model_processor.update_index('test-bucket', 'index.json', 'test.json', test_file_data)
        
        # Verify put_object was called to create new index
        mock_s3_client.put_object.assert_called_once()
        args, kwargs = mock_s3_client.put_object.call_args
        uploaded_index = json.loads(kwargs['Body'])
        
        assert uploaded_index['total_files'] == 1
        assert len(uploaded_index['files']) == 1
        assert uploaded_index['files'][0]['path'] == 'test.json'
        assert uploaded_index['files'][0]['model_count'] == 2

    @patch('model_processor.s3_client')
    def test_update_index_updates_existing_index(self, mock_s3_client):
        # Mock existing index
        existing_index = {
            'files': [{'path': 'old.json', 'model_count': 1}],
            'total_files': 1,
            'last_updated': 'old-request-id'
        }
        
        mock_s3_client.get_object.return_value = {
            'Body': MagicMock(read=MagicMock(return_value=json.dumps(existing_index).encode()))
        }
        
        test_file_data = {
            'metadata': {
                'model_type': 'markov_chain',
                'column_count': 3,
                'row_count': 15
            },
            'markov_models': [{'test': 'model'}]
        }
        
        model_processor.update_index('test-bucket', 'index.json', 'new.json', test_file_data)
        
        # Verify index was updated
        mock_s3_client.put_object.assert_called_once()
        args, kwargs = mock_s3_client.put_object.call_args
        uploaded_index = json.loads(kwargs['Body'])
        
        assert uploaded_index['total_files'] == 2
        assert len(uploaded_index['files']) == 2


class TestLambdaHandler:
    """Test the main Lambda handler function."""

    @patch('model_processor.update_index')
    @patch('model_processor.upload_json')
    @patch('model_processor.process_csv')
    @patch('model_processor.download_file')
    @patch.dict('os.environ', {
        'BUCKET_NAME': 'test-bucket',
        'INDEX_FILE': 'index.json'
    })
    def test_lambda_handler_processes_csv_files(
        self, mock_download, mock_process, mock_upload, mock_update_index, 
        sample_s3_event, sample_context
    ):
        # Setup mocks
        mock_download.return_value = "test,csv,content"
        mock_markov_data = {
            'metadata': {'model_type': 'markov_chain'},
            'markov_models': [{'test': 'model'}]
        }
        mock_process.return_value = mock_markov_data
        
        # Call handler
        result = model_processor.lambda_handler(sample_s3_event, sample_context)
        
        # Verify success response
        assert result['statusCode'] == 200
        assert '1 files' in result['body']
        
        # Verify function calls
        mock_download.assert_called_once_with('test-bucket', 'test-file.csv')
        mock_process.assert_called_once_with("test,csv,content", 'test-file.csv')
        mock_upload.assert_called_once_with('test-bucket', 'test-file.json', mock_markov_data)
        mock_update_index.assert_called_once_with('test-bucket', 'index.json', 'test-file.json', mock_markov_data)

    @patch('model_processor.download_file')
    @patch.dict('os.environ', {
        'BUCKET_NAME': 'test-bucket',
        'INDEX_FILE': 'index.json'
    })
    def test_lambda_handler_skips_non_csv_files(self, mock_download, sample_context):
        # Event with non-CSV file
        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': 'test-bucket'},
                        'object': {'key': 'test-file.txt'}
                    }
                }
            ]
        }
        
        result = model_processor.lambda_handler(event, sample_context)
        
        # Verify file was skipped
        assert result['statusCode'] == 200
        mock_download.assert_not_called()

    @patch('model_processor.download_file')
    @patch.dict('os.environ', {
        'BUCKET_NAME': 'test-bucket',
        'INDEX_FILE': 'index.json'
    })
    def test_lambda_handler_handles_exceptions(self, mock_download, sample_s3_event, sample_context):
        # Setup mock to raise exception
        mock_download.side_effect = Exception("Test error")
        
        with pytest.raises(Exception, match="Test error"):
            model_processor.lambda_handler(sample_s3_event, sample_context)