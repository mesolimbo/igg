# IGG - Idea Generator Generator

## 📚 Overview

The IGG (Idea Generator Generator) project is designed to help users generate creative ideas efficiently.
This project leverages Python and optionally AWS Lambda for backend processing and JavaScript for frontend
interactions.

The frontend code uses Markov chains stored in JSON files to generate new ideas based on the input data and
an optional text template. The backend code can automatically convert CSV files in S3 to Markov chain JSON files
for consumption by the client.

## 🛠️ Project Structure

- **Python**: Used for backend processing in AWS Lambda.
- **Pip**: Used for managing Python dependencies.
- **JavaScript**: Used for frontend interactions.
- **Docker**: Used for building and packaging the project.

## 📂 Directory Layout

- `src/`: Contains the Python source code for the project.
- `test/`: Contains the test cases for the project.
- `scripts/build.sh`: Script to build and package the project.
- `Dockerfile`: Defines the Docker image used the project builder script.
- `dist/`: Directory where the build artifacts for AWS is generated and stored.
- `web/`: Contains the JavaScript source code for the project.

## 🚀 Getting Started

### Prerequisites

- Docker
- Pipenv
- Git Bash (for Windows users)

### Installation

1. **Clone the repository**:
    ```sh
    git clone https://github.com/yourusername/igg.git
    cd igg
    ```

2. **Install dependencies**:
    ```sh
    pipenv install
    ```

3. Deploy the project to a web server. The `index.html` file can be hosted on any web server. The client code expects
   the Markov chain JSON files to be hosted on the server specified by the variable `baseUrl` in `base.js` (which is
   gitignored).

4. You can generate new JSON locally or Optionally, configure the backend project to run on AWS Lambda.
   Recommended set-up:
   - **Runtime**: Python 3.12
   - **Handler**: `lambda_function.lambda_handler`
   - **Memory**: 256 MB
   - **Timeout**: 10 seconds

5. **Build the project for Lambda**:
    ```sh
    scripts/build.sh
    ```
6. The Lambda code is designed to run against an S3 trigger. When CSVs are added to the source bucket,
   the Lambda function will process the files and save a JSON file representing a family of Markov chains.

## 📝 Configuration

- **Custom Domain**: The base URL for the project is set in a non-version file called `base.js`:
    ```javascript
    const baseUrl = 'https://invent.whileyou.work';
    ```

## 📄 License

This project is licensed under an Apache License. See the `LICENSE` file for details.

## 🤝 Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## 📧 Contact

For any inquiries, please use [a discussion thread](https://github.com/mesolimbo/igg/discussions).
