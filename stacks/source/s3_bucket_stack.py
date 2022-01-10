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
from aws_cdk import core, aws_s3, aws_ssm, aws_iam
from aws_cdk import aws_s3_deployment as s3_deploy
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_s3_notifications as s3_notifications

class S3BucketStack(core.Stack):
    def __init__(
        self,
        scope: core.Construct,
        id: str,
        **kwargs,
    ):
        core.Stack.__init__(self, scope,  id, **kwargs)

        destination_account_id = self.node.try_get_context("destination_account_id")

        if destination_account_id is None:
            raise ValueError("Please supply the aws account id of the destination account")
        
        source_bucket_name = self.node.try_get_context("source_bucket_name")
        
        if source_bucket_name is None:
            raise ValueError("Please supply the name source S3 bucket for uploading")
        
        lambda_trigger_function_name = self.node.try_get_context("lambda_trigger_function_name")

        if lambda_trigger_function_name is None:
            raise ValueError("Please supply the name of the lambda trigger function in the destination account")
            
        # set removal policy objects such as s3 and dynamo
        self.removal_policy = (
            core.RemovalPolicy.DESTROY
            if os.getenv("AWS_REMOVAL_POLICY", "FALSE") == "TRUE"
            else core.RemovalPolicy.RETAIN
        )

        # Create the source bucket
        self.source_bucket = aws_s3.Bucket(
            self,
            "rstudio-user-data",
            bucket_name=source_bucket_name,
            removal_policy=self.removal_policy,
            versioned=True
        )
        
        # Allow cross account access to the bucket
        self.source_bucket.add_to_resource_policy(
            permission=aws_iam.PolicyStatement(
                                principals=[aws_iam.AccountPrincipal(destination_account_id)],
                                effect=aws_iam.Effect.ALLOW,
                                actions=[
                                    "s3:AbortMultipartUpload",
                                    "s3:DeleteObject",
                                    "s3:GetObject",
                                    "s3:ListMultipartUploadParts",
                                    "s3:PutObjectTagging",
                                    "s3:GetObjectTagging",
                                    "s3:PutObject",
                                    "s3:ListBucket",
                                    "s3:GetBucketLocation",
                                    "s3:ListBucketMultipartUploads"
                                ],
                                resources=[
                                    self.source_bucket.bucket_arn,
                                    f'{self.source_bucket.bucket_arn}/*'
                                ]
                )
            )            

        lambda_trigger_function_arn=f'arn:aws:lambda:eu-west-1:{destination_account_id}:function:{lambda_trigger_function_name}'
        # Setup bucket notification to trigger lambda (in destination account) whenever a file is uploaded into the bucket
        lambda_destination = s3_notifications.LambdaDestination(
                                _lambda.Function.from_function_arn(self, 'datasync-lambda-test', lambda_trigger_function_arn)
        )
        
        self.source_bucket.add_event_notification(aws_s3.EventType.OBJECT_CREATED, 
                                            lambda_destination
                                            )