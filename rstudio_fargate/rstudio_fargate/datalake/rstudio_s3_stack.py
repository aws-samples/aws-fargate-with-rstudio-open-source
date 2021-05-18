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

from aws_cdk import core as cdk
from aws_cdk.core import RemovalPolicy,Duration,CfnOutput
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_iam
from aws_cdk import aws_s3_deployment as s3_deploy
from aws_cdk import aws_athena as athena

class RstudioS3Stack(cdk.Stack):
        def __init__(self, scope: cdk.Construct, 
            id: str, 
            instance: str,
            rstudio_instance_account_id: str,
            **kwargs) -> None:
            super().__init__(scope, id, **kwargs)

            rstudio_athena_bucket_name=self.node.try_get_context("rstudio_athena_bucket_name")
            
            if rstudio_athena_bucket_name is None:
                raise ValueError("Please provide name for rstudio Athena bucket")

            rstudio_athena_wg_name=self.node.try_get_context("rstudio_athena_wg_name")
            
            if rstudio_athena_wg_name is None:
                raise ValueError("Please provide name for rstudio Athena workgroup")
                
            #Create S3 bucket for athena queries
            self.s3_bucket = s3.Bucket(
                        self, 
                        'r-bucket-for-athena', 
                        versioned=False,
                        bucket_name=f'{rstudio_athena_bucket_name}-' + instance,
                        block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                        encryption=s3.BucketEncryption.S3_MANAGED,
                        removal_policy=RemovalPolicy.DESTROY,
                        lifecycle_rules= [
                            s3.LifecycleRule(
                                expiration=Duration.days(365),
                                transitions=[
                                    s3.Transition(
                                        storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                                        transition_after=Duration.days(30),
                                    ),
                                    s3.Transition(
                                        storage_class=s3.StorageClass.GLACIER,
                                        transition_after=Duration.days(90),
                                    )
                                ]
                            )
                        ],
                    )
            
            self.s3_bucket.add_to_resource_policy(
            permission=aws_iam.PolicyStatement(
                                principals=[aws_iam.AccountPrincipal(rstudio_instance_account_id)],
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
                                    self.s3_bucket.bucket_arn,
                                    f'{self.s3_bucket.bucket_arn}/*'
                                ]
                )
            )            
            
            s3_prefix_creation = s3_deploy.BucketDeployment(
                        self, 
                        's3-prefix-deployment',
                        sources=[
                            s3_deploy.Source.asset('./dummy')
                            ],
                        destination_bucket=self.s3_bucket,
                        destination_key_prefix= 'Athena-Query/',
                        retain_on_delete=False,
                    )

            athena_wg = athena.CfnWorkGroup(
                        self, 
                        f"r-wg-for-athena-{instance}",
                        name=f'{rstudio_athena_wg_name}-' + instance,
                        description='R Workgroup for Athena',
                        work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                            publish_cloud_watch_metrics_enabled=True,
                            enforce_work_group_configuration=True,
                            requester_pays_enabled=True,
                            #bytesScannedCutoffPerQuery=TEN_GIGABYTES_IN_BYTES,
                            result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                                output_location=f"s3://{self.s3_bucket.bucket_name}/Athena-Query/",
                                encryption_configuration=athena.CfnWorkGroup.EncryptionConfigurationProperty(
                                    encryption_option='SSE_S3',
                                )
                            )
                        )
                    )

            CfnOutput(self, 'AthenaWgNameExport-' + instance, 
                export_name='Athena-Wg-Name-' + instance,
                value=athena_wg.name,
                )                           


          


