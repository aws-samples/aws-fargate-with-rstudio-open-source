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

This stack creates the S3 bucket for user data upload and configues the bucket for
cross-account access. This stack also creates the instant and hourly data upload folders
and event notification for instant upload.

"""

import os

from aws_cdk import (
    core as cdk,
    aws_s3 as s3,
    aws_ssm as ssm,
    aws_iam as iam,
    aws_s3_deployment as s3_deploy,
    aws_s3_notifications as s3_notifications,
    aws_lambda as _lambda,
)
from aws_cdk.core import RemovalPolicy


class DataLakeResourcesStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        instance: str,
        rstudio_account_id: str,
        datalake_source_bucket_name: str,
        datalake_source_bucket_key_hourly: str,
        datalake_source_bucket_key_instant: str,
        lambda_datasync_trigger_function_arn: str,
        **kwargs,
    ):
        cdk.Stack.__init__(self, scope, id, **kwargs)

        """    
        # set removal policy objects
        self.removal_policy = (
            core.RemovalPolicy.DESTROY
            if os.getenv("AWS_REMOVAL_POLICY", "FALSE") == "TRUE"
            else core.RemovalPolicy.RETAIN
        )
        """

        source_bucket = s3.Bucket(
            self,
            id=f"rstudio-user-data-{instance}",
            bucket_name=datalake_source_bucket_name,
            # removal_policy=self.removal_policy,
            removal_policy=RemovalPolicy.DESTROY,
            versioned=True,
        )

        source_bucket.add_to_resource_policy(
            permission=iam.PolicyStatement(
                principals=[iam.AccountPrincipal(rstudio_account_id)],
                effect=iam.Effect.ALLOW,
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
                    "s3:ListBucketMultipartUploads",
                ],
                resources=[
                    source_bucket.bucket_arn,
                    f"{source_bucket.bucket_arn}/*",
                ],
            )
        )

        s3_prefix_creation_hourly = s3_deploy.BucketDeployment(
            self,
            id=f"s3-prefix-deployment-hourly-{instance}",
            sources=[s3_deploy.Source.asset("./dummy")],
            destination_bucket=source_bucket,
            destination_key_prefix=datalake_source_bucket_key_hourly,
            retain_on_delete=False,
        )

        s3_prefix_creation_instant = s3_deploy.BucketDeployment(
            self,
            id=f"s3-prefix-deployment-instant-{instance}",
            sources=[s3_deploy.Source.asset("./dummy")],
            destination_bucket=source_bucket,
            destination_key_prefix=datalake_source_bucket_key_instant,
            retain_on_delete=False,
        )

        # Setup bucket notification to trigger lambda (in destination account) whenever a file is uploaded into the bucket
        lambda_destination = s3_notifications.LambdaDestination(
            _lambda.Function.from_function_arn(
                self,
                id=f"datasync-lambda-{instance}",
                function_arn=lambda_datasync_trigger_function_arn,
            )
        )

        source_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            lambda_destination,
            s3.NotificationKeyFilter(prefix=f"{datalake_source_bucket_key_instant}/"),
        )
