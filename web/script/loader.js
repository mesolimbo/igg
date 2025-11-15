/*
 *  WARNING: This script expects a global variable named `baseUrl` to be defined, pointing
 *  to the URL where the Markov models are hosted. You can set it in an unversioned file
 *  named /web/script/base.js, which should be included before this script.
 */
const modelSelect = document.getElementById('model-select');
const generateButton = document.getElementById('generate-button');
const templateInput = document.getElementById('template-input');
const modelCache = {}; // Object to store cached models

// Fetch the list of available models and populate the dropdown
fetch(`${baseUrl}/index.json`)
    .then(response => response.json())
    .then(data => {
        const models = data.models;
        console.log('Fetched models:', models);
        if (Array.isArray(models)) {
            // Populate the dropdown with models
            models.forEach(modelPath => {
                const option = document.createElement('option');
                option.value = `${baseUrl}/${modelPath}`;
                option.textContent = modelPath;
                modelSelect.appendChild(option);
            });

            // Initialize the select element after options are added
            var elems = document.querySelectorAll('select');
            var instances = M.FormSelect.init(elems);
        } else {
            console.error('Error: Expected an array of models');
        }
    })
    .catch(error => console.error('Error loading model list:', error));

// Event listener for the generate button
generateButton.addEventListener('click', () => {
    const modelUrl = modelSelect.value;

    // Check if the model is already in the cache
    if (modelCache[modelUrl]) {
        console.log('Using cached model:', modelUrl);
        generateData(modelCache[modelUrl]);
    } else {
        // Fetch the Markov models from the selected JSON file or API endpoint
        fetch(modelUrl)
            .then(response => response.json())
            .then(markovModels => {
                // Store the fetched model in the cache
                modelCache[modelUrl] = markovModels;
                generateData(markovModels);
            })
            .catch(error => console.error('Error loading Markov models:', error));
    }
});

// Escape RegExp special characters for literal matching
function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
// Function to generate data using the Markov models
function generateData(markovModels) {
    const numberOfRowsToGenerate = 10; // Adjust as needed
    const generatedData = [];
    // Escape templateInput.value to prevent HTML injection
    function escapeHTML(str) {
        return str.replace(/[<>&"']/g, function (c) {
            return ({
                '<': '&lt;',
                '>': '&gt;',
                '&': '&amp;',
                '"': '&quot;',
                "'": '&#39;'
            })[c];
        });
    }
    const templateRaw = templateInput.value;
    const template =
        templateRaw
            ? escapeHTML(templateRaw)
            : markovModels.map((_, index) => `$${index + 1}`).join(' ');

    for (let i = 0; i < numberOfRowsToGenerate; i++) {
        const row = [];

        // Generate a phrase for each column
        for (const model of markovModels) {
            const phrase = generatePhrase(model);
            row.push(phrase);
        }

        // Fill the template with generated phrases
        let filledTemplate = template;
        if (templateInput.value) {
            row.forEach((phrase, index) => {
                const placeholder = `$${index + 1}`;
                // Escape phrase to prevent HTML injection inside <b>
                const escapedPhrase = phrase.replace(/[<>&"']/g, function (c) {
                    return ({
                        '<': '&lt;',
                        '>': '&gt;',
                        '&': '&amp;',
                        '"': '&quot;',
                        "'": '&#39;'
                    })[c];
                });
                // The template itself is escaped; only placeholders are replaced with HTML
                // To replace **ALL** placeholder instances, use a global regex
                filledTemplate = filledTemplate.replace(new RegExp(escapeRegExp(placeholder), 'g'), `<b>${escapedPhrase}</b>`);
            });
        } else {
            filledTemplate = row.join(' ');
        }

        generatedData.push(filledTemplate);
    }

    // Escape the text and replace line breaks with <br />
    const outputElement = document.getElementById('output');
    outputElement.innerHTML = '';
    generatedData.forEach(line => {
        // Create paragraph element and set its innerHTML to render HTML tags
        const p = document.createElement('p');
        p.innerHTML = line;
        outputElement.appendChild(p);
    });
}

document.addEventListener('DOMContentLoaded', function() {
    var elems = document.querySelectorAll('select');
    var instances = M.FormSelect.init(elems);
});
