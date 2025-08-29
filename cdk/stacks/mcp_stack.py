import os
import json
from aws_cdk import (
    Stack,
    CfnOutput,
    Tags
)
from constructs import Construct

from custom_constructs.mcp_server_construct import McpServerConstruct


class McpStack(Stack):
    """
    Stack for the MCP (Model Context Protocol) server infrastructure.
    Includes Lambda functions, API Gateway, authentication, and custom domain.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Load configuration from config.json
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Get MCP configuration (fallback to root level for backward compatibility)
            mcp_config = config.get('mcp', config)
            domain_name = mcp_config.get('domain')
            certificate_domain = mcp_config.get('certificateDomain', domain_name)
            
            if not domain_name:
                raise ValueError("mcp.domain is required in config.json")
                
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
            raise ValueError(f"Missing or invalid config.json for MCP server. Error: {e}")

        # Create the MCP server construct
        self.mcp_server = McpServerConstruct(
            self, "McpServer",
            domain_name=domain_name,
            certificate_domain=certificate_domain
        )

        # Apply stack-level tags
        Tags.of(self).add("Project", "igg")
        Tags.of(self).add("CDK", "true")
        Tags.of(self).add("Environment", "prod")
        Tags.of(self).add("Stack", "MCP")

        # Output important values
        CfnOutput(
            self, "McpDomainTarget",
            value=self.mcp_server.domain_target,
            description=f"CNAME target for your DNS record (point {domain_name} to this)"
        )

        CfnOutput(
            self, "McpCustomDomainUrl",
            value=f"https://{domain_name}",
            description="MCP custom domain endpoint URL (after DNS setup)"
        )

        CfnOutput(
            self, "McpApiGatewayUrl",
            value=self.mcp_server.api_url,
            description="MCP API Gateway default endpoint URL"
        )

        CfnOutput(
            self, "McpAuthSecretArn",
            value=self.mcp_server.auth_secret_arn,
            description="ARN of the auth secret in AWS Secrets Manager"
        )
