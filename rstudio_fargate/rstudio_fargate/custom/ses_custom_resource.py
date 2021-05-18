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

"""

from typing import Any
from aws_cdk import (
    core,
    aws_iam as iam,
    aws_s3 as s3,
    aws_kms as kms
)

from aws_cdk import (
    aws_cloudformation as cfn,
    aws_lambda as lambda_,
    core
)

from aws_cdk.custom_resources import (
    AwsCustomResourcePolicy,
    PhysicalResourceId,
)

from datetime import datetime

class SESSendEmail (core.Construct):
    """SSM Parameter constructs that retrieves the parameter value form an environment
    Arguments:
        :param parameter_name -- The name of the SSM parameter to retrieve its value
    """

    def __init__(self, 
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
                 **kwargs) -> None:
        super().__init__(scope, id)
        
        
        encryption_key_arn = self.node.try_get_context("encryption_key_arn")

        if encryption_key_arn is None:
            raise ValueError("Please provide encryption key arn")
            
        encryption_key=kms.Key.from_key_arn(self, 'Encryption-Key', key_arn=encryption_key_arn)
            
        with open("rstudio_fargate/custom/ses_custom_resource_handler.py", encoding="utf-8") as fp:
            code_body = fp.read()
        
        function_name = f"rstudio_send_email_" + instance + "_" + str(counter)
        #function_name = f"rstudio_send_email"
        policy = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup"
                    ],
                resources=[
                    f"arn:aws:logs:{region}:{account_id}:*"
                    ]
                ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                    ],
                resources=[
                    f"arn:aws:logs:{region}:{account_id}:log-group:/aws/lambda/{function_name}:*"
                    ]
                ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ses:SendEmail",
                    "ses:SendRawEmail",
                    "ses:SendTemplatedEmail"
                    ],
                resources=[
                    f"arn:aws:ses:{region}:{account_id}:identity/*"
                    ]
                ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "secretsmanager:GetSecretValue"
                    ],
                resources=[
                    "*"
                    ]
                ), 
            ]
        
        params = {
            "EmailFrom": email_from,
            "EmailTo": email_to,
            "SecretArn": secret_arn,
            "Subject": subject,
            "Message": message
        }
        
        func = lambda_.SingletonFunction(
                    self, "SesSingleton",
                    lambda_purpose="SesSingleton-Lambda",
                    function_name=function_name,
                    uuid="f3d4f730-4ee1-11e8-9c2d-fd7ae01bbebc",
                    code=lambda_.InlineCode(code_body),
                    handler="index.main",
                    timeout=core.Duration.seconds(300),
                    runtime=lambda_.Runtime.PYTHON_3_8,
                    initial_policy=policy
                )
                
        self.resource = cfn.CustomResource(
            self, "Resource",
            provider=cfn.CustomResourceProvider.lambda_(
                func
            ),
            properties=params,
        )
            
        encryption_key.grant_decrypt(func)