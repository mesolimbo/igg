from aws_cdk import (
    aws_s3 as s3,
    aws_apigateway as apigateway,
    aws_certificatemanager as acm,
    aws_iam as iam,
    RemovalPolicy,
    Tags
)
from constructs import Construct


class StaticSiteConstruct(Construct):
    """
    A construct that creates an S3 bucket served through API Gateway as a static website.
    Supports arbitrary path structures and serves files directly from S3.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        domain_name: str,
        certificate_arn: str,
        bucket_name: str = None,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create S3 bucket for static content
        self.bucket = s3.Bucket(
            self,
            "StaticSiteBucket",
            bucket_name=bucket_name,
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN,
            public_read_access=False,  # Access via API Gateway only
        )

        # Create IAM role for API Gateway to access S3
        self.api_gateway_role = iam.Role(
            self,
            "ApiGatewayS3Role",
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
            inline_policies={
                "S3Access": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["s3:GetObject"],
                            resources=[f"{self.bucket.bucket_arn}/*"]
                        )
                    ]
                )
            }
        )

        # Create custom domain for API Gateway
        self.custom_domain = apigateway.DomainName(
            self,
            "StaticSiteDomain",
            domain_name=domain_name,
            certificate=acm.Certificate.from_certificate_arn(
                self, "ImportedCertificate", certificate_arn
            ),
            endpoint_type=apigateway.EndpointType.REGIONAL,
            security_policy=apigateway.SecurityPolicy.TLS_1_2
        )

        # Create API Gateway for serving S3 content
        self.api = apigateway.RestApi(
            self,
            "StaticSiteApi",
            rest_api_name=f"Static Site API - {domain_name}",
            description=f"API Gateway serving S3 static content for {domain_name}",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=["GET", "HEAD", "OPTIONS"],
                allow_headers=["Content-Type", "Authorization"]
            )
        )

        # Create proxy resource for handling all paths
        proxy_resource = self.api.root.add_resource("{proxy+}")
        
        # S3 integration for proxy paths
        s3_integration = apigateway.AwsIntegration(
            service="s3",
            integration_http_method="GET",
            path=f"{self.bucket.bucket_name}/{{proxy}}",
            options=apigateway.IntegrationOptions(
                credentials_role=self.api_gateway_role,
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code="200",
                        response_parameters={
                            "method.response.header.Content-Type": "integration.response.header.Content-Type",
                            "method.response.header.Content-Length": "integration.response.header.Content-Length",
                        }
                    ),
                    apigateway.IntegrationResponse(
                        status_code="404",
                        selection_pattern="403"  # S3 returns 403 for missing objects
                    )
                ],
                request_parameters={
                    "integration.request.path.proxy": "method.request.path.proxy"
                }
            )
        )

        # Add GET method to proxy resource
        proxy_resource.add_method(
            "GET",
            s3_integration,
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Content-Type": True,
                        "method.response.header.Content-Length": True,
                    }
                ),
                apigateway.MethodResponse(status_code="404")
            ],
            request_parameters={
                "method.request.path.proxy": True
            }
        )

        # Handle root path (/) - serve index.html by default
        root_integration = apigateway.AwsIntegration(
            service="s3",
            integration_http_method="GET",
            path=f"{self.bucket.bucket_name}/index.html",
            options=apigateway.IntegrationOptions(
                credentials_role=self.api_gateway_role,
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code="200",
                        response_parameters={
                            "method.response.header.Content-Type": "integration.response.header.Content-Type",
                            "method.response.header.Content-Length": "integration.response.header.Content-Length",
                        }
                    ),
                    apigateway.IntegrationResponse(
                        status_code="404",
                        selection_pattern="403"
                    )
                ]
            )
        )

        # Add GET method to root
        self.api.root.add_method(
            "GET",
            root_integration,
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Content-Type": True,
                        "method.response.header.Content-Length": True,
                    }
                ),
                apigateway.MethodResponse(status_code="404")
            ]
        )

        # Connect custom domain to API
        self.custom_domain.add_base_path_mapping(self.api, base_path="")

        # Apply tags
        Tags.of(self).add("Component", "StaticSite")

    @property
    def bucket_name(self) -> str:
        """Returns the S3 bucket name."""
        return self.bucket.bucket_name

    @property
    def api_url(self) -> str:
        """Returns the API Gateway URL."""
        return self.api.url

    @property
    def domain_target(self) -> str:
        """Returns the domain target for CNAME configuration."""
        return self.custom_domain.domain_name_alias_domain_name
