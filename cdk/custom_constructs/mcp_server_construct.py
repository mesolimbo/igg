from aws_cdk import (
    Duration,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_secretsmanager as secretsmanager,
    aws_certificatemanager as acm,
    aws_iam as iam,
    RemovalPolicy,
    CustomResource,
    custom_resources as cr,
    Tags
)
from constructs import Construct


class McpServerConstruct(Construct):
    """
    A construct that creates an MCP (Model Context Protocol) server with:
    - Lambda functions for MCP server and authorization
    - API Gateway with custom authorizer
    - Secrets Manager for authentication
    - Custom domain with SSL certificate
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        domain_name: str,
        certificate_domain: str,
        source_code_path: str = "../src",
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a secret for basic auth token
        self.auth_secret = secretsmanager.Secret(
            self, "McpAuthSecret",
            description="Basic auth token for MCP server",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "admin"}',
                generate_string_key="password",
                exclude_characters=' "\\/@'
            ),
            removal_policy=RemovalPolicy.DESTROY
        )

        # Create the main MCP Lambda function
        self.mcp_function = lambda_.Function(
            self, "McpFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="lambda_handler.lambda_handler",
            code=lambda_.Code.from_asset(source_code_path),
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                "AUTH_SECRET_ARN": self.auth_secret.secret_arn
            }
        )

        # Create the Lambda authorizer function
        self.authorizer_function = lambda_.Function(
            self, "McpAuthorizerFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="authorizer.lambda_handler",
            code=lambda_.Code.from_asset(source_code_path),
            timeout=Duration.seconds(10),
            environment={
                "AUTH_SECRET_ARN": self.auth_secret.secret_arn
            }
        )

        # Grant both Lambda functions permission to read the secret
        self.auth_secret.grant_read(self.mcp_function)
        self.auth_secret.grant_read(self.authorizer_function)

        # Create cross-region certificate (Edge requires us-east-1)
        self.certificate_arn = self._create_certificate(certificate_domain)

        # Create custom domain for API Gateway
        self.custom_domain = apigateway.DomainName(
            self, "McpDomain",
            domain_name=domain_name,
            certificate=acm.Certificate.from_certificate_arn(
                self, "ImportedCertificate", 
                self.certificate_arn
            ),
            endpoint_type=apigateway.EndpointType.EDGE,
            security_policy=apigateway.SecurityPolicy.TLS_1_2
        )

        # Create Lambda authorizer
        self.auth = apigateway.TokenAuthorizer(
            self, "McpBasicAuthorizer",
            handler=self.authorizer_function,
            authorizer_name="BasicAuthAuthorizer",
            results_cache_ttl=Duration.seconds(300)
        )

        # Create API Gateway
        self.api = apigateway.RestApi(
            self, "McpApi",
            rest_api_name="MCP Server API",
            description="API Gateway for MCP Server",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"]
            )
        )

        # Create the API Gateway integration
        lambda_integration = apigateway.LambdaIntegration(self.mcp_function)

        # Add methods with authorization required
        self.api.root.add_method("POST", lambda_integration, authorizer=self.auth)
        self.api.root.add_method("GET", lambda_integration, authorizer=self.auth)

        # Connect the custom domain to the API
        self.custom_domain.add_base_path_mapping(self.api, base_path="")

        # Apply tags
        Tags.of(self).add("Component", "McpServer")

    def _create_certificate(self, certificate_domain: str) -> str:
        """Create SSL certificate in us-east-1 for API Gateway Edge."""
        certificate_handler = lambda_.Function(
            self, "CertificateHandler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_inline("""
import boto3
import json

def handler(event, context):
    request_type = event['RequestType']
    
    if request_type == 'Create':
        acm_client = boto3.client('acm', region_name='us-east-1')
        response = acm_client.request_certificate(
            DomainName=event['ResourceProperties']['DomainName'],
            ValidationMethod='DNS'
        )
        return {
            'Data': {
                'CertificateArn': response['CertificateArn']
            }
        }
    elif request_type == 'Delete':
        # Certificate deletion will be handled automatically by CloudFormation
        return {}
    else:
        return {}
"""),
            timeout=Duration.minutes(5)
        )
        
        # Add IAM permissions for ACM operations
        certificate_handler.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "acm:RequestCertificate",
                    "acm:DescribeCertificate",
                    "acm:DeleteCertificate"
                ],
                resources=["*"]
            )
        )
        
        certificate_provider = cr.Provider(
            self, "CertificateProvider",
            on_event_handler=certificate_handler
        )
        
        certificate_resource = CustomResource(
            self, "CrossRegionCertificate",
            service_token=certificate_provider.service_token,
            properties={'DomainName': certificate_domain}
        )
        
        return certificate_resource.get_att_string('CertificateArn')

    @property
    def api_url(self) -> str:
        """Returns the API Gateway URL."""
        return self.api.url

    @property
    def domain_target(self) -> str:
        """Returns the domain target for CNAME configuration."""
        return self.custom_domain.domain_name_alias_domain_name

    @property
    def auth_secret_arn(self) -> str:
        """Returns the auth secret ARN."""
        return self.auth_secret.secret_arn
