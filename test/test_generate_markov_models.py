import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from collections import Counter, defaultdict

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import generate_markov_models

@pytest.fixture
def sample_dataframe():
    data = {
        0: ["Hello world", "Test phrase", "Another example"],
        1: ["Sample text", "More data", "Final entry"]
    }
    return pd.DataFrame(data)

def test_preprocess_text_removes_non_alphanumeric():
    text = "Hello, world! 1-2-3"
    result = generate_markov_models.preprocess_text(text)
    assert result == "Hello world 123"

def test_preprocess_text_replaces_multiple_spaces():
    text = "Hello   world"
    result = generate_markov_models.preprocess_text(text)
    assert result == "Hello world"

def test_extract_columns_creates_markov_models(sample_dataframe):
    result = generate_markov_models.extract_columns(sample_dataframe)
    assert len(result) == 2
    assert all('column_index' in model for model in result)
    assert all('transitions' in model for model in result)
    assert all('start_words' in model for model in result)
    assert all('end_words' in model for model in result)
    assert all('lengths' in model for model in result)

def test_extract_phrases_creates_transitions():
    phrases = ["Hello world", "Hello there", "world peace"]
    transitions = defaultdict(Counter)
    start_words = Counter()
    end_words = Counter()
    lengths = []
    generate_markov_models.extract_phrases(end_words, lengths, phrases, start_words, transitions)
    assert start_words["Hello"] == 2
    assert end_words["world"] == 1
    assert transitions["Hello"]["world"] == 1
    assert transitions["Hello"]["there"] == 1

@patch('generate_markov_models.nltk.download')
@patch('generate_markov_models.pd.read_csv')
@patch('generate_markov_models.json.dump')
@patch('generate_markov_models.open', new_callable=MagicMock)
def test_generate_creates_json(mock_open, mock_json_dump, mock_read_csv, mock_nltk_download, sample_dataframe):
    mock_read_csv.return_value = sample_dataframe
    generate_markov_models.generate('input.csv', 'output.json')
    mock_read_csv.assert_called_once_with('input.csv', header=None)
    mock_json_dump.assert_called_once()
    mock_open.assert_called_once_with('output.json', 'w')
