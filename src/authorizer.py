import json
import base64
import os
import boto3
from botocore.exceptions import ClientError


def lambda_handler(event, context):
    """Lambda authorizer for API Gateway basic authentication."""
    
    # Debug logging - log the entire event structure
    print(f"Authorizer event: {json.dumps(event, default=str)}")
    
    try:
        # Extract the authorization token from the event
        # For TokenAuthorizer, it's in event['authorizationToken']
        auth_token = event.get('authorizationToken')
        
        if not auth_token or not auth_token.startswith('Basic '):
            return generate_policy('user', 'Deny', event['methodArn'])
        
        # Get the auth secret from environment
        secret_arn = os.environ.get('AUTH_SECRET_ARN')
        if not secret_arn:
            return generate_policy('user', 'Deny', event['methodArn'])
        
        # Get the secret value from AWS Secrets Manager
        secrets_client = boto3.client('secretsmanager')
        try:
            secret_response = secrets_client.get_secret_value(SecretId=secret_arn)
            secret_data = json.loads(secret_response['SecretString'])
            expected_password = secret_data['password']
        except (ClientError, KeyError, json.JSONDecodeError):
            return generate_policy('user', 'Deny', event['methodArn'])
        
        # Decode and validate the basic auth credentials
        try:
            encoded_credentials = auth_token[6:]  # Remove 'Basic '
            decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
            username, password = decoded_credentials.split(':', 1)
            
            # Validate credentials
            if username == 'admin' and password == expected_password:
                return generate_policy('admin', 'Allow', event['methodArn'])
            else:
                return generate_policy('user', 'Deny', event['methodArn'])
                
        except (ValueError, UnicodeDecodeError):
            return generate_policy('user', 'Deny', event['methodArn'])
            
    except Exception as e:
        print(f"Authorizer error: {str(e)}")
        return generate_policy('user', 'Deny', event['methodArn'])


def generate_policy(principal_id, effect, resource):
    """Generate IAM policy for API Gateway."""
    auth_response = {
        'principalId': principal_id
    }
    
    if effect and resource:
        policy_document = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource
                }
            ]
        }
        auth_response['policyDocument'] = policy_document
    
    return auth_response
