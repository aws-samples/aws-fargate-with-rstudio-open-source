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
    aws_route53 as r53,
    aws_certificatemanager as acm,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_wafv2 as waf,
    aws_efs as efs,
    aws_logs as logs,
    aws_secretsmanager as sm,
    aws_kms as kms,
    aws_iam as iam,
)
from aws_cdk.core import RemovalPolicy, Duration
from aws_cdk.aws_ec2 import Port
from aws_cdk.aws_elasticloadbalancingv2 import ApplicationProtocol
from aws_cdk.aws_ecr import Repository
from aws_cdk.aws_iam import PolicyStatement, Effect


class PackageEC2Stack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        vpc: ec2.Vpc,
        instance: str,
        pm_db_cluster_secret_arn: str,
        pm_usage_db_cluster_secret_arn: str,
        package_file_system_id: str,
        package_efs_security_group_id: str,
        package_efs_access_point_id: str,
        package_hosted_zone_id: str,
        package_hosted_zone_name: str,
        package_cert_arn: str,
        ecs_cluster_name: str,
        ecs_cluster_security_group_id: str,
        package_container_repository_name: str,
        package_container_repository_arn: str,
        db_domain_suffix: str,
        packagae_cwlogs_key_alias: str,
        package_db_key_alias: str,
        rspm_license_key_secret_name: str,
        rspm_min_capacity: int,
        rspm_desired_capacity: int,
        rspm_max_capacity: int,
        rspm_cont_mem_reserved: int,
        rspm_cookie_stickiness_duration: int,
        rspm_health_check_grace_period: int,
        rspm_scale_in_cooldown: int,
        rspm_scale_out_cooldown: int,
        rspm_cpu_target_utilization_percent: int,
        rspm_memory_target_utilization_percent: int,
        rspm_requests_per_target: int,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        package_image_repo = Repository.from_repository_attributes(
            self,
            id=f"Package-Docker-Image-Repo-{instance}",
            repository_arn=package_container_repository_arn,
            repository_name=package_container_repository_name,
        )

        encryption_key = kms.Alias.from_alias_name(
            self,
            id=f"Encryption-Key-{instance}",
            alias_name=package_db_key_alias,
        )

        pm_db_secret = sm.Secret.from_secret_attributes(
            self,
            id=f"aurora-pg-pm-db-secret-{instance}",
            secret_arn=pm_db_cluster_secret_arn,
            encryption_key=encryption_key,
        )

        pm_usage_db_secret = sm.Secret.from_secret_attributes(
            self,
            f"aurora-pg-pm-usage-db-secret-{instance}",
            secret_arn=pm_usage_db_cluster_secret_arn,
            encryption_key=encryption_key,
        )

        package_licesne_secret = sm.Secret.from_secret_name_v2(
            self,
            id=f"package-licesne-secret-{instance}",
            secret_name=rspm_license_key_secret_name,
        )

        secret_vars = {
            "PM_DB_SECRET": ecs.Secret.from_secrets_manager(
                secret=pm_db_secret, field="password"
            ),
            "PM_DB_HOST": ecs.Secret.from_secrets_manager(
                secret=pm_db_secret, field="host"
            ),
            "PM_DB_USER": ecs.Secret.from_secrets_manager(
                secret=pm_db_secret, field="username"
            ),
            "PM_DB_NAME": ecs.Secret.from_secrets_manager(
                secret=pm_db_secret, field="dbname"
            ),
            "PM_USAGE_DB_SECRET": ecs.Secret.from_secrets_manager(
                secret=pm_usage_db_secret, field="password"
            ),
            "PM_USAGE_DB_HOST": ecs.Secret.from_secrets_manager(
                secret=pm_usage_db_secret, field="host"
            ),
            "PM_USAGE_DB_USER": ecs.Secret.from_secrets_manager(
                secret=pm_usage_db_secret, field="username"
            ),
            "PM_USAGE_DB_NAME": ecs.Secret.from_secrets_manager(
                secret=pm_usage_db_secret, field="dbname"
            ),
            "RSPM_LICENSE": ecs.Secret.from_secrets_manager(package_licesne_secret),
        }

        package_asg_security_group = ec2.SecurityGroup.from_security_group_id(
            self,
            id=f"Connect-EC2-ASG-Security-Group-{instance}",
            security_group_id=ecs_cluster_security_group_id,
        )

        package_zone = r53.PublicHostedZone.from_hosted_zone_attributes(
            self,
            id=f"Package-sage-zone-{instance}",
            hosted_zone_id=package_hosted_zone_id,
            zone_name=package_hosted_zone_name,
        )

        package_cert = acm.Certificate.from_certificate_arn(
            self,
            id=f"Package-ec2-cert-{instance}",
            certificate_arn=package_cert_arn,
        )

        pm_db_domain_suffix = f"pm.{instance}.{db_domain_suffix}"

        envvars_package_cont = {
            "DB_DOMAIN_SUFFIX": pm_db_domain_suffix,
        }

        package_cluster_ec2 = ecs.Cluster.from_cluster_attributes(
            self,
            id=f"Connect-ec2-ecs-cluster-{instance}",
            cluster_name=ecs_cluster_name,
            vpc=vpc,
            security_groups=[package_asg_security_group],
        )

        package_efs_security_group = ec2.SecurityGroup.from_security_group_id(
            self,
            id=f"Efs-SG-package-{instance}",
            security_group_id=package_efs_security_group_id,
            mutable=True,
        )

        file_system_package_ec2 = efs.FileSystem.from_file_system_attributes(
            self,
            id=f"Package-cont-ec2-user-data-{instance}",
            file_system_id=package_file_system_id,
            security_group=package_efs_security_group,
        )

        access_point_package_ec2 = efs.AccessPoint.from_access_point_attributes(
            self,
            id=f"Package-ec2-access-point-{instance}",
            access_point_id=package_efs_access_point_id,
            file_system=file_system_package_ec2,
        )

        volume_config_package_ec2 = ecs.Volume(
            name=f"efs-volume-package-{instance}",
            efs_volume_configuration=ecs.EfsVolumeConfiguration(
                file_system_id=file_system_package_ec2.file_system_id,
                transit_encryption="ENABLED",
                authorization_config=ecs.AuthorizationConfig(
                    access_point_id=access_point_package_ec2.access_point_id,
                ),
            ),
        )

        package_cloudwatch_log_kms_key_alias = kms.Alias.from_alias_name(
            self,
            id=f"Package-Cw-kms-key-{instance}",
            alias_name=packagae_cwlogs_key_alias,
        )

        package_logs_container = logs.LogGroup(
            self,
            id=f"package-ec2-cw-logs-container-{instance}",
            log_group_name=f"Package-cont-ec2-{instance}/{id}",
            removal_policy=RemovalPolicy.DESTROY,
            retention=logs.RetentionDays.ONE_WEEK,
            encryption_key=package_cloudwatch_log_kms_key_alias,
        )

        package_task_ec2 = ecs.Ec2TaskDefinition(
            self,
            id=f"Package-ec2-task-{instance}",
            volumes=[volume_config_package_ec2],
        )

        package_task_ec2.add_to_task_role_policy(
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

        package_container_ec2 = package_task_ec2.add_container(
            f"RSPM-ec2-{instance}",
            image=ecs.ContainerImage.from_ecr_repository(package_image_repo),
            environment=envvars_package_cont,
            secrets=secret_vars,
            memory_reservation_mib=rspm_cont_mem_reserved,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix=f"Package-ec2-{instance}",
                log_group=package_logs_container,
            ),
            linux_parameters=ecs.LinuxParameters(
                self,
                id=f"RSPM-linux-params-{instance}",
                init_process_enabled=True,
            ),
            privileged=True,
        )

        package_container_ec2.node.add_dependency(package_logs_container)

        package_container_ec2.node.add_dependency(package_task_ec2)

        package_container_ec2.add_port_mappings(
            ecs.PortMapping(container_port=4242),
        )

        package_container_ec2.add_mount_points(
            ecs.MountPoint(
                container_path="/efs",
                source_volume=volume_config_package_ec2.name,
                read_only=False,
            )
        )

        listener_package_ec2 = f"package-ec2-listener-{instance}"

        package_service_ec2 = ecs_patterns.ApplicationMultipleTargetGroupsEc2Service(
            self,
            id=f"Package-ec2-service-{instance}",
            cluster=package_cluster_ec2,
            task_definition=package_task_ec2,
            desired_count=rspm_desired_capacity,
            load_balancers=[
                ecs_patterns.ApplicationLoadBalancerProps(
                    listeners=[
                        ecs_patterns.ApplicationListenerProps(
                            name=listener_package_ec2,
                            certificate=package_cert,
                            protocol=ApplicationProtocol.HTTPS,
                        )
                    ],
                    name=f"Package-ec2-LB-{instance}",
                    domain_name=package_zone.zone_name,
                    domain_zone=package_zone,
                )
            ],
            target_groups=[
                ecs_patterns.ApplicationTargetProps(container_port=4242),
            ],
            health_check_grace_period=cdk.Duration.seconds(
                rspm_health_check_grace_period
            ),
        )

        package_service_ec2.node.add_dependency(package_container_ec2)

        package_service_ec2.target_group.configure_health_check(path="/__ping__")

        package_service_ec2.target_group.enable_cookie_stickiness(
            cdk.Duration.hours(rspm_cookie_stickiness_duration),
        )

        cfn_service = package_service_ec2.service.node.default_child
        cfn_service.add_override("Properties.EnableExecuteCommand", True)

        package_scalable_target = package_service_ec2.service.auto_scale_task_count(
            min_capacity=rspm_min_capacity,
            max_capacity=rspm_max_capacity,  # Increase the max capacity in parameters.json to allow more containers depending on the EC2 instance size and number of EC2 instances in the ASG
        )

        package_scalable_target.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=rspm_cpu_target_utilization_percent,
            scale_in_cooldown=cdk.Duration.seconds(rspm_scale_in_cooldown),
            scale_out_cooldown=cdk.Duration.seconds(rspm_scale_out_cooldown),
        )

        package_scalable_target.scale_on_memory_utilization(
            "MemoryScaling",
            target_utilization_percent=rspm_memory_target_utilization_percent,
            scale_in_cooldown=cdk.Duration.seconds(rspm_scale_in_cooldown),
            scale_out_cooldown=cdk.Duration.seconds(rspm_scale_out_cooldown),
        )

        package_scalable_target.scale_on_request_count(
            "RequestCountScaling",
            requests_per_target=rspm_requests_per_target,
            target_group=package_service_ec2.target_group,
            scale_in_cooldown=cdk.Duration.seconds(rspm_scale_in_cooldown),
            scale_out_cooldown=cdk.Duration.seconds(rspm_scale_out_cooldown),
        )

        package_kms_policy = iam.PolicyStatement(
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

        package_secret_policy = iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
            effect=iam.Effect.ALLOW,
            resources=[
                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:*package*"
            ],
        )

        package_service_ec2.task_definition.add_to_execution_role_policy(
            package_kms_policy
        )
        package_service_ec2.task_definition.add_to_task_role_policy(
            package_secret_policy
        )
        package_service_ec2.task_definition.add_to_execution_role_policy(
            package_kms_policy
        )
        package_service_ec2.task_definition.add_to_execution_role_policy(
            package_secret_policy
        )

        pm_usage_db_secret.grant_read(
            package_service_ec2.task_definition.obtain_execution_role()
        )

        pm_db_secret.grant_read(
            package_service_ec2.task_definition.obtain_execution_role()
        )

        package_licesne_secret.grant_read(
            package_service_ec2.task_definition.obtain_execution_role()
        )

        file_system_package_ec2.connections.allow_from(
            package_service_ec2.service, Port.tcp(2049)
        )

        # Pass stack variables to other stacks

        self.package_load_balancer_arn = (
            package_service_ec2.load_balancer.load_balancer_arn
        )
