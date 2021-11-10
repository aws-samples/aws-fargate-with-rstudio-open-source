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

from aws_cdk import (
    core as cdk,
    aws_datasync as datasync,
    aws_iam as iam,
    aws_ssm as ssm,
    aws_logs as logs,
    aws_efs as efs,
    aws_ec2 as ec2,
)
from aws_cdk.core import (
    RemovalPolicy,
)
from aws_cdk.aws_ec2 import Port
import json


class DataSyncStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        instance: str,
        vpc: ec2.Vpc,
        file_system_rstudio_hourly_file_system_id: str,
        file_system_rstudio_hourly_security_group_id: str,
        file_system_rstudio_instant_file_system_id: str,
        file_system_rstudio_instant_security_group_id: str,
        datalake_source_bucket_name: str,
        datasync_task_arn_ssm_param_name: str,
        datalake_source_bucket_key_hourly: str,
        access_point_path_hourly: str,
        datalake_source_bucket_key_instant: str,
        access_point_path_instant: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        bucket_access_role = iam.Role(
            self,
            id=f"data_xfer_source_bucket_access_role-{instance}",
            assumed_by=iam.ServicePrincipal("datasync.amazonaws.com"),
        )

        data_xfer_source_bucket_arn = f"arn:aws:s3:::{datalake_source_bucket_name}"

        bucket_access_role.add_to_principal_policy(
            statement=iam.PolicyStatement(
                actions=[
                    "s3:GetBucketLocation",
                    "s3:ListBucket",
                    "s3:ListBucketMultipartUploads",
                    "s3:ListBucket",
                    "s3:ListObjectsV2",
                ],
                effect=iam.Effect.ALLOW,
                resources=[data_xfer_source_bucket_arn],
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
                    "s3:ListBucket",
                    "s3:ListObjectsV2",
                ],
                effect=iam.Effect.ALLOW,
                resources=[f"{data_xfer_source_bucket_arn}/*"],
            )
        )

        # Log group:
        datasync_log_group = logs.LogGroup(
            self,
            id=f"Rstudio-datasync-logs-{instance}",
            log_group_name=f"Rstudio-datasync-{instance}/{id}",
            removal_policy=RemovalPolicy.DESTROY,
            retention=logs.RetentionDays.ONE_WEEK,
        )

        # Create datasync security group
        datasync_security_group = ec2.SecurityGroup(
            self,
            id=f"Datasync-SecurityGroup-{instance}",
            vpc=vpc,
            description="Datasync security group",
            allow_all_outbound=True,
        )

        efs_security_group_hourly = ec2.SecurityGroup.from_security_group_id(
            self,
            id=f"Efs-SG-hourly-{instance}",
            security_group_id=file_system_rstudio_hourly_security_group_id,
            mutable=True,
        )

        efs_filesystem_hourly = efs.FileSystem.from_file_system_attributes(
            self,
            id=f"Rstudio-EFS-File-System-hourly-{instance}",
            file_system_id=file_system_rstudio_hourly_file_system_id,
            security_group=efs_security_group_hourly,
        )

        # Create target Locations
        source_location_hourly = datasync.CfnLocationS3(
            self,
            id=f"data-xfer-source-location-{instance}",
            s3_bucket_arn=data_xfer_source_bucket_arn,
            s3_config=datasync.CfnLocationS3.S3ConfigProperty(
                bucket_access_role_arn=bucket_access_role.role_arn
            ),
            subdirectory=datalake_source_bucket_key_hourly,
        )

        source_location_hourly.node.add_dependency(bucket_access_role)

        # Create destination Location
        destination_location_hourly = datasync.CfnLocationEFS(
            self,
            id=f"data-xfer-destination-location-{instance}",
            ec2_config=datasync.CfnLocationEFS.Ec2ConfigProperty(
                security_group_arns=[
                    f"arn:aws:ec2:{self.region}:{self.account}:security-group/{datasync_security_group.security_group_id}"
                ],
                subnet_arn=f"arn:aws:ec2:{self.region}:{self.account}:subnet/{vpc.private_subnets[0].subnet_id}",
            ),
            efs_filesystem_arn=f"arn:aws:elasticfilesystem:{self.region}:{self.account}:file-system/{efs_filesystem_hourly.file_system_id}",
            subdirectory=access_point_path_hourly,
            tags=None,
        )

        # Create a task
        datasync_task_hourly = datasync.CfnTask(
            self,
            id=f"rstudio-data-xfer-task-{instance}",
            destination_location_arn=destination_location_hourly.attr_location_arn,
            source_location_arn=source_location_hourly.attr_location_arn,
            cloud_watch_log_group_arn=f"arn:aws:logs:{self.region}:{self.account}:log-group:{datasync_log_group.log_group_name}",
            excludes=None,
            name=f"rstudio-data-xfer-task-{instance}",
            options=datasync.CfnTask.OptionsProperty(log_level="TRANSFER"),
            schedule=datasync.CfnTask.TaskScheduleProperty(
                schedule_expression="cron(0 * * * ? *)"
            ),
            tags=None,
        )

        efs_filesystem_hourly.connections.allow_from(
            datasync_security_group, Port.tcp(2049)
        )

        # Instant uploading task

        efs_security_group_instant = ec2.SecurityGroup.from_security_group_id(
            self,
            id=f"Efs-SG-instant-{instance}",
            security_group_id=file_system_rstudio_instant_security_group_id,
            mutable=True,
        )

        file_system_rstudio_instant = efs.FileSystem.from_file_system_attributes(
            self,
            id=f"Rstudio-Fargate-EFS-File-System-Instant-{instance}",
            file_system_id=file_system_rstudio_instant_file_system_id,
            security_group=efs_security_group_instant,
        )

        instant_source_location = datasync.CfnLocationS3(
            self,
            id=f"instant-data-xfer-source-location-{instance}",
            s3_bucket_arn=data_xfer_source_bucket_arn,
            s3_config=datasync.CfnLocationS3.S3ConfigProperty(
                bucket_access_role_arn=bucket_access_role.role_arn
            ),
            subdirectory=datalake_source_bucket_key_instant,
        )

        instant_source_location.node.add_dependency(bucket_access_role)

        instant_destination_location = datasync.CfnLocationEFS(
            self,
            id=f"instant-data-xfer-destination-location-{instance}",
            ec2_config=datasync.CfnLocationEFS.Ec2ConfigProperty(
                security_group_arns=[
                    f"arn:aws:ec2:{self.region}:{self.account}:security-group/{datasync_security_group.security_group_id}"
                ],
                subnet_arn=f"arn:aws:ec2:{self.region}:{self.account}:subnet/{vpc.private_subnets[0].subnet_id}",
            ),
            efs_filesystem_arn=f"arn:aws:elasticfilesystem:{self.region}:{self.account}:file-system/{file_system_rstudio_instant.file_system_id}",
            subdirectory=access_point_path_instant,
            tags=None,
        )

        file_system_rstudio_instant.connections.allow_from(
            datasync_security_group, Port.tcp(2049)
        )

        # Create a task
        instant_datasync_task = datasync.CfnTask(
            self,
            id=f"instant-rstudio-data-xfer-task-{instance}",
            destination_location_arn=instant_destination_location.attr_location_arn,
            source_location_arn=instant_source_location.attr_location_arn,
            cloud_watch_log_group_arn=f"arn:aws:logs:{self.region}:{self.account}:log-group:{datasync_log_group.log_group_name}",
            excludes=None,
            name=f"instant-rstudio-data-xfer-task-{instance}",
            options=datasync.CfnTask.OptionsProperty(log_level="TRANSFER"),
            tags=None,
        )

        cw_resource_policy = json.dumps(
            {
                "Statement": [
                    {
                        "Sid": f"DataSyncLogsToCloudWatchLogs",
                        "Effect": "Allow",
                        "Action": ["logs:PutLogEvents", "logs:CreateLogStream"],
                        "Principal": {"Service": "datasync.amazonaws.com"},
                        "Condition": {
                            "ArnLike": {
                                "aws:SourceArn": [
                                    f"arn:aws:datasync:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:task/*"
                                ]
                            },
                            "StringEquals": {"aws:SourceAccount": cdk.Aws.ACCOUNT_ID},
                        },
                        "Resource": f"arn:aws:logs:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:log-group:*:*",
                    }
                ],
                "Version": "2012-10-17",
            }
        )

        logs.CfnResourcePolicy(
            self,
            id=f"DataSyncResourcePolicy-{instance}",
            policy_document=str(cw_resource_policy),
            policy_name=f"DataSyncResourcePolicy-{instance}",
        )

        datasync_task_hourly.node.add_dependency(datasync_log_group)

        instant_datasync_task.node.add_dependency(datasync_log_group)

        self.instant_datasync_task_arn = instant_datasync_task.attr_task_arn

        ssm.StringParameter(
            self,
            id=f"rstudio-datasync-task-arn-{instance}",
            allowed_pattern=".*",
            description="The arn of the instant upload Datasync task",
            parameter_name=datasync_task_arn_ssm_param_name,
            string_value=instant_datasync_task.attr_task_arn,
            tier=ssm.ParameterTier.ADVANCED,
        )
