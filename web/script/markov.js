// Utility function for weighted random choice
function weightedRandomChoice(items, weights) {
    const cumulativeWeights = [];
    for (let i = 0; i < weights.length; i++) {
        cumulativeWeights[i] = weights[i] + (cumulativeWeights[i - 1] || 0);
    }
    const random = Math.random() * cumulativeWeights[cumulativeWeights.length - 1];
    for (let i = 0; i < cumulativeWeights.length; i++) {
        if (random <= cumulativeWeights[i]) {
            return items[i];
        }
    }
}

// Function to sample the target phrase length between 2 and max observed length
function samplePhraseLength(maxLength) {
    // Generate a random integer between 2 and maxLength (inclusive)
    return Math.floor(Math.random() * (maxLength - 1)) + 2;
}

// Function to select the start word
function selectStartWord(startWordsProb) {
    const startWords = Object.keys(startWordsProb);
    const startWeights = Object.values(startWordsProb);
    return weightedRandomChoice(startWords, startWeights);
}

// Function to select the next word based on the current word or randomly (5% chance)
function selectNextWord(currentWord, transitions, vocabulary) {
    const randomChance = Math.random();
    if (randomChance < 0.05) { // 5% chance
        // Pick a random word from the vocabulary
        return selectRandomWord(vocabulary);
    } else {
        const nextWordsProb = transitions[currentWord];
        if (!nextWordsProb) {
            return null;
        }
        const nextWords = Object.keys(nextWordsProb);
        const nextWeights = Object.values(nextWordsProb);
        return weightedRandomChoice(nextWords, nextWeights);
    }
}

// Function to check if a word is an end word
function isEndWord(word, endWords) {
    return endWords.hasOwnProperty(word);
}

// Function to select a random end word
function selectRandomEndWord(endWordsProb) {
    const endWords = Object.keys(endWordsProb);
    const endWeights = Object.values(endWordsProb);
    return weightedRandomChoice(endWords, endWeights);
}

// Function to select a random word from the vocabulary
function selectRandomWord(vocabulary) {
    const words = Array.from(vocabulary);
    const randomIndex = Math.floor(Math.random() * words.length);
    return words[randomIndex];
}

// Main function to generate a phrase from a model
function generatePhrase(model) {
    const { transitions, start_words, end_words, lengths } = model;

    // Determine max observed length from lengths
    const maxLength = Math.max(...Object.keys(lengths).map(Number));
    const targetLength = samplePhraseLength(maxLength);

    let currentWord = selectStartWord(start_words);
    const phrase = [currentWord];

    // Build a vocabulary set from transitions, start_words, and end_words
    const vocabulary = new Set(
        Object.keys(transitions)
            .concat(...Object.keys(end_words))
            .concat(...Object.keys(start_words))
    );

    const maxAttempts = 1000;
    let attempts = 0;

    while (attempts < maxAttempts) {
        attempts++;

        // Attempt to select the next word
        const nextWord = selectNextWord(currentWord, transitions, vocabulary);
        if (!nextWord) {
            break; // No transitions from current word
        }

        phrase.push(nextWord);
        currentWord = nextWord;

        // Check if we've reached or exceeded the target length
        if (phrase.length >= targetLength) {
            if (isEndWord(currentWord, end_words)) {
                break; // Current word is an end word; phrase is complete
            }
        }
    }

    // Ensure the last word is an end word
    if (!isEndWord(currentWord, end_words)) {
        // Try to find an end word from current transitions
        const possibleEndWords = Object.keys(transitions[currentWord] || {}).filter(word => isEndWord(word, end_words));
        if (possibleEndWords.length > 0) {
            // Select an end word from possible transitions
            const endWordWeights = possibleEndWords.map(word => transitions[currentWord][word]);
            currentWord = weightedRandomChoice(possibleEndWords, endWordWeights);
            phrase.push(currentWord);
        } else {
            // Append a random end word
            const randomEndWord = selectRandomEndWord(end_words);
            phrase.push(randomEndWord);
        }
    }

    return phrase.join(' ');
}

// Function to generate data using the Markov models
function generateData(markovModels) {
    const numberOfRowsToGenerate = 10; // Adjust as needed
    const generatedData = [];

    for (let i = 0; i < numberOfRowsToGenerate; i++) {
        const row = [];

        // Generate a phrase for each column
        for (const model of markovModels) {
            const phrase = generatePhrase(model);
            row.push(`"${phrase}"`); // Quote phrases to handle commas
        }

        // Join the row into a CSV line
        generatedData.push(row.join(','));
    }

    // Output the generated data
    document.getElementById('output').textContent = generatedData.join('\n');
}

