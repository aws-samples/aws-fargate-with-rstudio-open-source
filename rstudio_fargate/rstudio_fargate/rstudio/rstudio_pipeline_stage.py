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

from aws_cdk import core
from aws_cdk import core as cdk
from .route53.rstudio_instance_domain_stack import RstudioInstanceDomainStack
from .vpc.rstudio_vpc_stack import RstudioVpcStack
from .kms.rstudio_kms_stack import RstudioKmsStack
from .ecs.rstudio_ecs_cluster_stack import RstudioEcsClusterStack
from .fargate.rstudio_bastion_fargate_stack import RstudioBastionFargateStack
from .fargate.rstudio_fargate_stack import RstudioFargateStack
from .fargate.rstudio_ec2_stack import RstudioEC2Stack
from .fargate.rstudio_shiny_stack import RstudioShinyStack
from .efs.rstudio_efs_stack import RstudioEfsStack
from .fargate.rstudio_build_docker_images import RstudioBuildDockerImagesStack
from .waf.rstudio_waf_stack import RstudioWafStack
from .datasync.rstudio_datasync_stack import RstudioDataSyncStack
from .ses.rstudio_email_passwords_stack import RstudioEmailPasswordsStack

class RstudioPipelineStage(core.Stage):
    def __init__(self, scope: core.Construct, 
        id: str,
        instances: list,
        rstudio_account_ids: list,
        rstudio_install_types: list,
        rstudio_individual_containers: list,
        rstudio_container_memory_in_gb: list,
        shiny_container_memory_in_gb: list,
        rstudio_ec2_instance_types: list,
        pipeline_unique_id: str,
        **kwargs):
        super().__init__(scope, id, **kwargs)

        
        env_dict={
                "account":self.account,
                "region":self.region,
            }

        
        
        # Create docker image assets from ECR repo
        rstudio_docker_stack_build=RstudioBuildDockerImagesStack(
                self,
                'Rstudio-Docker-Build',
                env=env_dict
            )
        
        
        for i in range(len(instances)):
            instance=instances[i]
            rstudio_account_id=rstudio_account_ids[i]
            rstudio_install_type=rstudio_install_types[i]
            rstudio_individual_container=rstudio_individual_containers[i]
            rstudio_container_memory=rstudio_container_memory_in_gb[i]
            shiny_container_memory=shiny_container_memory_in_gb[i]
            rstudio_ec2_instance_type=rstudio_ec2_instance_types[i]
            
            rstudio_individual_container = eval(rstudio_individual_container.title())
            
            env_dict={
                "account":rstudio_account_id,
                "region":self.region,
            }
            route53_instance_stack_build = RstudioInstanceDomainStack(
                self, 
                'Route53-Instance-RstudioStack-' + instance,
                instance,
                rstudio_account_id,
                pipeline_unique_id=pipeline_unique_id,
                env=env_dict,
            )
            
            vpc_stack_build = RstudioVpcStack(
                self, 
                'VPC-RstudioStack-' + instance,
                instance=instance,
                env=env_dict,
            )
    
            kms_stack_build = RstudioKmsStack(
                self, 
                'Kms-RstudioStack-' + instance,
                instance,
                env=env_dict,
            )
            
            efs_stack_build = RstudioEfsStack( 
                self, 
                'Efs-RstudioStack-' + instance,
                vpc_stack_build.vpc,
                instance,
                rstudio_individual_containers=rstudio_individual_container,
                rstudio_install_type=rstudio_install_type,
                env=env_dict,
            )

            rstudio_datasync_stack_build = RstudioDataSyncStack(
                self, 
                'Datasync-RstudioStack-' + instance,
                instance=instance,
                vpc=vpc_stack_build.vpc,
                file_system_rstudio_fg_instant_file_system_id=efs_stack_build.file_system_rstudio_fg_instant_file_system_id,
                file_system_rstudio_fg_instant_security_group_id=efs_stack_build.file_system_rstudio_fg_instant_security_group_id,
                env=env_dict,
            )
    
            ecs_cluster_stack_build = RstudioEcsClusterStack(
                self, 
                'EcsCluster-' + instance,
                vpc_stack_build.vpc,
                instance,
                rstudio_install_type,
                rstudio_ec2_instance_type,
                env=env_dict,
            )            
    
            bastion_fargate_stack_build = RstudioBastionFargateStack(
                self, 
                'Bastion-Fargate-RstudioStack-' + instance,
                shared_vpc=vpc_stack_build.vpc,
                instance=instance,
                rstudio_pipeline_account_id=self.account,
                env=env_dict,
            )
    
            if rstudio_install_type == "fargate":
                rstudio_fargate_stack_build = RstudioFargateStack(
                    self, 
                    'Fargate-RstudioStack-' + instance,
                    vpc_stack_build.vpc,
                    file_system_rstudio_fg_instant_file_system_id=efs_stack_build.file_system_rstudio_fg_instant_file_system_id,
                    file_system_rstudio_fg_instant_security_group_id=efs_stack_build.file_system_rstudio_fg_instant_security_group_id,
                    access_point_id_rstudio_fg_instant=efs_stack_build.access_point_id_rstudio_fg_instant,
                    instance=instance,
                    rstudio_pipeline_account_id=self.account,
                    rstudio_individual_container=rstudio_individual_container,
                    cont_mem=int(rstudio_container_memory),
                    env=env_dict,
                )

            if rstudio_install_type == "ec2":
                rstudio_ec2_stack_build = RstudioEC2Stack(
                    self, 
                    'EC2-RstudioStack-' + instance,
                    vpc_stack_build.vpc,
                    file_system_rstudio_fg_instant_file_system_id=efs_stack_build.file_system_rstudio_fg_instant_file_system_id,
                    file_system_rstudio_fg_instant_security_group_id=efs_stack_build.file_system_rstudio_fg_instant_security_group_id,
                    access_point_id_rstudio_fg_instant=efs_stack_build.access_point_id_rstudio_fg_instant,
                    instance=instance,
                    rstudio_pipeline_account_id=self.account,
                    cont_mem=int(rstudio_container_memory),
                    env=env_dict,
                )
    
            shiny_fargate_stack_build = RstudioShinyStack(
                self, 
                'Fargate-ShinyStack-' + instance,
                vpc_stack_build.vpc,
                file_system_rstudio_fg_instant_file_system_id=efs_stack_build.file_system_rstudio_fg_instant_file_system_id,
                file_system_rstudio_fg_instant_security_group_id=efs_stack_build.file_system_rstudio_fg_instant_security_group_id,
                access_point_id_rstudio_fg_instant=efs_stack_build.access_point_id_rstudio_fg_instant,
                instance=instance,
                rstudio_pipeline_account_id=self.account,
                cont_mem=int(shiny_container_memory),
                env=env_dict,
            )
            
            rstudio_waf_stack_build = RstudioWafStack(
                self, 
                'Waf-RstudioStack-' + instance,
                instance=instance,
                rstudio_individual_container=rstudio_individual_container,
                env=env_dict,
            )

            rstudio_email_passwords_stack_build = RstudioEmailPasswordsStack(
                self, 
                "Rstudio-Email-Passwords-Stack" + instance,
                instance=instance,
                rstudio_install_type=rstudio_install_type,
                rstudio_individual_container=rstudio_individual_container,
                env=env_dict
            )
    
            ecs_cluster_stack_build.add_dependency(vpc_stack_build)
            efs_stack_build.add_dependency(vpc_stack_build)
            bastion_fargate_stack_build.add_dependency(ecs_cluster_stack_build)
            bastion_fargate_stack_build.add_dependency(kms_stack_build)
            bastion_fargate_stack_build.add_dependency(vpc_stack_build)
            rstudio_datasync_stack_build.add_dependency(efs_stack_build)

            if rstudio_install_type == "fargate":
                rstudio_fargate_stack_build.add_dependency(ecs_cluster_stack_build)
                rstudio_fargate_stack_build.add_dependency(route53_instance_stack_build)
                rstudio_fargate_stack_build.add_dependency(bastion_fargate_stack_build)
                rstudio_waf_stack_build.add_dependency(rstudio_fargate_stack_build)

            if rstudio_install_type == "ec2":
                rstudio_ec2_stack_build.add_dependency(ecs_cluster_stack_build)
                rstudio_ec2_stack_build.add_dependency(route53_instance_stack_build)
                rstudio_ec2_stack_build.add_dependency(bastion_fargate_stack_build)
                rstudio_waf_stack_build.add_dependency(rstudio_ec2_stack_build)
                

            shiny_fargate_stack_build.add_dependency(route53_instance_stack_build)
            shiny_fargate_stack_build.add_dependency(ecs_cluster_stack_build)
            shiny_fargate_stack_build.add_dependency(bastion_fargate_stack_build)

            rstudio_waf_stack_build.add_dependency(shiny_fargate_stack_build)
            rstudio_email_passwords_stack_build.add_dependency(rstudio_waf_stack_build)
