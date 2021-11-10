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
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

This script creates the lambda function to send SES emails to users

"""

from typing import Any
from aws_cdk import (
    core,
    aws_iam as iam,
    aws_s3 as s3,
    aws_kms as kms,
    aws_cloudformation as cfn,
    aws_lambda as lambda_,
)

from aws_cdk.custom_resources import (
    AwsCustomResourcePolicy,
    PhysicalResourceId,
)

from datetime import datetime


class SESSendEmail(core.Construct):
    """SSM Parameter constructs that retrieves the parameter value form an environment
    Arguments:
        :param parameter_name -- The name of the SSM parameter to retrieve its value
    """

    def __init__(
        self,
        scope: core.Construct,
        id: str,
        email_from: str,
        email_to: str,
        secret_arn: str,
        subject: str,
        message: str,
        region: str,
        account_id: str,
        counter: int,
        instance: str,
        rstudio_user_key_alias: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id)

        encryption_key = kms.Alias.from_alias_name(
            self,
            id=f"Encryption-Key-{instance}",
            alias_name=rstudio_user_key_alias,
        )

        with open(
            "rstudio_fargate/rstudio/ses/ses_custom_resource_handler.py",
            encoding="utf-8",
        ) as fp:
            code_body = fp.read()

        function_name = f"rstudio_send_email_{instance}_" + str(counter)
        # function_name = f"rstudio_send_email"
        policy = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["logs:CreateLogGroup"],
                resources=[f"arn:aws:logs:{region}:{account_id}:*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                resources=[
                    f"arn:aws:logs:{region}:{account_id}:log-group:/aws/lambda/{function_name}:*"
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ses:SendEmail", "ses:SendRawEmail", "ses:SendTemplatedEmail"],
                resources=[f"arn:aws:ses:{region}:{account_id}:identity/*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["secretsmanager:GetSecretValue"],
                resources=[
                    f"arn:aws:secretsmanager:{region}:{account_id}:secret:*rstudio*"
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "kms:Decrypt",
                    "kms:DescribeKey",
                    "kms:Encrypt",
                    "kms:ReEncrypt*",
                    "kms:GenerateDataKey*",
                ],
                resources=["*"],
            ),
        ]

        params = {
            "EmailFrom": email_from,
            "EmailTo": email_to,
            "SecretArn": secret_arn,
            "Subject": subject,
            "Message": message,
        }

        func = lambda_.SingletonFunction(
            self,
            "SesSingleton",
            lambda_purpose="SesSingleton-Lambda",
            function_name=function_name,
            uuid="f3d4f730-4ee1-11e8-9c2d-fd7ae01bbebc",
            code=lambda_.InlineCode(code_body),
            handler="index.main",
            timeout=core.Duration.seconds(300),
            runtime=lambda_.Runtime.PYTHON_3_8,
            initial_policy=policy,
        )

        self.resource = cfn.CustomResource(
            self,
            "Resource",
            provider=cfn.CustomResourceProvider.lambda_(func),
            properties=params,
        )

        encryption_key.grant_decrypt(func)
