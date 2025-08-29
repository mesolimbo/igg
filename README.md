# IGG - Idea Generator Generator

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## 📚 Overview

The IGG (Idea Generator Generator) project generates creative ideas using Markov chains trained on CSV data. It provides both a **static web interface** and an **MCP (Model Context Protocol) server** for integration with AI tools like Claude Code.

### Key Features
- 🔄 **Automatic CSV → Markov Model Processing**: Upload CSV files and get trained models
- 🌐 **Static Web Interface**: Browse and generate ideas from models  
- 🔌 **MCP Server Integration**: Use with Claude Code and other AI tools
- ☁️ **AWS CDK Infrastructure**: Fully managed serverless deployment
- 📊 **Model Caching**: Efficient local and remote model storage

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Frontend  │    │   MCP Server    │    │ AWS CDK Stack   │
│                 │    │                 │    │                 │
│ - Static Site   │    │ - Claude Code   │    │ - S3 Buckets    │
│ - Model Browse  │    │ - AI Integration│    │ - API Gateway   │
│ - Idea Gen      │    │ - Local Cache   │    │ - Lambda Funcs  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📂 Project Structure

```
├── src/                          # Python source code
│   ├── mcp_server.py            # MCP server entry point
│   ├── mcp_markov_models.py     # MCP Markov logic  
│   ├── model_processor.py       # Lambda CSV processor
│   └── generate_markov_models.py # Standalone utility
├── cdk/                         # AWS CDK infrastructure
│   ├── app.py                   # CDK application
│   ├── constructs/              # Reusable CDK components
│   │   ├── mcp_server_construct.py
│   │   ├── static_site_construct.py  
│   │   └── model_processor_construct.py
│   └── stacks/                  # CDK stack definitions
│       ├── mcp_stack.py         # MCP server infrastructure
│       └── static_site_stack.py # Static site infrastructure
├── test/                        # Unit tests
├── web/                         # Frontend JavaScript
└── models/cache/                # Local model cache
```

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+** with Pipenv
- **Node.js** and AWS CDK CLI (for infrastructure)
- **AWS CLI** configured (for deployment)

### 1. Local MCP Server Setup

```bash
# Clone and install dependencies
git clone <repository-url>
cd igg
pipenv install

# Run MCP server locally
pipenv run python src/mcp_server.py
```

### 2. MCP Integration with Claude Code

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

### 3. AWS Infrastructure Deployment

```bash
# Build Lambda layer with heavy dependencies (pandas, nltk)
pipenv run python layerator.py

# Configure domains in config.json
cd cdk
cp config.json.example config.json
# Edit config.json with your domains and certificates

# Deploy infrastructure
pipenv run cdk deploy --all

# Set up DNS records as shown in deployment outputs
```

## 🔧 Configuration

### CDK Configuration (`cdk/config.json`)
```json
{
  "mcp": {
    "domain": "mcp.yourdomain.com",
    "certificateDomain": "mcp.yourdomain.com"
  },
  "static_site": {
    "domain": "static.yourdomain.com", 
    "certificate_arn": "arn:aws:acm:...",
    "bucket_name": "your-bucket-name"
  }
}
```

### Environment Variables
- `IGG_BASE_URL`: Override default model endpoint for MCP server
- `BUCKET_NAME`: S3 bucket name (set by CDK)
- `INDEX_FILE`: Index file name (default: `index.json`)

## 🎯 Usage Examples

### MCP Tools Available

#### 1. List Models
```json
{
  "tool": "list_models"
}
```

#### 2. Generate Ideas
```json
{
  "tool": "generate_ideas",
  "arguments": {
    "model_name": "samples/sample.json",
    "count": 5
  }
}
```

#### 3. Template-based Generation  
```json
{
  "tool": "generate_with_template",
  "arguments": {
    "model_name": "samples/sample.json",
    "template": "A $1 solution for $2 professionals",
    "count": 3
  }
}
```

### CSV Processing Workflow

1. **Upload CSV**: Place CSV file in S3 bucket (any path structure)
2. **Auto-Processing**: Lambda automatically converts CSV → Markov JSON
3. **Index Update**: `index.json` updated with model metadata
4. **Access Models**: Available via API Gateway and MCP server

## 🧪 Testing

Run the complete test suite:
```bash
pipenv run pytest test/ -v
```

Test specific modules:
```bash
pipenv run pytest test/test_model_processor.py -v
pipenv run pytest test/test_generate_markov_models.py -v
```

## 🏗️ Development

### Adding New Models
1. Upload CSV data to S3 bucket
2. Models automatically generated and indexed
3. Available immediately via MCP and web interface

### Lambda Layer Management
The model processor uses a Lambda layer for heavy dependencies:

```bash
# Rebuild layer when dependencies change
pipenv run python layerator.py

# Deploy updated layer
pipenv run cdk deploy IggStaticSiteStack
```

### Extending MCP Tools
1. Add new methods to `mcp_markov_models.py`
2. Register tools in `mcp_server.py`
3. Add corresponding tests

### CDK Infrastructure Changes
1. Modify constructs in `cdk/constructs/`
2. Update stack definitions in `cdk/stacks/`
3. Test with `pipenv run cdk diff`
4. Deploy with `pipenv run cdk deploy`

## 📊 Monitoring & Debugging

### CloudWatch Logs
- Lambda function logs: `/aws/lambda/ModelProcessor`
- API Gateway logs: Available in CloudWatch

### Local Debugging
```bash
# Test model processor locally
pipenv run python -c "
import model_processor
result = model_processor.process_csv('col1,col2\nval1,val2', 'test.csv')
print(result)
"
```

## 🔒 Security

- All AWS resources use minimal IAM permissions
- API Gateway secured with custom authorizers (MCP stack)
- HTTPS/TLS 1.2+ enforced on all endpoints
- S3 bucket access restricted to API Gateway
- Authentication secrets managed via AWS Secrets Manager

## 🚢 Deployment

### Environment-specific Deployments
```bash
# Development
pipenv run cdk deploy --context environment=dev

# Production  
pipenv run cdk deploy --context environment=prod
```

### CI/CD Integration
```bash
# Validate infrastructure
pipenv run cdk synth
pipenv run cdk diff

# Deploy specific stacks
pipenv run cdk deploy IggMcpStack
pipenv run cdk deploy IggStaticSiteStack
```

## 🧹 Cleanup

Remove all AWS resources:
```bash
pipenv run cdk destroy --all
```

## 📄 License

This project is licensed under the Apache License 2.0. See the `LICENSE` file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Run tests: `pipenv run pytest`
4. Commit changes: `git commit -m 'Add amazing feature'`
5. Push to branch: `git push origin feature/amazing-feature`
6. Open a Pull Request

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/mesolimbo/igg/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mesolimbo/igg/discussions)
- **Documentation**: See individual component READMEs in subdirectories
