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

This stack creates the SSM parameter cross-account riole and permissions for the lambda
from rstudio deployment account to retrieve hosted zone delegation

"""

import os
import calendar
import time

from aws_cdk import (
    core as cdk,
    aws_iam as iam,
)


class NetworkAccountResources(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        instance: str,
        rstudio_account_id: str,
        ssm_cross_account_role_name: str,
        **kwargs,
    ):
        cdk.Stack.__init__(self, scope, id, **kwargs)

        # Create a policy and a role that will be assumed by the cross account lambda in the rstudio account to retrieve SSM parameters
        policy = iam.ManagedPolicy(
            self,
            id=f"SSM-Cross-Account-Policy-{instance}",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ssm:GetParameter",
                        "ssm:GetParameters",
                        "ssm:DescribeParameters",
                    ],
                    resources=[
                        f"arn:aws:ssm:{self.region}:{self.account}:parameter/{instance}/*"
                    ],
                ),
            ],
        )

        principal = []

        principal.append(iam.AccountPrincipal(rstudio_account_id))

        composite_principal = iam.CompositePrincipal(*principal)

        ssm_cross_account_role = iam.Role(
            self,
            id=f"SSM-Cross-Account-Role-{instance}",
            role_name=ssm_cross_account_role_name,
            assumed_by=composite_principal,
        )

        policy.attach_to_role(ssm_cross_account_role)
