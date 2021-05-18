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

from aws_cdk import core, aws_s3, aws_ssm, aws_iam
from aws_cdk import aws_s3_deployment as s3_deploy
from aws_cdk import aws_s3_notifications as s3_notifications
from aws_cdk import aws_lambda as _lambda

class DataLakeResourcesStack(core.Stack):
    def __init__(
        self,
        scope: core.Construct,
        id: str,
        instance: str,
        rstudio_account_id: str,
        pipeline_unique_id: str,
        **kwargs,
    ):
        core.Stack.__init__(self, scope,  id, **kwargs)
      
        
        datalake_source_bucket_key_hourly = self.node.try_get_context("datalake_source_bucket_key_hourly")

        if datalake_source_bucket_key_hourly is None:
            raise ValueError("Please supply the name of the folder to use for hourly uploads in the datalake bucket")  
    
        datalake_source_bucket_key_instant = self.node.try_get_context("datalake_source_bucket_key_instant")

        if datalake_source_bucket_key_instant is None:
            raise ValueError("Please supply the name of the folder to use for instant uploads in the datalake bucket")

        datalake_source_bucket_name = self.node.try_get_context("datalake_source_bucket_name")

        if datalake_source_bucket_name is None:
            raise ValueError("Please supply prefix for the data upload bucket")

        datalake_source_bucket_name=f'{datalake_source_bucket_name}-{instance}'
            
        # set removal policy objects
        self.removal_policy = (
            core.RemovalPolicy.DESTROY
            if os.getenv("AWS_REMOVAL_POLICY", "FALSE") == "TRUE"
            else core.RemovalPolicy.RETAIN
        )


        self.source_bucket = aws_s3.Bucket(
            self,
            "rstudio-user-data-" + instance,
            bucket_name=datalake_source_bucket_name,
            removal_policy=self.removal_policy,
            versioned=True,
        )

        self.source_bucket.add_to_resource_policy(
            permission=aws_iam.PolicyStatement(
                                principals=[aws_iam.AccountPrincipal(rstudio_account_id)],
                                effect=aws_iam.Effect.ALLOW,
                                actions=[
                                    "s3:GetBucketNotification",
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
              
        s3_prefix_creation_hourly = s3_deploy.BucketDeployment(
            self, 
            's3-prefix-deployment-hourly' + instance,
            sources=[
                s3_deploy.Source.asset('./dummy')
                ],
            destination_bucket=self.source_bucket,
            destination_key_prefix= datalake_source_bucket_key_hourly,
            retain_on_delete=False,
        ) 
        
        
        s3_prefix_creation_instant = s3_deploy.BucketDeployment(
            self, 
            's3-prefix-deployment-instant' + instance,
            sources=[
                s3_deploy.Source.asset('./dummy')
                ],
            destination_bucket=self.source_bucket,
            destination_key_prefix= datalake_source_bucket_key_instant,
            retain_on_delete=False,
        ) 
        
        lambda_trigger_function_arn=f'arn:aws:lambda:{self.region}:{rstudio_account_id}:function:trigger_datasync_task-{instance}-{pipeline_unique_id}'

        # Setup bucket notification to trigger lambda (in destination account) whenever a file is uploaded into the bucket
        lambda_destination = s3_notifications.LambdaDestination(
            _lambda.Function.from_function_arn(self, 'datasync-lambda-test', lambda_trigger_function_arn)
        )
        
        self.source_bucket.add_event_notification(
            aws_s3.EventType.OBJECT_CREATED, 
            lambda_destination, 
            aws_s3.NotificationKeyFilter(prefix=f'{datalake_source_bucket_key_instant}/'
            )
        )
                                            
                                            
        