# IGG MCP Server - AWS CDK Deployment

This directory contains AWS CDK configuration to deploy the IGG MCP Server as a minimalistic Lambda stack with API Gateway.

## Features

- **Lambda Function**: Hosts the MCP server with async request handling
- **API Gateway**: REST API endpoint with CORS support
- **Basic Authentication**: Secure access using AWS Secrets Manager
- **Minimalistic Stack**: Only essential AWS resources

## Prerequisites

1. AWS CLI configured with appropriate credentials
2. AWS CDK installed (`npm install -g aws-cdk`)
3. Python 3.11 or later

## Deployment Steps

1. **Configure your domain**:
   ```bash
   cd cdk
   cp config.json.example config.json
   # Edit config.json with your domain details
   ```

2. **Install CDK dependencies**:
   ```bash
   pipenv install
   ```

3. **Bootstrap CDK (first time only)**:
   ```bash
   pipenv run cdk bootstrap
   ```

4. **Deploy the stack**:
   ```bash
   pipenv run cdk deploy
   ```

5. **Validate SSL certificate with DNS**:
   After deployment starts, AWS will provide DNS validation records. You'll need to add a TXT record in your DNS provider:
   - Check the ACM console or CloudFormation events for the validation record details
   - Add the TXT record with the provided name and value
   - This typically looks like `_amazondomainvalidationrecord.your-subdomain.your-domain.com`

6. **Set up DNS record**:
   Once the certificate is validated, create a CNAME record for your subdomain:
   - **Host**: your subdomain (e.g., `api`)
   - **Value**: `<DOMAIN_TARGET_FROM_OUTPUT>` (the AWS domain name from stack output)

7. **Get the authentication credentials**:
   After deployment, retrieve the generated password from AWS Secrets Manager:
   ```bash
   aws secretsmanager get-secret-value --secret-id <AUTH_SECRET_ARN_FROM_OUTPUT>
   ```

## Stack Resources

- **Lambda Function**: `IggMcpFunction` - Handles MCP requests
- **API Gateway**: `IggMcpApi` - REST API with POST/GET endpoints
- **Secrets Manager**: `IggAuthSecret` - Stores basic auth credentials
- **IAM Roles**: Minimal permissions for Lambda and Secrets Manager

## Authentication

The stack creates a basic auth setup:
- **Username**: `admin`
- **Password**: Auto-generated and stored in AWS Secrets Manager

To authenticate requests, use the HTTP Basic Authentication header:
```
Authorization: Basic <base64(admin:password)>
```

## API Endpoints

- `GET /`: Returns service information
- `POST /`: MCP protocol requests (requires authentication)
- `OPTIONS /`: CORS preflight (public)

## Usage Example

```bash
# Get service info (replace with your domain)
curl https://your-subdomain.your-domain.com/

# Call MCP tool (replace with actual credentials and domain)
curl -X POST https://your-subdomain.your-domain.com/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic YWRtaW46eW91ci1wYXNzd29yZA==" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_models","arguments":{}}}'
```

## Cost Optimization

This stack is designed for minimal cost:
- Lambda function runs only when called
- API Gateway charges per request
- Secrets Manager has a minimal monthly fee
- No persistent compute or storage resources

## Cleanup

To remove all resources:
```bash
pipenv run cdk destroy
```

## Security Notes

- Auth token is securely generated and stored in AWS Secrets Manager
- Lambda function has minimal IAM permissions
- API Gateway includes CORS headers for web client compatibility
- All communications use HTTPS
