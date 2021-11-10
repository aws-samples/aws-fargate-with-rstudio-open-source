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

This stack creates the S3 bucket for athena query output and the athena workgroup
for using athena from rstudio. The stack also configures the bucket for cross-account
access.

"""

from aws_cdk import (
    core as cdk,
    aws_s3 as s3,
    aws_iam as iam,
    aws_s3_deployment as s3_deploy,
    aws_athena as athena,
    aws_ssm as ssm,
)
from aws_cdk.core import (
    RemovalPolicy,
    Duration,
)


class RstudioS3Stack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        instance: str,
        rstudio_account_id: str,
        athena_output_bucket_name: str,
        athena_output_bucket_key: str,
        athena_workgroup_name: str,
        s3_lifecycle_expiration_duration: int,
        s3_trasnition_duration_infrequent_access: int,
        s3_trasnition_duration_glacier: int,
        ssm_cross_account_role_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Create S3 bucket for athena queries
        athena_s3_bucket = s3.Bucket(
            self,
            id=f"r-bucket-for-athena-{instance}",
            versioned=False,
            bucket_name=athena_output_bucket_name,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            lifecycle_rules=[
                s3.LifecycleRule(
                    expiration=Duration.days(s3_lifecycle_expiration_duration),
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(
                                s3_trasnition_duration_infrequent_access
                            ),
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(
                                s3_trasnition_duration_glacier
                            ),
                        ),
                    ],
                )
            ],
        )

        athena_s3_bucket.add_to_resource_policy(
            permission=iam.PolicyStatement(
                principals=[iam.AccountPrincipal(rstudio_account_id)],
                effect=iam.Effect.ALLOW,
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
                    "s3:ListBucketMultipartUploads",
                ],
                resources=[
                    athena_s3_bucket.bucket_arn,
                    f"{athena_s3_bucket.bucket_arn}/*",
                ],
            )
        )

        s3_prefix_creation = s3_deploy.BucketDeployment(
            self,
            id=f"s3-prefix-deployment",
            sources=[s3_deploy.Source.asset("./dummy")],
            destination_bucket=athena_s3_bucket,
            destination_key_prefix=f"{athena_output_bucket_key}/",
            retain_on_delete=False,
        )

        athena_wg = athena.CfnWorkGroup(
            self,
            id=f"r-wg-for-athena-{instance}",
            name=athena_workgroup_name,
            description="Rstudio Workgroup for Athena",
            work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                publish_cloud_watch_metrics_enabled=True,
                enforce_work_group_configuration=True,
                requester_pays_enabled=True,
                # bytesScannedCutoffPerQuery=TEN_GIGABYTES_IN_BYTES,
                result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                    output_location=f"s3://{athena_s3_bucket.bucket_name}/{athena_output_bucket_key}/",
                    encryption_configuration=athena.CfnWorkGroup.EncryptionConfigurationProperty(
                        encryption_option="SSE_S3",
                    ),
                ),
            ),
        )

