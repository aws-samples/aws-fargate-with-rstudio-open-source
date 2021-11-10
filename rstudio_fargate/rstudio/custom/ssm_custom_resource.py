"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
OFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

This script creates the lambda function to read the cross account SSM parameter store
for obtaining route53 hsited zone delegation

"""

from typing import Any
from aws_cdk import (
    core,
    aws_iam as iam,
    aws_s3 as s3,
)

from aws_cdk import aws_cloudformation as cfn, aws_lambda as lambda_, core

from aws_cdk.custom_resources import (
    AwsCustomResourcePolicy,
    PhysicalResourceId,
)

from datetime import datetime


class SSMParameterReader(core.Construct):
    """SSM Parameter constructs that retrieves the parameter value form an environment
    Arguments:
        :param parameter_name -- The name of the SSM parameter to retrieve its value
    """

    def __init__(
        self,
        scope: core.Construct,
        id: str,
        parameter_name: str,
        region: str,
        instance: str,
        rstudio_account_id: str,
        rstudio_pipeline_account_id: str,
        network_account_id: str,
        cross_account_id: str,
        ssm_cross_account_role_name: str,
        ssm_cross_account_lambda_role_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id)

        with open(
            "rstudio_fargate/rstudio/custom/ssm_custom_resource_handler.py",
            encoding="utf-8",
        ) as fp:
            code_body = fp.read()

        cross_account_role_arn_network = (
            f"arn:aws:iam::{network_account_id}:role/{ssm_cross_account_role_name}"
        )

        cross_account_role_arn_pipeline = f"arn:aws:iam::{rstudio_pipeline_account_id}:role/{ssm_cross_account_role_name}"

        cross_account_role_arn = (
            f"arn:aws:iam::{cross_account_id}:role/{ssm_cross_account_role_name}"
        )

        policy = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sts:AssumeRole",
                ],
                resources=[
                    cross_account_role_arn_network,
                    cross_account_role_arn_pipeline,
                ],
            ),
        ]

        params = {"ParameterName": parameter_name, "AssumeRole": cross_account_role_arn}

        role = self.get_provisioning_lambda_role(
            construct_id=id,
            instance=instance,
            role_name=ssm_cross_account_lambda_role_name,
            rstudio_account_id=rstudio_account_id,
            ssm_cross_account_lambda_role_name=ssm_cross_account_lambda_role_name,
        )

        self.resource = cfn.CustomResource(
            self,
            id=f"Resource",
            provider=cfn.CustomResourceProvider.lambda_(
                lambda_.SingletonFunction(
                    self,
                    "Singleton",
                    uuid="f7d4f730-4ee1-11e8-9c2d-fa7ae01bbebc",
                    code=lambda_.InlineCode(code_body),
                    handler="index.main",
                    timeout=core.Duration.seconds(300),
                    runtime=lambda_.Runtime.PYTHON_3_7,
                    role=role,
                    initial_policy=policy,
                )
            ),
            properties=params,
        )

    def get_parameter_value(self):
        return self.resource.get_att("Response").to_string()

    def get_provisioning_lambda_role(
        self,
        construct_id: str,
        instance: str,
        role_name: str,
        rstudio_account_id: str,
        ssm_cross_account_lambda_role_name: str,
    ):
        return iam.Role.from_role_arn(
            self,
            id=f"LambdaExecutionRole-{instance}",
            role_arn=f"arn:aws:iam::{rstudio_account_id}:role/{ssm_cross_account_lambda_role_name}",
            mutable=True,
        )
