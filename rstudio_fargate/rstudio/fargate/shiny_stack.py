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

from ..custom.ssm_custom_resource import SSMParameterReader

from aws_cdk import (
    core as cdk,
    aws_route53 as r53,
    aws_route53_targets as route53_targets,
    aws_certificatemanager as acm,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_efs as efs,
    aws_logs as logs,
    aws_secretsmanager as sm,
    aws_kms as kms,
    aws_ssm as ssm,
)
from aws_cdk.core import RemovalPolicy, Duration
from aws_cdk.aws_route53 import RecordType, RecordTarget
from aws_cdk.aws_ec2 import Port
from aws_cdk.aws_elasticloadbalancingv2 import ApplicationProtocol
from aws_cdk.aws_ecr import Repository
from aws_cdk.aws_iam import PolicyStatement, Effect


class ShinyStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        instance: str,
        vpc: ec2.Vpc,
        file_system_shiny_home_file_system_id: str,
        file_system_shiny_home_security_group_id: str,
        access_point_id_shiny_home: str,
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
        shiny_cert_arn: str,
        shiny_hosted_zone_id: str,
        shiny_hosted_zone_name: str,
        ecs_cluster_name: str,
        shiny_container_repository_name_ssm_param: str,
        shiny_container_repository_arn_ssm_param: str,
        ssm_cross_account_role_name: str,
        ssm_cross_account_lambda_role_name: str,
        shiny_cwlogs_key_alias: str,
        shiny_min_capacity: int,
        shiny_desired_capacity: int,
        shiny_max_capacity: int,
        shiny_container_memory_in_gb: int,
        shiny_health_check_grace_period: int,
        shiny_cookie_stickiness_duration: int,
        shiny_scale_in_cooldown: int,
        shiny_scale_out_cooldown: int,
        shiny_cpu_target_utilization_percent: int,
        shiny_memory_target_utilization_percent: int,
        shiny_requests_per_target: int,
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
            parameter_name=shiny_container_repository_name_ssm_param,
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
            parameter_name=shiny_container_repository_arn_ssm_param,
            region=self.region,
            instance=instance,
            rstudio_account_id=self.account,
            network_account_id=network_account_id,
            rstudio_pipeline_account_id=rstudio_pipeline_account_id,
            cross_account_id=rstudio_pipeline_account_id,
            ssm_cross_account_role_name=ssm_cross_account_role_name,
            ssm_cross_account_lambda_role_name=ssm_cross_account_lambda_role_name,
        )

        shiny_repository_name = ssm_repo_name_reader.get_parameter_value()

        shiny_repository_arn = ssm_repo_arn_reader.get_parameter_value()

        shiny_image_repo = Repository.from_repository_attributes(
            self,
            id=f"Shiny-Docker-Image-Repo-{instance}",
            repository_arn=shiny_repository_arn,
            repository_name=shiny_repository_name,
        )

        if shiny_container_memory_in_gb < 1:
            cont_cpu = 256
        elif 1 <= shiny_container_memory_in_gb <= 2:
            cont_cpu = 512
        elif 2 < shiny_container_memory_in_gb <= 8:
            cont_cpu = 1024
        elif 8 < shiny_container_memory_in_gb <= 16:
            cont_cpu = 2048
        elif 16 < shiny_container_memory_in_gb <= 32:
            cont_cpu = 4096

        cont_mem = shiny_container_memory_in_gb * 1024

        cluster_fg = ecs.Cluster.from_cluster_attributes(
            self,
            id=f"Shiny-fg-ecs-cluster-{instance}",
            cluster_name=ecs_cluster_name,
            vpc=vpc,
            security_groups=[],
        )

        # Configure the Shiny home file system volume

        efs_security_group_home = ec2.SecurityGroup.from_security_group_id(
            self,
            id=f"Shiny-Efs-SG-Home-{instance}",
            security_group_id=file_system_shiny_home_security_group_id,
            mutable=True,
        )

        file_system_shiny_home = efs.FileSystem.from_file_system_attributes(
            self,
            id=f"Shiny-EFS-Home-{instance}",
            file_system_id=file_system_shiny_home_file_system_id,
            security_group=efs_security_group_home,
        )

        access_point_shiny_home = efs.AccessPoint.from_access_point_attributes(
            self,
            id=f"access-point-shiny-homme-{instance}",
            access_point_id=access_point_id_shiny_home,
            file_system=file_system_shiny_home,
        )

        volume_config_shiny_home = ecs.Volume(
            name=f"efs-volume-shiny-home-{instance}",
            efs_volume_configuration=ecs.EfsVolumeConfiguration(
                file_system_id=file_system_shiny_home.file_system_id,
                transit_encryption="ENABLED",
                authorization_config=ecs.AuthorizationConfig(
                    access_point_id=access_point_shiny_home.access_point_id,
                ),
            ),
        )

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

        shiny_cloudwatch_log_kms_key_alias = kms.Alias.from_alias_name(
            self,
            id="Shiny-Cw-logs-key-{instance}",
            alias_name=shiny_cwlogs_key_alias,
        )

        shiny_logs_container = logs.LogGroup(
            self,
            id=f"shiny-cw-logs-container-{instance}",
            log_group_name=f"Shiny-cont-fg-{instance}/{id}",
            removal_policy=RemovalPolicy.DESTROY,
            retention=logs.RetentionDays.ONE_WEEK,
            encryption_key=shiny_cloudwatch_log_kms_key_alias,
        )

        shiny_logs_container.node.add_dependency(shiny_cloudwatch_log_kms_key_alias)

        shiny_task_fg = ecs.FargateTaskDefinition(
            self,
            id=f"Shiny-fg-task-{instance}",
            memory_limit_mib=cont_mem,
            cpu=cont_cpu,
            volumes=[
                volume_config_shiny_home,
                volume_config_rstudio_shiny_share,
                volume_config_rstudio_hourly,
                volume_config_rstudio_instant,
            ],
        )

        shiny_task_fg.add_to_task_role_policy(
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

        shiny_container_fg = shiny_task_fg.add_container(
            id=f"Shiny-fg-{instance}",
            image=ecs.ContainerImage.from_ecr_repository(shiny_image_repo),
            memory_limit_mib=cont_mem,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix=f"Shiny-fg-{instance}",
                log_group=shiny_logs_container,
            ),
            linux_parameters=ecs.LinuxParameters(
                self,
                id=f"Shiny-linux-params-{instance}",
                init_process_enabled=True,
            ),
        )

        shiny_container_fg.node.add_dependency(shiny_logs_container)

        shiny_container_fg.node.add_dependency(shiny_task_fg)

        shiny_container_fg.add_port_mappings(
            ecs.PortMapping(container_port=3838),
        )

        shiny_container_fg.add_mount_points(
            ecs.MountPoint(
                container_path=home_container_path,
                source_volume=volume_config_shiny_home.name,
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

        shiny_zone_fg = r53.PublicHostedZone.from_hosted_zone_attributes(
            self,
            id=f"Shiny-zone-{instance}",
            hosted_zone_id=shiny_hosted_zone_id,
            zone_name=shiny_hosted_zone_name,
        )

        cert = acm.Certificate.from_certificate_arn(
            self,
            id=f"Shiny-instance-cert-{instance}",
            certificate_arn=shiny_cert_arn,
        )

        shiny_service_fg = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            id=f"Shiny-fg-service-{instance}",
            cluster=cluster_fg,
            memory_limit_mib=cont_mem,
            cpu=cont_cpu,
            task_definition=shiny_task_fg,
            desired_count=shiny_desired_capacity,
            certificate=cert,
            domain_name=shiny_zone_fg.zone_name,
            domain_zone=shiny_zone_fg,
            protocol=ApplicationProtocol.HTTPS,
            platform_version=ecs.FargatePlatformVersion.VERSION1_4,
            health_check_grace_period=cdk.Duration.seconds(
                shiny_health_check_grace_period
            ),
        )

        shiny_service_fg.node.add_dependency(shiny_container_fg)

        shiny_service_fg.target_group.configure_health_check(
            healthy_http_codes="200,301,302"
        )

        shiny_service_fg.target_group.enable_cookie_stickiness(
            cdk.Duration.hours(shiny_cookie_stickiness_duration),
        )

        cfn_service = shiny_service_fg.service.node.default_child
        cfn_service.add_override("Properties.EnableExecuteCommand", True)

        shiny_scalable_target = shiny_service_fg.service.auto_scale_task_count(
            min_capacity=shiny_min_capacity,
            max_capacity=shiny_max_capacity,
        )

        shiny_scalable_target.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=shiny_cpu_target_utilization_percent,
            scale_in_cooldown=cdk.Duration.seconds(shiny_scale_in_cooldown),
            scale_out_cooldown=cdk.Duration.seconds(shiny_scale_out_cooldown),
        )

        shiny_scalable_target.scale_on_memory_utilization(
            "MemoryScaling",
            target_utilization_percent=shiny_memory_target_utilization_percent,
            scale_in_cooldown=cdk.Duration.seconds(shiny_scale_in_cooldown),
            scale_out_cooldown=cdk.Duration.seconds(shiny_scale_out_cooldown),
        )

        shiny_scalable_target.scale_on_request_count(
            "RequestCountScaling",
            requests_per_target=shiny_requests_per_target,
            target_group=shiny_service_fg.target_group,
            scale_in_cooldown=cdk.Duration.seconds(shiny_scale_in_cooldown),
            scale_out_cooldown=cdk.Duration.seconds(shiny_scale_out_cooldown),
        )

        file_system_shiny_home.connections.allow_from(
            shiny_service_fg.service, Port.tcp(2049)
        )
        file_system_rstudio_shiny_share.connections.allow_from(
            shiny_service_fg.service, Port.tcp(2049)
        )
        file_system_rstudio_hourly.connections.allow_from(
            shiny_service_fg.service, Port.tcp(2049)
        )
        file_system_rstudio_instant.connections.allow_from(
            shiny_service_fg.service, Port.tcp(2049)
        )

        self.shiny_load_balancer_arn = shiny_service_fg.load_balancer.load_balancer_arn
