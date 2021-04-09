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

import os

from aws_cdk import core as cdk
from stacks.destination.datasync_stack import DataSyncStack
from stacks.destination.efs_stack import EfsStack
from stacks.destination.kms_stack import KmsStack
from stacks.destination.vpc_stack import VpcStack
from stacks.destination.lambda_stack import LambdaStack
from stacks.source.s3_bucket_stack import S3BucketStack

app = cdk.App()

instance = app.node.try_get_context("instance")

if instance is None:
    raise ValueError("Please pass instance to use via context (dev/prod/...)")

destination_account_id = app.node.try_get_context("destination_account_id")

if destination_account_id is None:
    raise ValueError("Please provide the account id of the destination account")
    
vpc_cidr = app.node.try_get_context("vpc_cidr_range")

if vpc_cidr is None:
    raise ValueError("Please provide vpc cidr range for the build")

# The following stacks much be deployed into the destination account
#1. Create the shared VPC for this demo
vpc_stack_build = VpcStack(
            app, 
            "VpcStack",
            env= cdk.Environment(
                account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
                region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]),
                )
        )
#2. Create the KMS keys and aliases requrired for the destination EFS file system
kms_stack_build=KmsStack(
            app, 
            "KmsStack",
            env= cdk.Environment(
                account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
                region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]),
                )
        )

#3. Create the destination EFS file system and its access point        
efs_stack_build=EfsStack(
            app, 
            "EfsStack",
            vpc=vpc_stack_build.vpc,
            env= cdk.Environment(
                account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
                region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]),
                )
        )
#4. Create the lambda function used by the remote bucket to trigger datasync
lambda_stack_build=LambdaStack(
            app, 
            "LambdaStack",
            env= cdk.Environment(
                account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
                region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]),
                )
        )
#5. Peforms all the necessary Datasync configurations
datasync_stack_build=DataSyncStack(
            app, 
            "DataSyncStack",
            vpc=vpc_stack_build.vpc,
            destination_file_system_id=efs_stack_build.destination_file_system_id,
            destination_file_system_security_group_id=efs_stack_build.destination_file_system_security_group_id,
            trigger_lambda_execution_role_arn=lambda_stack_build.trigger_function_role_arn,
            env= cdk.Environment(
                account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
                region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]),
            )
        )


#6. The following stack must be run on the source account - it creates the source bucket and configures 
#   an event notification to invoke the above Lambda function    
s3_stack_build = S3BucketStack(app, 'S3BucketStack', 
                env= cdk.Environment(
                    account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
                    region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]),
                )
                )


efs_stack_build.add_dependency(kms_stack_build)                
efs_stack_build.add_dependency(vpc_stack_build)
datasync_stack_build.add_dependency(efs_stack_build)
datasync_stack_build.add_dependency(vpc_stack_build)
datasync_stack_build.add_dependency(lambda_stack_build)


app.synth()
