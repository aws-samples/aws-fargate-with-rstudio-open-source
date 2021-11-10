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
from aws_cdk import core as cdk

from .route53.rstudio_instance_domain_stack import InstanceDomainStack
from .vpc.vpc_stack import VpcStack
from .kms.kms_stack import KmsStack
from .ecs.ecs_cluster_stack import EcsClusterStack
from .efs.rstudio_efs_stack import RstudioEfsStack
from .efs.shiny_efs_stack import ShinyEfsStack
from .fargate.rstudio_ec2_stack import RstudioEc2Stack
from .fargate.rstudio_fargate_stack import RstudioFargateStack
from .fargate.shiny_stack import ShinyStack
from .waf.rstudio_waf_stack import RstudioWafStack
from .waf.shiny_waf_stack import ShinyWafStack
from .datasync.datasync_stack import DataSyncStack
from .ses.rstudio_email_passwords_stack import RstudioEmailPasswordsStack


class PipelineStage(cdk.Stage):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        instance: str,
        rstudio_account_id: str,
        network_account_id: str,
        datalake_account_id: str,
        rstudio_install_type: str,
        rstudio_ec2_instance_type: str,
        rstudio_container_memory_in_gb: int,
        number_of_rstudio_containers: int,
        vpc_cidr_range: str,
        allowed_ips: str,
        sns_email: str,
        datalake_source_bucket_name: str,
        athena_output_bucket_name: str,
        athena_workgroup_name: str,
        lambda_datasync_trigger_function_arn: str,
        ssm_cross_account_role_name: str,
        ssm_cross_account_lambda_role_name: str,
        datasync_task_arn_ssm_param_name: str,
        datasync_function_name: str,
        rstudio_container_repository_name_ssm_param: str,
        rstudio_container_repository_arn_ssm_param: str,
        shiny_container_repository_name_ssm_param: str,
        shiny_container_repository_arn_ssm_param: str,
        ssm_route53_delegation_name: str,
        ssm_route53_delegation_id: str,
        r53_delegation_role_name: str,
        ecs_cluster_name: str,
        rstudio_cwlogs_key_alias: str,
        shiny_cwlogs_key_alias: str,
        rstudio_efs_key_alias: str,
        shiny_efs_key_alias: str,
        rstudio_user_key_alias: str,
        asg_min_capacity: int,
        asg_desired_capacity: int,
        asg_max_capacity: int,
        shiny_min_capacity: int,
        shiny_desired_capacity: int,
        shiny_max_capacity: int,
        shiny_container_memory_in_gb: int,
        rstudio_container_memory_reserved: int,
        rstudio_health_check_grace_period: int,
        shiny_health_check_grace_period: int,
        shiny_cookie_stickiness_duration: int,
        shiny_scale_in_cooldown: int,
        shiny_scale_out_cooldown: int,
        shiny_cpu_target_utilization_percent: int,
        shiny_memory_target_utilization_percent: int,
        shiny_requests_per_target: int,
        datalake_source_bucket_key_hourly: str,
        access_point_path_hourly: str,
        datalake_source_bucket_key_instant: str,
        access_point_path_instant: str,
        athena_output_bucket_key: str,
        home_container_path: str,
        shiny_share_container_path: str,
        hourly_sync_container_path: str,
        instant_sync_container_path: str,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        env_dict = {
            "account": rstudio_account_id,
            "region": self.region,
        }

        route53_instance_stack_build = InstanceDomainStack(
            self,
            id=f"Route53-Instance-Rstudio-Shiny-{instance}",
            instance=instance,
            rstudio_account_id=rstudio_account_id,
            rstudio_pipeline_account_id=self.account,
            network_account_id=network_account_id,
            ssm_route53_delegation_name=ssm_route53_delegation_name,
            ssm_route53_delegation_id=ssm_route53_delegation_id,
            r53_delegation_role_name=r53_delegation_role_name,
            ssm_cross_account_role_name=ssm_cross_account_role_name,
            ssm_cross_account_lambda_role_name=ssm_cross_account_lambda_role_name,
            env=env_dict,
        )

        vpc_stack_build = VpcStack(
            self,
            id=f"VPC-Rstudio-Shiny-{instance}",
            instance=instance,
            vpc_cidr_range=vpc_cidr_range,
            env=env_dict,
        )

        kms_stack_build = KmsStack(
            self,
            id=f"Kms-Rstudio-Shiny-{instance}",
            instance=instance,
            rstudio_cwlogs_key_alias=rstudio_cwlogs_key_alias,
            shiny_cwlogs_key_alias=shiny_cwlogs_key_alias,
            rstudio_efs_key_alias=rstudio_efs_key_alias,
            shiny_efs_key_alias=shiny_efs_key_alias,
            rstudio_user_key_alias=rstudio_user_key_alias,
            env=env_dict,
        )

        rstudio_efs_stack_build = RstudioEfsStack(
            self,
            id=f"Efs-RstudioStack-{instance}",
            vpc=vpc_stack_build.vpc,
            instance=instance,
            rstudio_efs_key_alias=rstudio_efs_key_alias,
            access_point_path_hourly=access_point_path_hourly,
            access_point_path_instant=access_point_path_instant,
            env=env_dict,
        )

        shiny_efs_stack_build = ShinyEfsStack(
            self,
            id=f"Efs-ShinyStack-{instance}",
            vpc=vpc_stack_build.vpc,
            instance=instance,
            shiny_efs_key_alias=shiny_efs_key_alias,
            env=env_dict,
        )

        ecs_cluster_stack_build = EcsClusterStack(
            self,
            id=f"Rstudio-Shiny-EcsCluster-{instance}",
            vpc=vpc_stack_build.vpc,
            instance=instance,
            rstudio_install_type=rstudio_install_type,
            rstudio_ec2_instance_type=rstudio_ec2_instance_type,
            ecs_cluster_name=ecs_cluster_name,
            asg_min_capacity=asg_min_capacity,
            asg_desired_capacity=asg_desired_capacity,
            asg_max_capacity=asg_max_capacity,
            env=env_dict,
        )

        if rstudio_install_type == "ec2":
            rstudio_stack_build = RstudioEc2Stack(
                self,
                id=f"RstudioEc2Stack-{instance}",
                vpc=vpc_stack_build.vpc,
                instance=instance,
                file_system_rstudio_shiny_share_file_system_id=rstudio_efs_stack_build.file_system_rstudio_shiny_share_file_system_id,
                file_system_rstudio_shiny_share_security_group_id=rstudio_efs_stack_build.file_system_rstudio_shiny_share_security_group_id,
                access_point_id_rstudio_shiny_share=rstudio_efs_stack_build.access_point_id_rstudio_shiny_share,
                file_system_rstudio_hourly_file_system_id=rstudio_efs_stack_build.file_system_rstudio_hourly_file_system_id,
                file_system_rstudio_hourly_security_group_id=rstudio_efs_stack_build.file_system_rstudio_hourly_security_group_id,
                access_point_id_rstudio_hourly=rstudio_efs_stack_build.access_point_id_rstudio_hourly,
                file_system_rstudio_instant_file_system_id=rstudio_efs_stack_build.file_system_rstudio_instant_file_system_id,
                file_system_rstudio_instant_security_group_id=rstudio_efs_stack_build.file_system_rstudio_instant_security_group_id,
                access_point_id_rstudio_instant=rstudio_efs_stack_build.access_point_id_rstudio_instant,
                rstudio_pipeline_account_id=self.account,
                network_account_id=network_account_id,
                rstudio_cert_arn=route53_instance_stack_build.rstudio_cert_arn,
                rstudio_hosted_zone_id=route53_instance_stack_build.rstudio_hosted_zone_id,
                rstudio_hosted_zone_name=route53_instance_stack_build.rstudio_hosted_zone_name,
                ecs_cluster_security_group_id=ecs_cluster_stack_build.ecs_cluster_security_group_id,
                ecs_cluster_name=ecs_cluster_stack_build.ecs_cluster_name,
                rstudio_container_repository_name_ssm_param=rstudio_container_repository_name_ssm_param,
                rstudio_container_repository_arn_ssm_param=rstudio_container_repository_arn_ssm_param,
                ssm_cross_account_role_name=ssm_cross_account_role_name,
                ssm_cross_account_lambda_role_name=ssm_cross_account_lambda_role_name,
                athena_output_bucket_name=athena_output_bucket_name,
                athena_workgroup_name=athena_workgroup_name,
                number_of_rstudio_containers=number_of_rstudio_containers,
                rstudio_cwlogs_key_alias=rstudio_cwlogs_key_alias,
                rstudio_efs_key_alias=rstudio_efs_key_alias,
                rstudio_user_key_alias=rstudio_user_key_alias,
                rstudio_container_memory_reserved=rstudio_container_memory_reserved,
                rstudio_health_check_grace_period=rstudio_health_check_grace_period,
                home_container_path=home_container_path,
                shiny_share_container_path=shiny_share_container_path,
                hourly_sync_container_path=hourly_sync_container_path,
                instant_sync_container_path=instant_sync_container_path,
                env=env_dict,
            )

        if rstudio_install_type == "fargate":
            rstudio_stack_build = RstudioFargateStack(
                self,
                id=f"RstudioFargateStack-{instance}",
                vpc=vpc_stack_build.vpc,
                instance=instance,
                file_system_rstudio_shiny_share_file_system_id=rstudio_efs_stack_build.file_system_rstudio_shiny_share_file_system_id,
                file_system_rstudio_shiny_share_security_group_id=rstudio_efs_stack_build.file_system_rstudio_shiny_share_security_group_id,
                access_point_id_rstudio_shiny_share=rstudio_efs_stack_build.access_point_id_rstudio_shiny_share,
                file_system_rstudio_hourly_file_system_id=rstudio_efs_stack_build.file_system_rstudio_hourly_file_system_id,
                file_system_rstudio_hourly_security_group_id=rstudio_efs_stack_build.file_system_rstudio_hourly_security_group_id,
                access_point_id_rstudio_hourly=rstudio_efs_stack_build.access_point_id_rstudio_hourly,
                file_system_rstudio_instant_file_system_id=rstudio_efs_stack_build.file_system_rstudio_instant_file_system_id,
                file_system_rstudio_instant_security_group_id=rstudio_efs_stack_build.file_system_rstudio_instant_security_group_id,
                access_point_id_rstudio_instant=rstudio_efs_stack_build.access_point_id_rstudio_instant,
                rstudio_pipeline_account_id=self.account,
                network_account_id=network_account_id,
                rstudio_container_memory_in_gb=rstudio_container_memory_in_gb,
                rstudio_cert_arn=route53_instance_stack_build.rstudio_cert_arn,
                rstudio_hosted_zone_id=route53_instance_stack_build.rstudio_hosted_zone_id,
                rstudio_hosted_zone_name=route53_instance_stack_build.rstudio_hosted_zone_name,
                ecs_cluster_security_group_id=ecs_cluster_stack_build.ecs_cluster_security_group_id,
                ecs_cluster_name=ecs_cluster_stack_build.ecs_cluster_name,
                rstudio_container_repository_name_ssm_param=rstudio_container_repository_name_ssm_param,
                rstudio_container_repository_arn_ssm_param=rstudio_container_repository_arn_ssm_param,
                athena_output_bucket_name=athena_output_bucket_name,
                athena_workgroup_name=athena_workgroup_name,
                ssm_cross_account_role_name=ssm_cross_account_role_name,
                ssm_cross_account_lambda_role_name=ssm_cross_account_lambda_role_name,
                number_of_rstudio_containers=number_of_rstudio_containers,
                rstudio_cwlogs_key_alias=rstudio_cwlogs_key_alias,
                rstudio_efs_key_alias=rstudio_efs_key_alias,
                rstudio_user_key_alias=rstudio_user_key_alias,
                rstudio_health_check_grace_period=rstudio_health_check_grace_period,
                home_container_path=home_container_path,
                shiny_share_container_path=shiny_share_container_path,
                hourly_sync_container_path=hourly_sync_container_path,
                instant_sync_container_path=instant_sync_container_path,
                env=env_dict,
            )

        shiny_fargate_stack_build = ShinyStack(
            self,
            id=f"Fargate-ShinyStack-{instance}",
            vpc=vpc_stack_build.vpc,
            instance=instance,
            file_system_shiny_home_file_system_id=shiny_efs_stack_build.file_system_shiny_home_file_system_id,
            file_system_shiny_home_security_group_id=shiny_efs_stack_build.file_system_shiny_home_security_group_id,
            access_point_id_shiny_home=shiny_efs_stack_build.access_point_id_shiny_home,
            file_system_rstudio_shiny_share_file_system_id=rstudio_efs_stack_build.file_system_rstudio_shiny_share_file_system_id,
            file_system_rstudio_shiny_share_security_group_id=rstudio_efs_stack_build.file_system_rstudio_shiny_share_security_group_id,
            access_point_id_rstudio_shiny_share=rstudio_efs_stack_build.access_point_id_rstudio_shiny_share,
            file_system_rstudio_hourly_file_system_id=rstudio_efs_stack_build.file_system_rstudio_hourly_file_system_id,
            file_system_rstudio_hourly_security_group_id=rstudio_efs_stack_build.file_system_rstudio_hourly_security_group_id,
            access_point_id_rstudio_hourly=rstudio_efs_stack_build.access_point_id_rstudio_hourly,
            file_system_rstudio_instant_file_system_id=rstudio_efs_stack_build.file_system_rstudio_instant_file_system_id,
            file_system_rstudio_instant_security_group_id=rstudio_efs_stack_build.file_system_rstudio_instant_security_group_id,
            access_point_id_rstudio_instant=rstudio_efs_stack_build.access_point_id_rstudio_instant,
            rstudio_pipeline_account_id=self.account,
            network_account_id=network_account_id,
            shiny_cert_arn=route53_instance_stack_build.shiny_cert_arn,
            shiny_hosted_zone_id=route53_instance_stack_build.shiny_hosted_zone_id,
            shiny_hosted_zone_name=route53_instance_stack_build.shiny_hosted_zone_name,
            ecs_cluster_name=ecs_cluster_stack_build.ecs_cluster_name,
            shiny_container_repository_name_ssm_param=shiny_container_repository_name_ssm_param,
            shiny_container_repository_arn_ssm_param=shiny_container_repository_arn_ssm_param,
            ssm_cross_account_role_name=ssm_cross_account_role_name,
            ssm_cross_account_lambda_role_name=ssm_cross_account_lambda_role_name,
            shiny_cwlogs_key_alias=shiny_cwlogs_key_alias,
            shiny_min_capacity=shiny_min_capacity,
            shiny_desired_capacity=shiny_desired_capacity,
            shiny_max_capacity=shiny_max_capacity,
            shiny_container_memory_in_gb=shiny_container_memory_in_gb,
            shiny_health_check_grace_period=shiny_health_check_grace_period,
            shiny_cookie_stickiness_duration=shiny_cookie_stickiness_duration,
            shiny_scale_in_cooldown=shiny_scale_in_cooldown,
            shiny_scale_out_cooldown=shiny_scale_out_cooldown,
            shiny_cpu_target_utilization_percent=shiny_cpu_target_utilization_percent,
            shiny_memory_target_utilization_percent=shiny_memory_target_utilization_percent,
            shiny_requests_per_target=shiny_requests_per_target,
            home_container_path=home_container_path,
            shiny_share_container_path=shiny_share_container_path,
            hourly_sync_container_path=hourly_sync_container_path,
            instant_sync_container_path=instant_sync_container_path,
            env=env_dict,
        )

        datasync_stack_build = DataSyncStack(
            self,
            id=f"Datasync-RstudioStack-{instance}",
            instance=instance,
            vpc=vpc_stack_build.vpc,
            file_system_rstudio_hourly_file_system_id=rstudio_efs_stack_build.file_system_rstudio_hourly_file_system_id,
            file_system_rstudio_hourly_security_group_id=rstudio_efs_stack_build.file_system_rstudio_hourly_security_group_id,
            file_system_rstudio_instant_file_system_id=rstudio_efs_stack_build.file_system_rstudio_instant_file_system_id,
            file_system_rstudio_instant_security_group_id=rstudio_efs_stack_build.file_system_rstudio_instant_security_group_id,
            datalake_source_bucket_name=datalake_source_bucket_name,
            datasync_task_arn_ssm_param_name=datasync_task_arn_ssm_param_name,
            datalake_source_bucket_key_hourly=datalake_source_bucket_key_hourly,
            access_point_path_hourly=access_point_path_hourly,
            datalake_source_bucket_key_instant=datalake_source_bucket_key_instant,
            access_point_path_instant=access_point_path_instant,
            env=env_dict,
        )

        rstudio_waf_stack_build = RstudioWafStack(
            self,
            id=f"Waf-RstudioStack-{instance}",
            instance=instance,
            rstudio_load_balancer_arn=rstudio_stack_build.rstudio_load_balancer_arn,
            allowed_ips=allowed_ips,
            env=env_dict,
        )

        shiny_waf_stack_build = ShinyWafStack(
            self,
            id=f"Waf-ShinyStack-{instance}",
            instance=instance,
            shiny_load_balancer_arn=shiny_fargate_stack_build.shiny_load_balancer_arn,
            allowed_ips=allowed_ips,
            env=env_dict,
        )

        ses_email_stack_build = RstudioEmailPasswordsStack(
            self,
            id=f"Rstudio-SesEmailStack-{instance}",
            instance=instance,
            rstudio_hosted_zone_id=route53_instance_stack_build.rstudio_hosted_zone_id,
            rstudio_hosted_zone_name=route53_instance_stack_build.rstudio_hosted_zone_name,
            shiny_hosted_zone_id=route53_instance_stack_build.shiny_hosted_zone_id,
            shiny_hosted_zone_name=route53_instance_stack_build.shiny_hosted_zone_name,
            sns_email=sns_email,
            secretpass_arn=rstudio_stack_build.secretpass_arn,
            number_of_rstudio_containers=number_of_rstudio_containers,
            rstudio_user_key_alias=rstudio_user_key_alias,
            env=env_dict,
        )

        ecs_cluster_stack_build.add_dependency(vpc_stack_build)
        rstudio_efs_stack_build.add_dependency(vpc_stack_build)
        shiny_efs_stack_build.add_dependency(vpc_stack_build)

        rstudio_stack_build.add_dependency(route53_instance_stack_build)
        rstudio_stack_build.add_dependency(ecs_cluster_stack_build)
        rstudio_stack_build.add_dependency(rstudio_efs_stack_build)

        shiny_fargate_stack_build.add_dependency(route53_instance_stack_build)
        shiny_fargate_stack_build.add_dependency(ecs_cluster_stack_build)
        shiny_fargate_stack_build.add_dependency(rstudio_efs_stack_build)
        shiny_fargate_stack_build.add_dependency(shiny_efs_stack_build)

        datasync_stack_build.add_dependency(rstudio_efs_stack_build)
        rstudio_waf_stack_build.add_dependency(rstudio_stack_build)
        shiny_waf_stack_build.add_dependency(shiny_fargate_stack_build)
        ses_email_stack_build.add_dependency(rstudio_stack_build)
