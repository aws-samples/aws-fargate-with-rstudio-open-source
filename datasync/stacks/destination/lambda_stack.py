#!/usr/bin/env python3

"""
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: MIT-0
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this
 * software and associated documentation files (the "Software"), to deal in the Software
 * without restriction, including without limitation the rights to use, copy, modify,
 * merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
 * INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
 * PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 * OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

from os import getenv
from pathlib import Path

from aws_cdk import core as cdk
from aws_cdk import aws_lambda as _lambda
from aws_cdk.core import Fn,RemovalPolicy,Duration,CfnOutput,Construct,Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ssm as ssm

# from cdk_libs.idp_lambda import Code
# from cdk_libs.idp_s3_assets import DependentAsset

LAMBDA_DURATION = Duration.minutes(3)
LAMBDA_MEMORY = 1024
LAMBDA_RUNTIME = _lambda.Runtime.PYTHON_3_7

base_deployment_dependencies = [
    "./source/helpers/dynamo_utils.py",
    "./source/helpers/encoding.py",
    "./source/helpers/parsing.py",
    "./requirements/functions.txt"
]

class LambdaStack(Stack):

    def __init__(self, scope: Construct, id: str,
                **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        instance = self.node.try_get_context("instance")

        if instance is None:
            raise ValueError("Please pass instance to use via context (dev/prod/...)")

        source_bucket_name = self.node.try_get_context("source_bucket_name")
            
        if source_bucket_name is None:
            raise ValueError("Please provide name of the source bucket for file uploads") 

        source_account_id = self.node.try_get_context("source_account_id")

        if source_account_id is None:
            raise ValueError("Please provide source account id")  
      
        lambda_trigger_function_name = self.node.try_get_context("lambda_trigger_function_name")

        if lambda_trigger_function_name is None:
            raise ValueError("Please supply the name of the lambda trigger function in the destination account")
        
        
        datasync_task_arn_ssm_param_name = self.node.try_get_context("datasync_task_arn_ssm_param_name")

        if datasync_task_arn_ssm_param_name is None:
            raise ValueError("Please supply the name of the parameter storing datasync task arn in ssm")
        
        trigger_datasync_function = _lambda.Function(
            self,
            id='trigger_datasync_function',
            code=_lambda.Code.asset('source/functions'),
            function_name=lambda_trigger_function_name,
            handler='trigger_datasync_function.lambda_handler',
            layers=[],
            runtime=LAMBDA_RUNTIME,
            timeout=LAMBDA_DURATION,
            memory_size=LAMBDA_MEMORY,
            environment={
                'DATASYNC_TASK_ARN_SSM_PARAM_NAME': datasync_task_arn_ssm_param_name
            },
        )
 
        trigger_datasync_function.add_to_role_policy(
            statement=iam.PolicyStatement(
                            actions=[
                                "datasync:StartTaskExecution"
                            ],
                            effect=iam.Effect.ALLOW,
                            resources=[f'arn:aws:datasync:{self.region}:{self.account}:task/*']
                        )
        )

        trigger_datasync_function.add_to_role_policy(
            statement=iam.PolicyStatement(
                            actions=[
                                "ec2:DescribeNetworkInterfaces"
                            ],
                            effect=iam.Effect.ALLOW,
                            resources=["*"]
                        )
        )
        
        trigger_datasync_function.add_to_role_policy(
            statement=iam.PolicyStatement(
                            actions=[
                                "ssm:GetParameter",
                            ],
                            effect=iam.Effect.ALLOW,
                            resources=[f'arn:aws:ssm:{self.region}:{self.account}:parameter{datasync_task_arn_ssm_param_name}']
                        )
        )
        
        trigger_datasync_function.add_to_role_policy(
            statement=iam.PolicyStatement(
                            actions=[
                                "ssm:DescribeParameters"
                            ],
                            effect=iam.Effect.ALLOW,
                            resources=[f'arn:aws:ssm:{self.region}::{self.account}:*']
                        )
        )

        # To allow the remote X3 bucket to invoke this lambda:
        trigger_datasync_function.add_permission(id="AllowS3OnDLToInvokeMe",
                principal=iam.ServicePrincipal('s3.amazonaws.com'), 
                action='lambda:InvokeFunction', 
                source_account=source_account_id, 
                source_arn=f'arn:aws:s3:::{source_bucket_name}')

        trigger_datasync_function.add_permission(id="AllowS3OnDLToUpdateMyPermissions",
                principal=iam.AccountPrincipal(source_account_id), 
                action='lambda:AddPermission', 
                source_account=source_account_id)
                
        self.trigger_function_arn = trigger_datasync_function.function_arn
        self.trigger_function_role_arn = trigger_datasync_function.role.role_arn
        
    @property
    def _function(self) -> _lambda.IFunction:
        return self.trigger_function
