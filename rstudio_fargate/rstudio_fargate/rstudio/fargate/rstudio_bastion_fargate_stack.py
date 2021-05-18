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
from aws_cdk.core import Fn, RemovalPolicy,Duration,CfnOutput
from aws_cdk import aws_ec2 as ec2
from aws_cdk.aws_ec2 import Port
from aws_cdk import aws_ecs as ecs
from aws_cdk.aws_ecr_assets import DockerImageAsset
from aws_cdk import aws_efs as efs
from aws_cdk import aws_logs as logs
from aws_cdk import aws_secretsmanager as sm
import aws_cdk.aws_kms as kms
from aws_cdk.aws_ecr import Repository

class RstudioBastionFargateStack(cdk.Stack):
        def __init__(self, scope: cdk.Construct, 
                    id: str, 
                    shared_vpc: ec2.Vpc,
                    instance: str,
                    rstudio_pipeline_account_id: str,
                    **kwargs) -> None:
            super().__init__(scope, id, **kwargs)

            ssh_image_repo_name = self.node.try_get_context("ssh_image_repo_name")

            if ssh_image_repo_name is None:
                raise ValueError("Please provide ssh server docker image ecr repository name")
                
            bastion_client_ip = self.node.try_get_context("bastion_client_ip_range")

            if bastion_client_ip is None:
                raise ValueError("Please provide client ip range allowed to access bastion fargate ssh server")

                
            ecs_cluster_name = Fn.import_value(f'Rstudio-Cluster-Export-{instance}')

            pubkey_arn = self.node.try_get_context("public_key_arn")

            if pubkey_arn is None:
                raise ValueError("Please provide public key of key pair secret manager ARN)")

            encryption_key_arn = self.node.try_get_context("encryption_key_arn")

            if encryption_key_arn is None:
                raise ValueError("Please provide encryption key arn")
                
            encryption_key=kms.Key.from_key_arn(self, 'Encryption-Key', key_arn=encryption_key_arn)
            
            pubkey = sm.Secret.from_secret_attributes(
                self, 
                "ImportedSecretPubKey",
                secret_arn=pubkey_arn,
                encryption_key=encryption_key
                )

            bastion_fg_asset = DockerImageAsset(
                self, 
                'Bastion-fg-image-' + instance,
                directory="./docimage-openssh",
                file='Dockerfile', 
                build_args={
                    'AWS_ACCOUNT': rstudio_pipeline_account_id,
                    'AWS_REGION': self.region,
                    'IMAGE_REPO': ssh_image_repo_name
                    }     
                ) 
            
            """
            ssh_repository_arn=f'arn:aws:ecr:{self.region}:{rstudio_pipeline_account_id}:repository/{ssh_image_repo_name}'
            
            ssh_image_repo = Repository.from_repository_arn(self, 
                                id=f'Ssh-Docker-Image-Repo-{instance}',
                                repository_arn=ssh_repository_arn
            )

            """

            
            envvars_bast_fg = {
                'PUID' : '1000',
                #'PUBLIC_KEY': pub_key,
                'SUDO_ACCESS': 'true',
                'PASSWORD_ACCESS': 'false',
                'USER_NAME': 'ec2-user'              
                }

            secret_vars={
                    'PUBLIC_KEY': ecs.Secret.from_secrets_manager(pubkey) 
                }
            file_system_bastion_fg = efs.FileSystem(
                self, 
                f'Bastion-rstudio-fg-user-data-{instance}',
                file_system_name=f'Bastion-rstudio-fg-fs-{instance}',
                vpc=shared_vpc,
                encrypted=True,
                performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
                throughput_mode=efs.ThroughputMode.BURSTING,
                removal_policy=RemovalPolicy.DESTROY,                
            )

            access_point_bastion_fg = efs.AccessPoint(
                self, 
                f'Bastion-fg-access-point-{instance}',
                file_system=file_system_bastion_fg,
                path= '/Bastion-path-fg',
                create_acl=efs.Acl(owner_uid= '1000', owner_gid= '1000', permissions= '755'),    
            )

            volume_config_bastion_fg = ecs.Volume(
                name= f'efs-volume-bastion-fg-{instance}',
                efs_volume_configuration=ecs.EfsVolumeConfiguration(
                    file_system_id=file_system_bastion_fg.file_system_id,
                    transit_encryption='ENABLED',
                    authorization_config=ecs.AuthorizationConfig(
                        access_point_id=access_point_bastion_fg.access_point_id,
                    )
                )
            )

            bastion_cloudwatch_log_kms_key_alias = kms.Alias.from_alias_name(
                self,
                'Bastion-Cw-' + instance, 
                alias_name= f'alias/cwlogs-bastion-rstudio-{instance}'
                )

            bastion_logs_container = logs.LogGroup(
                self,
                f'bastion-fg-cw-logs-container-{instance}',
                log_group_name=f'Bastion-rstudio-fg-{instance}/{id}',
                removal_policy=RemovalPolicy.DESTROY,
                retention=logs.RetentionDays.ONE_WEEK,
                encryption_key=bastion_cloudwatch_log_kms_key_alias,
            )

            cluster_fg = ecs.Cluster.from_cluster_attributes(
                self, 
                f'Bastion-fg-ecs-cluster-{instance}',
                cluster_name=ecs_cluster_name,
                vpc=shared_vpc,
                security_groups=[],
                )

            bastion_task_fg = ecs.FargateTaskDefinition(
                self, 
                f'Bastion-fg-task-{instance}',
                memory_limit_mib=512,
                cpu=256,
                volumes=[volume_config_bastion_fg],
            )

            
            bastion_container_fg = bastion_task_fg.add_container(
                f'Bastion-fg-{instance}', 
                #image=ecs.ContainerImage.from_ecr_repository(ssh_image_repo), 
                image=ecs.ContainerImage.from_docker_image_asset(bastion_fg_asset),
                environment=envvars_bast_fg,
                secrets=secret_vars,
                memory_limit_mib=512,
                logging=ecs.LogDrivers.aws_logs(
                    stream_prefix=f'Bastion-fg-{instance}', 
                    log_group=bastion_logs_container
                ),
            )

            bastion_container_fg.node.add_dependency(bastion_logs_container)

            bastion_container_fg.node.add_dependency(bastion_task_fg)

            bastion_container_fg.add_port_mappings(
                ecs.PortMapping(
                    container_port=8787),
            )

            bastion_container_fg.add_mount_points(
                ecs.MountPoint(
                    container_path='/home',
                    source_volume=volume_config_bastion_fg.name,
                    read_only=False,
                 )
            )

            bastion_fg_security_group = ec2.SecurityGroup(
                self, 
                f'Fargate-BastionSecurityGroup-{instance}',
                vpc=shared_vpc,
                description='Allow ssh access to bastion fargate instances',
                allow_all_outbound=True,
            )

            bastion_fg_security_group.add_ingress_rule(ec2.Peer.ipv4(bastion_client_ip), ec2.Port.tcp(22), 'allow ssh access from approved IP')

            bastion_service_fg = ecs.FargateService(
                self, 
                f'Bastion-Service-Fg-{instance}',
                cluster= cluster_fg,
                task_definition=bastion_task_fg,
                desired_count=1,
                vpc_subnets=ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PUBLIC
                ),
                assign_public_ip=True,
                security_groups=[bastion_fg_security_group],
                platform_version=ecs.FargatePlatformVersion.VERSION1_4,
            )

            encryption_key.grant_decrypt(bastion_service_fg.task_definition.obtain_execution_role()) # Grant decrypt to task definition
            pubkey.grant_read(bastion_service_fg.task_definition.obtain_execution_role())
        
            bastion_service_fg.node.add_dependency(bastion_container_fg)

            bastion_service_fg.node.add_dependency(bastion_fg_security_group)

            file_system_bastion_fg.connections.allow_from(bastion_fg_security_group, Port.tcp(2049))

            CfnOutput(self, f'RstudioBastionFargateSEcurityGroupExport-{instance}', 
                export_name=f'Rstudio-Fargate-Bastion-Security-Group-Id-{instance}',
                value=bastion_fg_security_group.security_group_id,
            )


            
            
