from __future__ import annotations

import json
import re  # Import the regex module
import sys

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from _typeshed import SupportsWrite
from collections import defaultdict, Counter

import pandas as pd
import nltk


# Function to normalize counts to probabilities
def normalize(counter):
    total = sum(counter.values())
    return {k: v / total for k, v in counter.items()}

# Function to preprocess text
def preprocess_text(text):
    # Remove non-alphanumeric characters (keep letters and numbers)
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    # Strip leading and trailing whitespace
    text = text.strip()

    return text


def extract_columns(df):
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


def extract_phrases(end_words, lengths, phrases, start_words, transitions):
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


def generate(in_file, out_file):
    # Set the NLTK data path to /tmp
    nltk.data.path.append("/tmp")
    nltk.download('punkt', download_dir='/tmp', quiet=True)
    nltk.download('punkt_tab', download_dir='/tmp', quiet=True)

    # Read the CSV file into a DataFrame
    df = pd.read_csv(in_file, header=None)  # Update the filename as needed

    markov_models = extract_columns(df)

    # Save the Markov models to JSON
    f: SupportsWrite[str]
    with open(out_file, 'w') as f:
        json.dump(markov_models, f, indent=4)


if __name__ == '__main__':
    # The first command-line param is the input file
    generate(sys.argv[1], sys.argv[2])
