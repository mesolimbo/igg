import os
import json
from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_secretsmanager as secretsmanager,
    aws_certificatemanager as acm,
    RemovalPolicy,
    CfnOutput,
    Tags
)
from constructs import Construct


class IggStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Load configuration from config.json
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            domain_name = config['domain']
            certificate_domain = config['certificateDomain']
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
            raise ValueError(f"Missing or invalid config.json. Copy config.json.example to config.json and configure your domain. Error: {e}")

        # Create a secret for basic auth token
        auth_secret = secretsmanager.Secret(
            self, "IggAuthSecret",
            description="Basic auth token for IGG MCP server",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "admin"}',
                generate_string_key="password",
                exclude_characters=' "\\/@'
            ),
            removal_policy=RemovalPolicy.DESTROY
        )

        # Create the Lambda function
        lambda_function = lambda_.Function(
            self, "IggMcpFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="lambda_handler.lambda_handler",
            code=lambda_.Code.from_asset("../src"),
            timeout=Duration.seconds(30),
            environment={
                "AUTH_SECRET_ARN": auth_secret.secret_arn
            }
        )

        # Create the Lambda authorizer function
        authorizer_function = lambda_.Function(
            self, "IggAuthorizerFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="authorizer.lambda_handler",
            code=lambda_.Code.from_asset("../src"),
            timeout=Duration.seconds(10),
            environment={
                "AUTH_SECRET_ARN": auth_secret.secret_arn
            }
        )

        # Grant both Lambda functions permission to read the secret
        auth_secret.grant_read(lambda_function)
        auth_secret.grant_read(authorizer_function)

        # Create SSL certificate with DNS validation
        certificate = acm.Certificate(
            self, "McpIggCertificate",
            domain_name=certificate_domain,
            validation=acm.CertificateValidation.from_dns()
        )

        # Create custom domain for API Gateway
        custom_domain = apigateway.DomainName(
            self, "McpIggDomain",
            domain_name=domain_name,
            certificate=certificate,
            endpoint_type=apigateway.EndpointType.EDGE,
            security_policy=apigateway.SecurityPolicy.TLS_1_2
        )

        # Create Lambda authorizer
        auth = apigateway.RequestAuthorizer(
            self, "IggBasicAuthorizer",
            handler=authorizer_function,
            identity_sources=[apigateway.IdentitySource.header('Authorization')],
            authorizer_name="BasicAuthAuthorizer",
            results_cache_ttl=Duration.seconds(300)  # Cache for 5 minutes
        )

        # Create API Gateway
        api = apigateway.RestApi(
            self, "IggMcpApi",
            rest_api_name="IGG MCP Server API",
            description="API Gateway for IGG MCP Server",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"]
            )
        )

        # Create the API Gateway integration
        lambda_integration = apigateway.LambdaIntegration(lambda_function)

        # Add methods with authorization required
        api.root.add_method("POST", lambda_integration, authorizer=auth)
        api.root.add_method("GET", lambda_integration, authorizer=auth)

        # Connect the custom domain to the API
        custom_domain.add_base_path_mapping(
            api,
            base_path=""
        )

        # Output the domain target and URLs
        CfnOutput(
            self, "DomainTarget",
            value=custom_domain.domain_name_alias_domain_name,
            description=f"CNAME target for your DNS record (point {domain_name} to this)"
        )

        CfnOutput(
            self, "CustomDomainUrl",
            value=f"https://{domain_name}",
            description="Custom domain endpoint URL (after DNS setup)"
        )

        CfnOutput(
            self, "ApiGatewayUrl",
            value=api.url,
            description="API Gateway default endpoint URL"
        )

        CfnOutput(
            self, "AuthSecretArn",
            value=auth_secret.secret_arn,
            description="ARN of the auth secret in AWS Secrets Manager"
        )

        # Apply tags to all resources in this stack
        Tags.of(self).add("Project", "igg")
        Tags.of(self).add("CDK", "true")
        Tags.of(self).add("Environment", "prod")
