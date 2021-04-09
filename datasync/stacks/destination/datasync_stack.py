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

from aws_cdk import core as cdk
from aws_cdk import aws_datasync as datasync
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk.core import Fn, RemovalPolicy, CfnOutput
from aws_cdk import aws_efs as efs
from aws_cdk import aws_ec2 as ec2
from aws_cdk.aws_ec2 import Port
from aws_cdk import aws_ssm as ssm

class DataSyncStack(cdk.Stack):
        def __init__(self, 
                    scope: cdk.Construct, 
                    id: str, 
                    vpc: ec2.Vpc, 
                    destination_file_system_id: str,
                    destination_file_system_security_group_id: str,
                    trigger_lambda_execution_role_arn: str,
                    **kwargs) -> None:
            super().__init__(scope, id, **kwargs)

            instance = self.node.try_get_context("instance")

            if instance is None:
                raise ValueError("Please pass instance to use via context (dev/prod/...)")
            
            source_bucket_name = self.node.try_get_context("source_bucket_name")
            
            if source_bucket_name is None:
                raise ValueError("Please provide name of the Invista source bucket for file uploads")            
            bucket_access_role = iam.Role(self, f'data_xfer_source_bucket_access_role-{instance}', assumed_by = iam.ServicePrincipal('datasync.amazonaws.com'))
            
            data_xfer_source_bucket_arn=f'arn:aws:s3:::{source_bucket_name}'

            datasync_task_arn_ssm_param_name = self.node.try_get_context("datasync_task_arn_ssm_param_name")

            if datasync_task_arn_ssm_param_name is None:
                raise ValueError("Please supply the name of the parameter storing datasync task arn in ssm")
            
            bucket_access_role.add_to_principal_policy(
                     statement=iam.PolicyStatement(
                        actions=[
                            "s3:GetBucketLocation",
                            "s3:ListBucket",
                            "s3:ListBucketMultipartUploads",
                            "s3:ListBucket","s3:ListObjectsV2"
                        ],
                        effect=iam.Effect.ALLOW,
                        resources=[data_xfer_source_bucket_arn]
                    )
                )
                
            bucket_access_role.add_to_principal_policy(
                     statement=iam.PolicyStatement(
                        actions=[
                            "s3:AbortMultipartUpload",
                            "s3:DeleteObject",
                            "s3:GetObject",
                            "s3:ListMultipartUploadParts",
                            "s3:PutObjectTagging",
                            "s3:GetObjectTagging",
                            "s3:PutObject",
                            "s3:ListBucket","s3:ListObjectsV2"
                        ],
                        effect=iam.Effect.ALLOW,
                        resources=[f'{data_xfer_source_bucket_arn}/*']
                    )
                )
            
            #Log group:
            datasync_log_group = logs.LogGroup(
                self,
                id=f'datasync-logs-{instance}',
                log_group_name=f'datasync-{instance}/{id}',
                removal_policy=RemovalPolicy.DESTROY,
                retention=logs.RetentionDays.ONE_WEEK
                # encryption_key=rstudio_cloudwatch_log_kms_key_alias,
            )
            
            # Create datasync security group
            datasync_security_group = ec2.SecurityGroup(
                self, 
                f'Datasync-SecurityGroup-{instance}',
                vpc=vpc,
                description='Datasync security group',
                allow_all_outbound=True,
            )
            
            #Uploading task
            efs_security_group = ec2.SecurityGroup.from_security_group_id(self, "Efs-SG", destination_file_system_security_group_id,
                    mutable=True
                )

            file_system=efs.FileSystem.from_file_system_attributes(self, f'EFS-File-System-{instance}',
                                                                            file_system_id=destination_file_system_id,
                                                                            security_group=efs_security_group)

            instant_source_location = datasync.CfnLocationS3(self, 
                                                     id=f'data-xfer-source-location-{instance}',
                                                     s3_bucket_arn=data_xfer_source_bucket_arn, 
                                                     s3_config=datasync.CfnLocationS3.S3ConfigProperty(bucket_access_role_arn=bucket_access_role.role_arn),
                                                     subdirectory="instant_upload")

            instant_source_location.node.add_dependency(bucket_access_role)
            
            instant_destination_location = datasync.CfnLocationEFS(self,
                                                    id=f'data-xfer-destination-location-{instance}', 
                                                    ec2_config=datasync.CfnLocationEFS.Ec2ConfigProperty(security_group_arns=[f'arn:aws:ec2:{self.region}:{self.account}:security-group/{datasync_security_group.security_group_id}'],
                                                                                                         subnet_arn=f'arn:aws:ec2:{self.region}:{self.account}:subnet/{vpc.private_subnets[0].subnet_id}'),    
                                                    efs_filesystem_arn=f'arn:aws:elasticfilesystem:{self.region}:{self.account}:file-system/{file_system.file_system_id}', 
                                                    subdirectory='/destination-path', 
                                                    tags=None)
                                                    
            file_system.connections.allow_from(datasync_security_group, Port.tcp(2049));  

            # Create a task
            datasync_task = datasync.CfnTask(self, 
                            id =  f'data-xfer-task-{instance}',
                            destination_location_arn = instant_destination_location.attr_location_arn, 
                            source_location_arn = instant_source_location.attr_location_arn, 
                            cloud_watch_log_group_arn=f'arn:aws:logs:{self.region}:{self.account}:log-group:{datasync_log_group.log_group_name}', 
                            excludes=None, 
                            name=f'data-xfer-task-{instance}', 
                            options=datasync.CfnTask.OptionsProperty(log_level='TRANSFER'),
                            tags=None)

            datasync_task.node.add_dependency(datasync_log_group)
            
            rask_arn_param = ssm.StringParameter(self, "task_arn" + instance,
                allowed_pattern=".*",
                description="The arn of the instant upload Datasync task",
                parameter_name=datasync_task_arn_ssm_param_name,
                string_value=datasync_task.attr_task_arn,
                tier=ssm.ParameterTier.ADVANCED
            )
            
            lambda_execution_role = iam.Role.from_role_arn(self, 
                                                        'Lambda-Execution-Role' + instance,
                                                        trigger_lambda_execution_role_arn)
                        
            rask_arn_param.grant_read(lambda_execution_role)