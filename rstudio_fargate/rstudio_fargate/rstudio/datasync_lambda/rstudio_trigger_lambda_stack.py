#!/usr/bin/env python3

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

from os import getenv
from pathlib import Path

from aws_cdk import core as cdk
from aws_cdk import aws_lambda as _lambda
from aws_cdk.core import Fn,RemovalPolicy,Duration,CfnOutput,Construct,Stack
from aws_cdk import aws_iam as iam

LAMBDA_DURATION = Duration.minutes(3)
LAMBDA_MEMORY = 1024
LAMBDA_RUNTIME = _lambda.Runtime.PYTHON_3_7

class RstudioTriggerLambdaStack(Stack):

    def __init__(self, 
                    scope: Construct, 
                    id: str,
                    instance: str,
                    pipeline_unique_id: str,
                **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        datalake_account_id = self.node.try_get_context("datalake_account_id")

        if datalake_account_id is None:
            raise ValueError("Please provide datalake account id")  
      
        datalake_source_bucket_name = self.node.try_get_context("datalake_source_bucket_name")

        if datalake_source_bucket_name is None:
            raise ValueError("Please supply prefix for the data upload bucket")

        datalake_source_bucket_name=f'{datalake_source_bucket_name}-{instance}'

        datasync_task_arn_ssm_param_name=f'/{instance}/rstudio-datasync-taskarn'
    
        trigger_datasync_function = _lambda.Function(
            self,
            id='trigger_datasync_function',
            code=_lambda.Code.asset('rstudio_fargate/rstudio/datasync_lambda/source/'),
            function_name=f'trigger_datasync_task-{instance}-{pipeline_unique_id}',
            handler='trigger_datasync_handler.lambda_handler',
            layers=[],
            runtime=LAMBDA_RUNTIME,
            timeout=LAMBDA_DURATION,
            memory_size=LAMBDA_MEMORY,
            environment={
                'DATASYNC_TASK_ARN_SSM_PARAM_NAME': datasync_task_arn_ssm_param_name
            },
        )
 
        # Retrieve the datasync task arn parameter
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
                                "ssm:GetParameter",
                                "ssm:GetParameters"
                            ],
                            effect=iam.Effect.ALLOW,
                            resources=[f'arn:aws:ssm:{self.region}:{self.account}:parameter/*']
                        )
        )
        
        trigger_datasync_function.add_to_role_policy(
            statement=iam.PolicyStatement(
                            actions=[
                                "ssm:DescribeParameters"
                            ],
                            effect=iam.Effect.ALLOW,
                            resources=[f'arn:aws:ssm:{self.region}:{self.account}:*']
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

        # To allow the remote S3 bucket to invoke this lambda:
        trigger_datasync_function.add_permission(id="AllowDLToInvokeMe",
                principal=iam.ServicePrincipal('s3.amazonaws.com'), 
                action='lambda:InvokeFunction', 
                source_account=datalake_account_id, 
                source_arn=f'arn:aws:s3:::{datalake_source_bucket_name}')

        trigger_datasync_function.add_permission(id="AllowDLToAddPermissionsOnMe",
                principal=iam.AccountPrincipal(datalake_account_id), 
                action='lambda:AddPermission', 
                source_account=datalake_account_id)

        
        #The following role will be used as an execution role for the lambda function that retrieves cross-account SSM parameters
        ssm_lambda_execution_role = iam.Role(
            role_name=f'get_ssm_parameter_lambda_role-{instance}-{pipeline_unique_id}',
            scope=self,
            id='SSM-Lambda-ExecutionRole' + instance,
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole")],
        )
        
    @property
    def _function(self) -> _lambda.IFunction:
        return self.trigger_function
