import enum
import logging
from typing import Optional

import boto3
from sagemaker.enums import EndpointType
from sagemaker.huggingface import HuggingFaceModel

from src.settings import settings


class DeploymentService:
    def __init__(self, resource_manager, logger=None):
        """
        Initializes the DeploymentService with necessary dependencies.

        :param resource_manager: Manages resources and configurations for deployments.
        :param settings: Configuration settings for deployment.
        :param logger: Optional logger for logging messages. If None, the standard logging module will be used.
        """
        self.sagemaker_client = boto3.client("sagemaker")
        self.resource_manager = resource_manager
        self.settings = settings
        self.logger = logger if logger else logging.getLogger(__name__)

    def deploy(
        self,
        role_arn: str,
        llm_image: str,
        config: dict,
        endpoint_name: str,
        endpoint_config_name: str,
        gpu_instance_type: str,
        resources: Optional[dict] = None,
        endpoint_type: enum.Enum = EndpointType.MODEL_BASED,
    ):
        """
        Handles the deployment of a model to SageMaker, including checking and creating
        configurations and endpoints as necessary.

        :param role_arn: The ARN of the IAM role for SageMaker to access resources.
        :param llm_image: URI of the Docker image in ECR for the HuggingFace model.
        :param config: Configuration dictionary for the environment variables of the model.
        :param endpoint_name: The name for the SageMaker endpoint.
        :param endpoint_config_name: The name for the SageMaker endpoint configuration.
        :param resources: Optional resources for the model deployment(used for multi model endpoints)
        :param endpoint_type: can be EndpointType.MODEL_BASED (without inference component)
                or EndpointType.INFERENCE_COMPONENT (with inference component)
        :param gpu_instance_type: The instance type for the SageMaker endpoint.
        """
        try:
            # Check if the endpoint configuration exists
            if self.resource_manager.endpoint_config_exists(endpoint_config_name=endpoint_config_name):
                self.logger.info(
                    f"Endpoint configuration {endpoint_config_name} exists. Using existing configuration..."
                )
            else:
                self.logger.info(f"Endpoint configuration{endpoint_config_name} does not exist.")
            # Check if the endpoint already exists
            try:
                self.sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
                endpoint_exists = True
                self.logger.info(f"Endpoint {endpoint_name} already exists. Updating...")
            except self.sagemaker_client.exceptions.ClientError as e:
                if "Could not find endpoint" in str(e):
                    endpoint_exists = False
                    self.logger.info(f"Endpoint {endpoint_name} does not exist. Creating...")

            # Prepare and deploy the HuggingFace model
            self.prepare_and_deploy_model(
                role_arn=role_arn,
                llm_image=llm_image,
                config=config,
                endpoint_name=endpoint_name,
                update_endpoint=endpoint_exists,
                resources=resources,
                endpoint_type=endpoint_type,
                gpu_instance_type=gpu_instance_type,
            )

            self.logger.info(f"Successfully deployed/updated model to endpoint {endpoint_name}.")
        except Exception as e:
            self.logger.error(f"Failed to deploy model to SageMaker: {e}")
            raise

    @staticmethod
    def prepare_and_deploy_model(
        role_arn: str,
        llm_image: str,
        config: dict,
        endpoint_name: str,
        update_endpoint: bool,
        gpu_instance_type: str,
        resources: Optional[dict] = None,
        endpoint_type: enum.Enum = EndpointType.MODEL_BASED,
    ):
        """
        Prepares and deploys/updates the HuggingFace model on SageMaker.

        :param role_arn: The ARN of the IAM role.
        :param llm_image: The Docker image URI for the HuggingFace model.
        :param config: Configuration settings for the model.
        :param endpoint_name: The name of the endpoint.
        :param update_endpoint: Boolean flag to update an existing endpoint.
        :param gpu_instance_type: The instance type for the SageMaker endpoint.
        :param resources: Optional resources for the model deployment(used for multi model endpoints)
        :param endpoint_type: can be EndpointType.MODEL_BASED (without inference component)
                or EndpointType.INFERENCE_COMPONENT (with inference component)
        """
        huggingface_model = HuggingFaceModel(role=role_arn, image_uri=llm_image, env=config)

        # Deploy or update the model based on the endpoint existence
        huggingface_model.deploy(
            instance_type=gpu_instance_type,
            initial_instance_count=1,
            endpoint_name=endpoint_name,
            update_endpoint=update_endpoint,
            resources=resources,
            tags=[{"Key": "task", "Value": "model_task"}],
            endpoint_type=endpoint_type,
        )
