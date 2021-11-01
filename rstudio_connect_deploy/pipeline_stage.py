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
from aws_cdk.core import Fn

from .route53_stack import Route53Stack
from .vpc_stack import VpcStack
from .kms_stack import KmsStack
from .connect_db_stack import ConnectRdsStack
from .package_db_stack import PMRdsStack
from .ecs_cluster_stack import EcsClusterStack
from .connect_efs_stack import ConnectEfsStack
from .package_efs_stack import PackageEfsStack
from .connect_ec2_stack import ConnectEC2Stack
from .package_ec2_stack import PackageEC2Stack
from .connect_waf_stack import ConnectWafStack
from .package_waf_stack import PackageWafStack


class PipelineStage(cdk.Stage):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        instance: str,
        r53_base_domain: str,
        ec2_instance_type: str,
        vpc_cidr: str,
        allowed_ips: str,
        sns_email: str,
        db_domain_suffix: str,
        connect_cwlogs_key_alias: str,
        packagae_cwlogs_key_alias: str,
        connect_efs_key_alias: str,
        package_efs_key_alias: str,
        connect_db_key_alias: str,
        package_db_key_alias: str,
        rsc_license_key_secret_name: str,
        rspm_license_key_secret_name: str,
        asg_min_capacity: int,
        asg_desired_capacity: int,
        asg_max_capacity: int,
        rsc_min_capacity: int,
        rsc_desired_capacity: int,
        rsc_max_capacity: int,
        rsc_cont_mem_reserved: int,
        rspm_min_capacity: int,
        rspm_desired_capacity: int,
        rspm_max_capacity: int,
        rspm_cont_mem_reserved: int,
        rsc_cookie_stickiness_duration: int,
        rsc_health_check_grace_period: int,
        rspm_cookie_stickiness_duration: int,
        rspm_health_check_grace_period: int,
        rsc_scale_in_cooldown: int,
        rsc_scale_out_cooldown: int,
        rsc_cpu_target_utilization_percent: int,
        rsc_memory_target_utilization_percent: int,
        rsc_requests_per_target: int,
        rspm_scale_in_cooldown: int,
        rspm_scale_out_cooldown: int,
        rspm_cpu_target_utilization_percent: int,
        rspm_memory_target_utilization_percent: int,
        rspm_requests_per_target: int,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        env_dict = {
            "account": self.account,
            "region": self.region,
        }

        connect_container_repository_name = Fn.import_value(
            f"Connect-ECR-Repo-Name-{instance}"
        )
        connect_container_repository_arn = Fn.import_value(
            f"Connect-ECR-Repo-Arn-{instance}"
        )
        package_container_repository_name = Fn.import_value(
            f"Package-ECR-Repo-Name-{instance}"
        )
        package_container_repository_arn = Fn.import_value(
            f"Package-ECR-Repo-Arn-{instance}"
        )

        r53_stack_build = Route53Stack(
            self,
            id=f"r53-RSC-RSPM-{instance}",
            instance=instance,
            r53_base_domain=r53_base_domain,
            env=env_dict,
        )

        vpc_stack_build = VpcStack(
            self,
            id=f"VPC-RSC-RSPM-{instance}",
            instance=instance,
            vpc_cidr=vpc_cidr,
            env=env_dict,
        )

        kms_stack_build = KmsStack(
            self,
            id=f"Kms-RSC-RSPM-{instance}",
            instance=instance,
            connect_cwlogs_key_alias=connect_cwlogs_key_alias,
            packagae_cwlogs_key_alias=packagae_cwlogs_key_alias,
            connect_efs_key_alias=connect_efs_key_alias,
            package_efs_key_alias=package_efs_key_alias,
            connect_db_key_alias=connect_db_key_alias,
            package_db_key_alias=package_db_key_alias,
            env=env_dict,
        )

        connect_efs_stack_build = ConnectEfsStack(
            self,
            id=f"Efs-RSC-{instance}",
            instance=instance,
            vpc=vpc_stack_build.vpc,
            connect_efs_key_alias=connect_efs_key_alias,
            env=env_dict,
        )

        package_efs_stack_build = PackageEfsStack(
            self,
            id=f"Efs-RSPM-{instance}",
            instance=instance,
            vpc=vpc_stack_build.vpc,
            package_efs_key_alias=package_efs_key_alias,
            env=env_dict,
        )

        ecs_cluster_stack_build = EcsClusterStack(
            self,
            id=f"Ecs-RSC-RSPM-{instance}",
            instance=instance,
            ec2_instance_type=ec2_instance_type,
            vpc=vpc_stack_build.vpc,
            asg_min_capacity=asg_min_capacity,
            asg_desired_capacity=asg_desired_capacity,
            asg_max_capacity=asg_max_capacity,
            env=env_dict,
        )

        connect_db_stack_build = ConnectRdsStack(
            self,
            id=f"RdsDb-RSC-{instance}",
            instance=instance,
            vpc=vpc_stack_build.vpc,
            db_domain_suffix=db_domain_suffix,
            connect_db_key_alias=connect_db_key_alias,
            env=env_dict,
        )

        package_db_stack_build = PMRdsStack(
            self,
            id=f"RdsDb-RSPM-{instance}",
            instance=instance,
            vpc=vpc_stack_build.vpc,
            db_domain_suffix=db_domain_suffix,
            package_db_key_alias=package_db_key_alias,
            env=env_dict,
        )

        connect_ec2_stack_build = ConnectEC2Stack(
            self,
            id=f"EC2-RSC-{instance}",
            instance=instance,
            vpc=vpc_stack_build.vpc,
            connect_db_cluster_secret_arn=connect_db_stack_build.connect_db_cluster_secret_arn,
            connect_file_system_id=connect_efs_stack_build.connect_file_system_id,
            connect_efs_security_group_id=connect_efs_stack_build.connect_efs_security_group_id,
            connect_efs_access_point_id=connect_efs_stack_build.connect_efs_access_point_id,
            connect_hosted_zone_id=r53_stack_build.connect_hosted_zone_id,
            connect_hosted_zone_name=r53_stack_build.connect_hosted_zone_name,
            connect_cert_arn=r53_stack_build.cert_arn,
            ecs_cluster_name=ecs_cluster_stack_build.ecs_cluster_name,
            ecs_cluster_security_group_id=ecs_cluster_stack_build.ecs_cluster_security_group_id,
            connect_container_repository_name=connect_container_repository_name,
            connect_container_repository_arn=connect_container_repository_arn,
            db_domain_suffix=db_domain_suffix,
            connect_cwlogs_key_alias=connect_cwlogs_key_alias,
            connect_db_key_alias=connect_db_key_alias,
            rsc_license_key_secret_name=rsc_license_key_secret_name,
            rsc_min_capacity=rsc_min_capacity,
            rsc_desired_capacity=rsc_desired_capacity,
            rsc_max_capacity=rsc_max_capacity,
            rsc_cont_mem_reserved=rsc_cont_mem_reserved,
            rsc_cookie_stickiness_duration=rsc_cookie_stickiness_duration,
            rsc_health_check_grace_period=rsc_health_check_grace_period,
            rsc_scale_in_cooldown=rsc_scale_in_cooldown,
            rsc_scale_out_cooldown=rsc_scale_out_cooldown,
            rsc_cpu_target_utilization_percent=rsc_cpu_target_utilization_percent,
            rsc_memory_target_utilization_percent=rsc_memory_target_utilization_percent,
            rsc_requests_per_target=rsc_requests_per_target,
            env=env_dict,
        )

        package_ec2_stack_build = PackageEC2Stack(
            self,
            id=f"EC2-RSPM-{instance}",
            instance=instance,
            vpc=vpc_stack_build.vpc,
            pm_db_cluster_secret_arn=package_db_stack_build.pm_db_cluster_secret_arn,
            pm_usage_db_cluster_secret_arn=package_db_stack_build.pm_usage_db_cluster_secret_arn,
            package_file_system_id=package_efs_stack_build.package_file_system_id,
            package_efs_security_group_id=package_efs_stack_build.package_efs_security_group_id,
            package_efs_access_point_id=package_efs_stack_build.package_efs_access_point_id,
            package_hosted_zone_id=r53_stack_build.package_hosted_zone_id,
            package_hosted_zone_name=r53_stack_build.package_hosted_zone_name,
            package_cert_arn=r53_stack_build.cert_arn,
            ecs_cluster_name=ecs_cluster_stack_build.ecs_cluster_name,
            ecs_cluster_security_group_id=ecs_cluster_stack_build.ecs_cluster_security_group_id,
            package_container_repository_name=package_container_repository_name,
            package_container_repository_arn=package_container_repository_arn,
            db_domain_suffix=db_domain_suffix,
            packagae_cwlogs_key_alias=packagae_cwlogs_key_alias,
            package_db_key_alias=package_db_key_alias,
            rspm_license_key_secret_name=rspm_license_key_secret_name,
            rspm_min_capacity=rspm_min_capacity,
            rspm_desired_capacity=rspm_desired_capacity,
            rspm_max_capacity=rspm_max_capacity,
            rspm_cont_mem_reserved=rspm_cont_mem_reserved,
            rspm_cookie_stickiness_duration=rspm_cookie_stickiness_duration,
            rspm_health_check_grace_period=rspm_health_check_grace_period,
            rspm_scale_in_cooldown=rspm_scale_in_cooldown,
            rspm_scale_out_cooldown=rspm_scale_out_cooldown,
            rspm_cpu_target_utilization_percent=rspm_cpu_target_utilization_percent,
            rspm_memory_target_utilization_percent=rspm_memory_target_utilization_percent,
            rspm_requests_per_target=rspm_requests_per_target,
            env=env_dict,
        )

        connect_waf_stack_build = ConnectWafStack(
            self,
            id=f"Waf-RSC-{instance}",
            instance=instance,
            connect_load_balancer_arn=connect_ec2_stack_build.connect_load_balancer_arn,
            allowed_ips=allowed_ips,
            env=env_dict,
        )

        package_waf_stack_build = PackageWafStack(
            self,
            id=f"Waf-RSPM-{instance}",
            instance=instance,
            package_load_balancer_arn=package_ec2_stack_build.package_load_balancer_arn,
            allowed_ips=allowed_ips,
            env=env_dict,
        )

        ecs_cluster_stack_build.add_dependency(vpc_stack_build)
        connect_efs_stack_build.add_dependency(vpc_stack_build)
        package_efs_stack_build.add_dependency(vpc_stack_build)
        connect_db_stack_build.add_dependency(vpc_stack_build)
        package_db_stack_build.add_dependency(vpc_stack_build)
        connect_ec2_stack_build.add_dependency(ecs_cluster_stack_build)
        connect_ec2_stack_build.add_dependency(connect_efs_stack_build)
        connect_ec2_stack_build.add_dependency(connect_db_stack_build)
        package_ec2_stack_build.add_dependency(ecs_cluster_stack_build)
        package_ec2_stack_build.add_dependency(package_efs_stack_build)
        package_ec2_stack_build.add_dependency(package_db_stack_build)
        connect_waf_stack_build.add_dependency(connect_ec2_stack_build)
        package_waf_stack_build.add_dependency(package_ec2_stack_build)
