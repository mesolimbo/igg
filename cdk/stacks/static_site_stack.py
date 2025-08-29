import os
import json
from aws_cdk import (
    Stack,
    CfnOutput,
    Tags
)
from constructs import Construct

from custom_constructs.static_site_construct import StaticSiteConstruct
from custom_constructs.model_processor_construct import ModelProcessorConstruct


class StaticSiteStack(Stack):
    """
    Stack for the static site infrastructure.
    Includes S3 bucket, API Gateway integration, and CSV processing Lambda.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Load configuration from config.json
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Get static site configuration
            static_config = config.get('static_site', {})
            domain_name = static_config.get('domain')
            certificate_arn = static_config.get('certificate_arn')
            bucket_name = static_config.get('bucket_name')
            
            if not certificate_arn or not domain_name or not bucket_name:
                raise ValueError("static_site.certificate_arn, static_site.domain, and static_site.bucket_name are required in config.json")
                
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
            raise ValueError(f"Missing or invalid config.json for static site. Error: {e}")

        # Create the static site construct
        self.static_site = StaticSiteConstruct(
            self, "StaticSite",
            domain_name=domain_name,
            certificate_arn=certificate_arn,
            bucket_name=bucket_name
        )

        # Create the model processor for CSV → JSON processing
        self.model_processor = ModelProcessorConstruct(
            self, "ModelProcessor",
            bucket=self.static_site.bucket
        )

        # Apply stack-level tags
        Tags.of(self).add("Project", "igg")
        Tags.of(self).add("CDK", "true")
        Tags.of(self).add("Environment", "prod")
        Tags.of(self).add("Stack", "StaticSite")

        # Output important values
        CfnOutput(
            self, "StaticSiteDomainTarget",
            value=self.static_site.domain_target,
            description=f"CNAME target for your DNS record (point {domain_name} to this)"
        )

        CfnOutput(
            self, "StaticSiteUrl",
            value=f"https://{domain_name}",
            description="Static site URL (after DNS setup)"
        )

        CfnOutput(
            self, "ApiGatewayUrl",
            value=self.static_site.api_url,
            description="API Gateway default endpoint URL"
        )

        CfnOutput(
            self, "S3BucketName",
            value=self.static_site.bucket_name,
            description="S3 bucket name for static content"
        )

        CfnOutput(
            self, "ModelProcessorFunctionArn",
            value=self.model_processor.function_arn,
            description="ARN of the CSV processing Lambda function"
        )
