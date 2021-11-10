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
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
from ..custom.ssm_custom_resource import SSMParameterReader

from aws_cdk import (
    core as cdk,
    aws_route53 as r53,
    aws_route53_targets as route53_targets,
    aws_certificatemanager as acm,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_elasticloadbalancingv2 as alb,
    aws_efs as efs,
    aws_logs as logs,
    aws_secretsmanager as sm,
    aws_kms as kms,
    aws_ssm as ssm,
    aws_iam as iam,
)

from aws_cdk.core import RemovalPolicy, Duration
from aws_cdk.aws_route53 import RecordType, RecordTarget
from aws_cdk.aws_ec2 import Port
from aws_cdk.aws_elasticloadbalancingv2 import ApplicationProtocol
from aws_cdk.aws_ecr import Repository
from aws_cdk.aws_iam import PolicyStatement, Effect


class RstudioFargateStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        instance: str,
        vpc: ec2.Vpc,
        file_system_rstudio_shiny_share_file_system_id: str,
        file_system_rstudio_shiny_share_security_group_id: str,
        access_point_id_rstudio_shiny_share: str,
        file_system_rstudio_hourly_file_system_id: str,
        file_system_rstudio_hourly_security_group_id: str,
        access_point_id_rstudio_hourly: str,
        file_system_rstudio_instant_file_system_id: str,
        file_system_rstudio_instant_security_group_id: str,
        access_point_id_rstudio_instant: str,
        rstudio_pipeline_account_id: str,
        network_account_id: str,
        rstudio_container_memory_in_gb: int,
        rstudio_cert_arn: str,
        rstudio_hosted_zone_id: str,
        rstudio_hosted_zone_name: str,
        ecs_cluster_name: str,
        ecs_cluster_security_group_id: str,
        rstudio_container_repository_name_ssm_param: str,
        rstudio_container_repository_arn_ssm_param: str,
        athena_output_bucket_name: str,
        athena_workgroup_name: str,
        number_of_rstudio_containers: int,
        ssm_cross_account_role_name: str,
        ssm_cross_account_lambda_role_name: str,
        rstudio_user_key_alias: str,
        rstudio_efs_key_alias: str,
        rstudio_cwlogs_key_alias: str,
        rstudio_health_check_grace_period: int,
        home_container_path: str,
        shiny_share_container_path: str,
        hourly_sync_container_path: str,
        instant_sync_container_path: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        ssm_repo_name_reader = SSMParameterReader(
            self,
            id=f"SSM-Repo-Name-{instance}",
            parameter_name=rstudio_container_repository_name_ssm_param,
            region=self.region,
            instance=instance,
            rstudio_account_id=self.account,
            network_account_id=network_account_id,
            rstudio_pipeline_account_id=rstudio_pipeline_account_id,
            cross_account_id=rstudio_pipeline_account_id,
            ssm_cross_account_role_name=ssm_cross_account_role_name,
            ssm_cross_account_lambda_role_name=ssm_cross_account_lambda_role_name,
        )

        ssm_repo_arn_reader = SSMParameterReader(
            self,
            id=f"SSM-Repo-Arn-{instance}",
            parameter_name=rstudio_container_repository_arn_ssm_param,
            region=self.region,
            instance=instance,
            rstudio_account_id=self.account,
            network_account_id=network_account_id,
            rstudio_pipeline_account_id=rstudio_pipeline_account_id,
            cross_account_id=rstudio_pipeline_account_id,
            ssm_cross_account_role_name=ssm_cross_account_role_name,
            ssm_cross_account_lambda_role_name=ssm_cross_account_lambda_role_name,
        )

        rstudio_repository_name = ssm_repo_name_reader.get_parameter_value()

        rstudio_repository_arn = ssm_repo_arn_reader.get_parameter_value()

        rstudio_image_repo = Repository.from_repository_attributes(
            self,
            id=f"Rstudio-Docker-Image-Repo-{instance}",
            repository_arn=rstudio_repository_arn,
            repository_name=rstudio_repository_name,
        )

        encryption_key = kms.Alias.from_alias_name(
            self,
            id=f"Encryption-Key-{instance}",
            alias_name=rstudio_user_key_alias,
        )

        envvars_cont = {
            "RSTUDIO_VERSION": "1.4.1717",
            "AWS_S3_BUCKET": f"s3://{athena_output_bucket_name}/Athena-Query",
            "AWS_ATHENA_WG": f"{athena_workgroup_name}-{instance}",
        }

        rstudio_efs_kms_key_alias = kms.Alias.from_alias_name(
            self,
            id=f"Rstudio-Efs-{instance}",
            alias_name=rstudio_efs_key_alias,
        )

        if rstudio_container_memory_in_gb < 1:
            cont_cpu = 256
        elif 1 <= rstudio_container_memory_in_gb <= 2:
            cont_cpu = 512
        elif 2 < rstudio_container_memory_in_gb <= 8:
            cont_cpu = 1024
        elif 8 < rstudio_container_memory_in_gb <= 16:
            cont_cpu = 2048
        elif 16 < rstudio_container_memory_in_gb <= 32:
            cont_cpu = 4096

        cont_mem = rstudio_container_memory_in_gb * 1024

        # Configure the Shiny/Rstudio shared file system volume

        efs_security_group_share = ec2.SecurityGroup.from_security_group_id(
            self,
            id=f"Efs-SG-share-{instance}",
            security_group_id=file_system_rstudio_shiny_share_security_group_id,
            mutable=True,
        )

        file_system_rstudio_shiny_share = efs.FileSystem.from_file_system_attributes(
            self,
            id=f"Rstudio-Shiny-EFS-File-System-Share-{instance}",
            file_system_id=file_system_rstudio_shiny_share_file_system_id,
            security_group=efs_security_group_share,
        )

        access_point_rstudio_shiny_share = efs.AccessPoint.from_access_point_attributes(
            self,
            id=f"access-point-rstudio-shiny-share-{instance}",
            access_point_id=access_point_id_rstudio_shiny_share,
            file_system=file_system_rstudio_shiny_share,
        )

        volume_config_rstudio_shiny_share = ecs.Volume(
            name=f"efs-volume-rstudio-shiny-share-{instance}",
            efs_volume_configuration=ecs.EfsVolumeConfiguration(
                file_system_id=file_system_rstudio_shiny_share.file_system_id,
                transit_encryption="ENABLED",
                authorization_config=ecs.AuthorizationConfig(
                    access_point_id=access_point_rstudio_shiny_share.access_point_id,
                ),
            ),
        )

        # Configure the hourly sync file system volume

        efs_security_group_hourly = ec2.SecurityGroup.from_security_group_id(
            self,
            id=f"Efs-SG-hourly-{instance}",
            security_group_id=file_system_rstudio_hourly_security_group_id,
            mutable=True,
        )

        file_system_rstudio_hourly = efs.FileSystem.from_file_system_attributes(
            self,
            id=f"Rstudio-Fargate-EFS-File-System-Hourly-{instance}",
            file_system_id=file_system_rstudio_hourly_file_system_id,
            security_group=efs_security_group_hourly,
        )

        access_point_rstudio_hourly = efs.AccessPoint.from_access_point_attributes(
            self,
            id=f"access-point-rstudio-fg-hourly-{instance}",
            access_point_id=access_point_id_rstudio_hourly,
            file_system=file_system_rstudio_hourly,
        )

        volume_config_rstudio_hourly = ecs.Volume(
            name=f"efs-volume-rstudio-fg-hourly-{instance}",
            efs_volume_configuration=ecs.EfsVolumeConfiguration(
                file_system_id=file_system_rstudio_hourly.file_system_id,
                transit_encryption="ENABLED",
                authorization_config=ecs.AuthorizationConfig(
                    access_point_id=access_point_rstudio_hourly.access_point_id,
                ),
            ),
        )

        # Configure the instant sync file system volume

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

        access_point_rstudio_instant = efs.AccessPoint.from_access_point_attributes(
            self,
            id=f"access-point-rstudio-fg-instant-{instance}",
            access_point_id=access_point_id_rstudio_instant,
            file_system=file_system_rstudio_instant,
        )

        volume_config_rstudio_instant = ecs.Volume(
            name=f"efs-volume-rstudio-fg-instant-{instance}",
            efs_volume_configuration=ecs.EfsVolumeConfiguration(
                file_system_id=file_system_rstudio_instant.file_system_id,
                transit_encryption="ENABLED",
                authorization_config=ecs.AuthorizationConfig(
                    access_point_id=access_point_rstudio_instant.access_point_id,
                ),
            ),
        )

        rstudio_cloudwatch_log_kms_key_alias = kms.Alias.from_alias_name(
            self,
            id=f"Rstudio-Cw-logs-key-{instance}",
            alias_name=f"alias/cwlogs-rstudio-{instance}",
        )

        rstudio_zone = r53.PublicHostedZone.from_hosted_zone_attributes(
            self,
            id=f"Rstudio-zone-{instance}",
            hosted_zone_id=rstudio_hosted_zone_id,
            zone_name=rstudio_hosted_zone_name,
        )

        cert = acm.Certificate.from_certificate_arn(
            self,
            id=f"Rstudio-instance-cert-{instance}",
            certificate_arn=rstudio_cert_arn,
        )

        cluster_fg = ecs.Cluster.from_cluster_attributes(
            self,
            f"Rstudio-fg-ecs-cluster-{instance}",
            cluster_name=ecs_cluster_name,
            vpc=vpc,
            security_groups=[],
        )

        rstudio_load_balancer_arn_list = []
        secretpass_arn_list = []

        for i in range(1, number_of_rstudio_containers + 1):

            # RStudio Instance Home File System
            file_system_rstudio_home = efs.FileSystem(
                self,
                id=f"Rstudio{i}-cont-user-home-{instance}",
                file_system_name=f"Rstudio{i}-cont-fs-home-{instance}",
                vpc=vpc,
                encrypted=True,
                kms_key=rstudio_efs_kms_key_alias,
                performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
                throughput_mode=efs.ThroughputMode.BURSTING,
                enable_automatic_backups=True,
                removal_policy=RemovalPolicy.DESTROY,
            )

            access_point_rstudio_home = efs.AccessPoint(
                self,
                id=f"Rstudio{i}-access-point-home-{instance}",
                file_system=file_system_rstudio_home,
                path=f"/rstudio{i}-path-home",
                create_acl=efs.Acl(
                    owner_uid="1000", owner_gid="1000", permissions="755"
                ),
            )

            volume_config_rstudio_home = ecs.Volume(
                name=f"efs-volume-rstudio{i}-home-{instance}",
                efs_volume_configuration=ecs.EfsVolumeConfiguration(
                    file_system_id=file_system_rstudio_home.file_system_id,
                    transit_encryption="ENABLED",
                    authorization_config=ecs.AuthorizationConfig(
                        access_point_id=access_point_rstudio_home.access_point_id,
                    ),
                ),
            )

            rstudio_logs_container = logs.LogGroup(
                self,
                id=f"rstudio{i}-cw-logs-container-{instance}",
                log_group_name=f"Rstudio{i}-cont-fg-{instance}/{id}",
                removal_policy=RemovalPolicy.DESTROY,
                retention=logs.RetentionDays.ONE_WEEK,
                encryption_key=rstudio_cloudwatch_log_kms_key_alias,
            )

            rstudio_task = ecs.FargateTaskDefinition(
                self,
                id=f"Rstudio{i}-fg-task-{instance}",
                memory_limit_mib=cont_mem,
                cpu=cont_cpu,
                volumes=[
                    volume_config_rstudio_home,
                    volume_config_rstudio_shiny_share,
                    volume_config_rstudio_hourly,
                    volume_config_rstudio_instant,
                ],
            )

            rstudio_secret = sm.Secret(
                self,
                id=f"Rstudio{i}-Pass-{instance}",
                secret_name=f"rstudio{i}/passwd/{instance}",
                encryption_key=encryption_key,
                removal_policy=cdk.RemovalPolicy.DESTROY,
            )

            secret_vars = {
                "RSTUDIO_PASS": ecs.Secret.from_secrets_manager(rstudio_secret),
            }

            rstudio_container = rstudio_task.add_container(
                f"Rstudio{i}-fg-{instance}",
                image=ecs.ContainerImage.from_ecr_repository(rstudio_image_repo),
                environment=envvars_cont,
                secrets=secret_vars,
                memory_limit_mib=cont_mem,
                logging=ecs.LogDrivers.aws_logs(
                    stream_prefix=f"Rstudio{i}-fg-{instance}",
                    log_group=rstudio_logs_container,
                ),
                linux_parameters=ecs.LinuxParameters(
                    self,
                    id=f"Rstudio{i}-linux-params-{instance}",
                    init_process_enabled=True,
                ),
            )

            rstudio_container.add_port_mappings(
                ecs.PortMapping(container_port=8787),
                ecs.PortMapping(container_port=3838),
            )

            rstudio_container.add_mount_points(
                ecs.MountPoint(
                    container_path=home_container_path,
                    source_volume=volume_config_rstudio_home.name,
                    read_only=False,
                ),
                ecs.MountPoint(
                    container_path=shiny_share_container_path,
                    source_volume=volume_config_rstudio_shiny_share.name,
                    read_only=False,
                ),
                ecs.MountPoint(
                    container_path=hourly_sync_container_path,
                    source_volume=volume_config_rstudio_hourly.name,
                    read_only=False,
                ),
                ecs.MountPoint(
                    container_path=instant_sync_container_path,
                    source_volume=volume_config_rstudio_instant.name,
                    read_only=False,
                ),
            )

            rstudio_task.add_to_task_role_policy(
                PolicyStatement(
                    actions=[
                        "ssmmessages:CreateControlChannel",
                        "ssmmessages:CreateDataChannel",
                        "ssmmessages:OpenControlChannel",
                        "ssmmessages:OpenDataChannel",
                    ],
                    effect=Effect.ALLOW,
                    resources=["*"],
                )
            )

            rstudio_logs_container.node.add_dependency(
                rstudio_cloudwatch_log_kms_key_alias
            )

            rstudio_container.node.add_dependency(rstudio_logs_container)

            rstudio_container.node.add_dependency(rstudio_task)

            rstudio_individual_domain = f"container{i}.{rstudio_zone.zone_name}"

            individual_zone = r53.PublicHostedZone(
                self,
                id=f"route53-individual-Rstudio{i}-zone-{instance}",
                zone_name=rstudio_individual_domain,
            )

            rstudio_recordset = r53.RecordSet(
                self,
                id=f"ns-rstudio{i}-individual-record-set-{instance}",
                zone=rstudio_zone,
                record_type=RecordType.NS,
                target=RecordTarget.from_values(
                    *individual_zone.hosted_zone_name_servers
                ),
                record_name=rstudio_individual_domain,
            )

            rstudio_recordset.node.add_dependency(individual_zone)

            rstudio_service = ecs_patterns.ApplicationLoadBalancedFargateService(
                self,
                id=f"Rstudio{i}-fg-service-{instance}",
                cluster=cluster_fg,
                memory_limit_mib=cont_mem,
                cpu=cont_cpu,
                task_definition=rstudio_task,
                desired_count=1,
                certificate=cert,
                domain_name=individual_zone.zone_name,
                domain_zone=individual_zone,
                protocol=ApplicationProtocol.HTTPS,
                platform_version=ecs.FargatePlatformVersion.VERSION1_4,
                health_check_grace_period=cdk.Duration.seconds(900),
            )

            rstudio_kms_policy = iam.PolicyStatement(
                actions=[
                    "kms:Decrypt",
                    "kms:DescribeKey",
                    "kms:Encrypt",
                    "kms:ReEncrypt*",
                    "kms:GenerateDataKey*",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            )

            rstudio_secret_policy = iam.PolicyStatement(
                actions=[
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret",
                ],
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:*rstudio*"
                ],
            )

            rstudio_service.task_definition.add_to_task_role_policy(rstudio_kms_policy)
            rstudio_service.task_definition.add_to_task_role_policy(
                rstudio_secret_policy
            )
            rstudio_service.task_definition.add_to_execution_role_policy(
                rstudio_kms_policy
            )
            rstudio_service.task_definition.add_to_execution_role_policy(
                rstudio_secret_policy
            )

            encryption_key.grant_decrypt(
                rstudio_service.task_definition.obtain_execution_role()
            )  # Grant decrypt to task definition

            rstudio_secret.grant_read(
                rstudio_service.task_definition.obtain_execution_role()
            )

            rstudio_service.node.add_dependency(rstudio_container)

            rstudio_service.target_group.configure_health_check(
                healthy_http_codes="200,301,302"
            )

            cfn_service = rstudio_service.service.node.default_child
            cfn_service.add_override("Properties.EnableExecuteCommand", True)

            file_system_rstudio_hourly.connections.allow_from(
                rstudio_service.service, Port.tcp(2049)
            )
            file_system_rstudio_home.connections.allow_from(
                rstudio_service.service, Port.tcp(2049)
            )
            file_system_rstudio_instant.connections.allow_from(
                rstudio_service.service, Port.tcp(2049)
            )
            file_system_rstudio_shiny_share.connections.allow_from(
                rstudio_service.service, Port.tcp(2049)
            )

            rstudio_load_balancer_arn_list.append(
                rstudio_service.load_balancer.load_balancer_arn
            )
            secretpass_arn_list.append(rstudio_secret.secret_arn)

        # Pass variables to other stacks

        self.rstudio_load_balancer_arn = []
        self.secretpass_arn = []

        self.rstudio_load_balancer_arn = rstudio_load_balancer_arn_list
        self.secretpass_arn = secretpass_arn_list
