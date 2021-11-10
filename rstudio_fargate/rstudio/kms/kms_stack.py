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

from aws_cdk import (
    core as cdk,
    aws_kms as kms,
    aws_iam as iam,
)
from aws_cdk.core import RemovalPolicy


class KmsStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        instance: str,
        rstudio_cwlogs_key_alias: str,
        shiny_cwlogs_key_alias: str,
        rstudio_efs_key_alias: str,
        shiny_efs_key_alias: str,
        rstudio_user_key_alias: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        rstudio_kms_key = kms.Key(
            self,
            id=f"Rstudio-Kms-Key-{instance}",
            enable_key_rotation=True,
            alias=rstudio_cwlogs_key_alias,
            removal_policy=RemovalPolicy.DESTROY,
        )

        rstudio_kms_key.add_alias(shiny_cwlogs_key_alias)
        rstudio_kms_key.add_alias(rstudio_efs_key_alias)
        rstudio_kms_key.add_alias(shiny_efs_key_alias)
        rstudio_kms_key.add_alias(rstudio_user_key_alias)

        rstudio_kms_key.add_to_resource_policy(
            statement=iam.PolicyStatement(
                actions=[
                    "kms:Decrypt",
                    "kms:DescribeKey",
                    "kms:Encrypt",
                    "kms:ReEncrypt*",
                    "kms:GenerateDataKey*",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
                principals=[
                    iam.ServicePrincipal(f"logs.{self.region}.amazonaws.com"),
                    iam.ServicePrincipal("sns.amazonaws.com"),
                ],
            )
        )
