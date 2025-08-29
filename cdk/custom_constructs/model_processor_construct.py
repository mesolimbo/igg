from aws_cdk import (
    Duration,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_iam as iam,
    Tags
)
from constructs import Construct
import os


class ModelProcessorConstruct(Construct):
    """
    A construct that creates a Lambda function triggered by S3 uploads.
    Processes CSV files and generates JSON models, maintaining an index.json file.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        bucket: s3.IBucket,
        source_code_path: str = "../src",
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Lambda layer for heavy dependencies (pandas, nltk)
        layer_path = os.path.join(os.path.dirname(__file__), '..', '..', 'lambda-layer')
        dependencies_layer = lambda_.LayerVersion(
            self,
            "ModelProcessorDependencies", 
            code=lambda_.Code.from_asset(layer_path),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="Heavy dependencies for model processing (pandas, nltk)"
        )

        # Create Lambda function for processing CSV files
        self.processor_function = lambda_.Function(
            self,
            "ModelProcessorFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="model_processor.lambda_handler",
            code=lambda_.Code.from_asset(source_code_path),
            layers=[dependencies_layer],
            timeout=Duration.minutes(15),  # CSV processing can take time
            memory_size=1024,  # More memory for CSV processing
            environment={
                "BUCKET_NAME": bucket.bucket_name,
                "INDEX_FILE": "index.json"
            }
        )

        # Grant Lambda permissions to read/write S3 bucket
        bucket.grant_read_write(self.processor_function)

        # Add S3 trigger for CSV files
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.processor_function),
            s3.NotificationKeyFilter(suffix=".csv")
        )

        # Apply tags
        Tags.of(self).add("Component", "ModelProcessor")

    @property
    def function_arn(self) -> str:
        """Returns the Lambda function ARN."""
        return self.processor_function.function_arn

    @property
    def function_name(self) -> str:
        """Returns the Lambda function name."""
        return self.processor_function.function_name
