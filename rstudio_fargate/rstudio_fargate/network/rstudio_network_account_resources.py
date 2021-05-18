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

import os
import calendar
import time

from aws_cdk import core, aws_s3, aws_ssm
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda

class NetworkAccountResources(core.Stack):
    def __init__(
        self,
        scope: core.Construct,
        id: str,
        pipeline_unique_id: str,
        **kwargs,
    ):
        core.Stack.__init__(self, scope,  id, **kwargs)

        rstudio_account_ids = self.node.try_get_context("rstudio_account_ids")

        if rstudio_account_ids is None:
            raise ValueError("Please supply the comma separated aws account ids of the rstudio accounts")
        
        # Create a policy and a role that will be assumed by the cross account lambda in the rstudio account to retrieve SSM parameters
        policy = iam.ManagedPolicy(
          self, 
          'SSM-Cross-Account-Policy', 
          statements=[
            iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
              "ssm:GetParameter",
              "ssm:GetParameters"
              ],
              resources=[f'arn:aws:ssm:{self.region}:{self.account}:parameter/poc/*'],
              ),
            iam.PolicyStatement(
              effect=iam.Effect.ALLOW,
              actions=[
                "ssm:DescribeParameters"
                ],
              resources=[f'arn:aws:ssm:{self.region}:{self.account}:*'],
              )
            ],
          )

        principals = []
        
        for account in rstudio_account_ids.split(","):
            principals.append(
                iam.AccountPrincipal(account)
            )
        
        #for principal in principals
        composite_principal=iam.CompositePrincipal(*principals)
    
        ssm_cross_account_role = iam.Role(self, 'SSM-Cross-Account-Role-', 
          role_name=f'ssm_cross_account_role-{pipeline_unique_id}',
          assumed_by=composite_principal
        )
    
        policy.attach_to_role(ssm_cross_account_role)

