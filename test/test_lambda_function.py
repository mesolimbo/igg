import os
from unittest import TestCase
from unittest.mock import patch, MagicMock

import lambda_function


class TestLambdaFunction(TestCase):
    @patch('lambda_function.boto3.client')
    @patch('lambda_function.process_model')
    @patch('lambda_function.update_index')
    def test_lambda_handler(self, mock_update_index, mock_process_model, mock_boto3_client):
        # Mock the S3 client
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3

        # Mock the event
        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': 'test-bucket'},
                        'object': {'key': 'test.csv'}
                    }
                }
            ]
        }

        # Mock the process_model function to return a model key
        mock_process_model.return_value = 'test.json'

        # Call the lambda_handler function
        lambda_function.lambda_handler(event, None)

        # Assertions
        mock_boto3_client.assert_called_once_with('s3')
        mock_process_model.assert_called_once_with(mock_s3, 'test-bucket', 'test.csv')
        mock_update_index.assert_called_once_with(mock_s3, 'test-bucket', 'test.json')

    @patch('lambda_function.boto3.client')
    @patch('lambda_function.generate_markov_models.generate')
    @patch('lambda_function.open', new_callable=MagicMock)
    def test_process_model(self, _, mock_generate, mock_boto3_client):
        # Mock the S3 client
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3

        # Call the process_model function
        csv_name = 'test.csv'
        csv_path = os.path.join('/tmp', os.path.basename(csv_name))
        json_name = 'test.json'
        json_path = os.path.join('/tmp', os.path.basename(json_name))
        model_key = lambda_function.process_model(mock_s3, 'test-bucket', csv_name)

        # Assertions
        mock_s3.download_file.assert_called_once_with('test-bucket', csv_name, csv_path)
        mock_generate.assert_called_once_with(csv_path, json_path)
        mock_s3.upload_file.assert_called_once_with(json_path, 'test-bucket', json_name)
        self.assertEqual(model_key, json_name)

    @patch('lambda_function.boto3.client')
    @patch('lambda_function.json.load')
    @patch('lambda_function.json.dump')
    @patch('lambda_function.open', new_callable=MagicMock)
    def test_update_index(self, mock_open, mock_json_dump, mock_json_load, mock_boto3_client):
        # Mock the S3 client
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3

        # Mock the json.load and json.dump functions
        mock_json_load.return_value = {'models': []}
        index_name = 'index.json'
        index_path = os.path.join('/tmp', os.path.basename(index_name))

        # Call the update_index function
        lambda_function.update_index(mock_s3, 'test-bucket', 'test.json')

        # Assertions
        mock_s3.download_file.assert_called_once_with('test-bucket', index_name, index_path)
        mock_json_load.assert_called_once()
        mock_json_dump.assert_called_once_with({'models': ['test.json']}, mock_open().__enter__())
        mock_s3.upload_file.assert_called_once_with(index_path, 'test-bucket', index_name)
