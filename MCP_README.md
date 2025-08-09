# IGG MCP Server

An MCP (Model Context Protocol) server that provides creative text generation using Markov chain models from the IGG (Idea Generator Generator) project.

## Features

The MCP server exposes three tools for creative text generation:

### 1. `list_models`
Lists available Markov models from the web endpoint.

**Returns:**
- Available models from the server
- Locally cached models  
- Model counts and metadata

### 2. `generate_ideas`
Generate creative text ideas using a specific model.

**Parameters:**
- `model_name` (string): Name of the model to use (e.g., "samples/sample.json")
- `count` (integer, optional): Number of ideas to generate (default: 5, max: 50)

**Example Usage:**
```json
{
  "model_name": "samples/sample.json",
  "count": 3
}
```

### 3. `generate_with_template`
Generate ideas using a template with placeholders.

**Parameters:**
- `model_name` (string): Name of the model to use
- `template` (string): Template with placeholders like "A $1 for $2 people"  
- `count` (integer, optional): Number of ideas to generate (default: 5, max: 50)

**Example Usage:**
```json
{
  "model_name": "samples/sample.json", 
  "template": "Try our $1 solution for $2 professionals",
  "count": 3
}
```

## Setup

1. **Install dependencies:**
   ```bash
   pipenv install
   ```

2. **Set base URL (optional):**
   Set the `IGG_BASE_URL` environment variable to override the default endpoint:
   ```bash
   export IGG_BASE_URL="https://your-domain.com"
   ```

3. **Run the MCP server:**
   ```bash
   pipenv run python src/mcp_server.py
   ```

## Testing

Run the test suite to verify functionality:
```bash
pipenv run python test_mcp.py
```

## Integration

To use this MCP server with Claude Code or other MCP clients, configure your client to connect to the server using stdio transport.

### Example MCP Client Configuration

Add to your MCP client configuration:
```json
{
  "mcpServers": {
    "igg-markov": {
      "command": "pipenv",
      "args": ["run", "python", "src/mcp_server.py"],
      "cwd": "/path/to/igg"
    }
  }
}
```

## Model Caching

Models are automatically downloaded and cached locally in `models/cache/` on first use. This improves performance for subsequent requests.

## Architecture

- `src/mcp_server.py`: Main MCP server entry point
- `src/mcp_markov_models.py`: Core Markov chain logic and model handling
- `src/generate_markov_models.py`: Shared utilities (unchanged from original IGG)

The server maintains compatibility with the original IGG web frontend by using the same model format and endpoints.
