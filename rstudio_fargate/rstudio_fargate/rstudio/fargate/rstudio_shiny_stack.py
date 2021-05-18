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
from aws_cdk import aws_route53 as r53
from aws_cdk.aws_route53 import RecordType,RecordTarget
from aws_cdk import aws_route53_targets as route53_targets
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_athena as athena
from aws_cdk import aws_ec2 as ec2
from aws_cdk.aws_ec2 import Port
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecs_patterns as ecs_patterns
from aws_cdk.aws_elasticloadbalancingv2 import ApplicationProtocol
from aws_cdk import aws_wafv2 as waf
from aws_cdk.aws_ecr_assets import DockerImageAsset
from aws_cdk import aws_efs as efs
from aws_cdk import aws_logs as logs
from aws_cdk import aws_secretsmanager as sm
from aws_cdk.aws_ecr import Repository
import aws_cdk.aws_kms as kms
import aws_cdk.aws_iam as iam
from aws_cdk.aws_ecr import Repository

class RstudioShinyStack(cdk.Stack):
        def __init__(
            self, 
            scope: cdk.Construct, 
            id: str, 
            shared_vpc: ec2.Vpc,
            file_system_rstudio_fg_instant_file_system_id: str,
            file_system_rstudio_fg_instant_security_group_id: str,
            access_point_id_rstudio_fg_instant: str,
            instance: str,
            rstudio_pipeline_account_id: str,
            cont_mem: int,
            **kwargs) -> None:
            super().__init__(scope, id, **kwargs)

           
            shiny_image_repo_name = self.node.try_get_context("shiny_image_repo_name")

            if shiny_image_repo_name is None:
                raise ValueError("Please provide shiny docker image ecr repository name")
            
            number_of_shiny_containers = self.node.try_get_context("number_of_shiny_containers")

            if number_of_shiny_containers is None:
                raise ValueError("Please provide number of shiny containers to deploy")

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

            if (cont_mem < 1):
                cont_cpu = 256
            elif (1 <= cont_mem <= 2):
                cont_cpu = 512
            elif (2 < cont_mem <= 8):
                cont_cpu = 1024
            elif (8 < cont_mem <= 16):
                cont_cpu = 2048
            elif (16 < cont_mem <= 32):
                cont_cpu=4096

            cont_mem = cont_mem * 1024
            
            
            shiny_asset = DockerImageAsset(
                self, 
                'Shiny-image-' + instance,
                directory="./docimage-shiny",
                file='Dockerfile', 
                build_args={
                    'AWS_ACCOUNT': rstudio_pipeline_account_id,
                    'AWS_REGION': self.region,
                    'IMAGE_REPO': shiny_image_repo_name
                    }
                )
            
            """
            shiny_repository_arn=f'arn:aws:ecr:{self.region}:{rstudio_pipeline_account_id}:repository/{shiny_image_repo_name}'
            
            shiny_image_repo = Repository.from_repository_arn(self, 
                                id=f'Shiny-Docker-Image-Repo-{instance}',
                                repository_arn=shiny_repository_arn
            )
            """

            ecs_cluster_name = Fn.import_value(f'Rstudio-Cluster-Export-{instance}')
            bastion_security_group_id = Fn.import_value(f'Rstudio-Fargate-Bastion-Security-Group-Id-{instance}')

            bastion_fg_security_group = ec2.SecurityGroup.from_security_group_id(
                self, 
                f'Rstudiuo-FG-Bastion-Security-Group-{instance}',
                bastion_security_group_id,
                ) 

            envvars_shiny_cont = {
                'AWS_ACCOUNT': self.account,
                'AWS_REGION': self.region,
                'PUID' : '1000',
                'SUDO_ACCESS': 'true',
                'PASSWORD_ACCESS': 'false',
                'USER_NAME': 'ec2-user'
            } 

            secret_vars={
                'PUBLIC_KEY': ecs.Secret.from_secrets_manager(pubkey) 
            }
            
            cluster_fg = ecs.Cluster.from_cluster_attributes(
                self, 
                f'Rstudio-fg-ecs-cluster-{instance}',
                cluster_name=ecs_cluster_name,
                vpc=shared_vpc,
                security_groups=[],
                )

            efs_security_group_small = ec2.SecurityGroup.from_security_group_id(
                self, 
                "Efs-SG-small", 
                Fn.import_value(f'Rstudio-Shiny-Fargate-EFS-Small-Security-Group-Id-{instance}'),
                mutable=True,
                )

            file_system_shiny_fg_small=efs.FileSystem.from_file_system_attributes(
                self, 
                f'Shiny-Fargate-EFS-File-System-Small-{instance}',
                file_system_id=Fn.import_value(f'Rstudio-Shiny-Fargate-EFS-File-System-Small-Id-{instance}'),
                security_group=efs_security_group_small,
                )

            access_point_shiny_fg_small = efs.AccessPoint.from_access_point_attributes(
                self, 
                id="access_point_shiny_fg_small", 
                access_point_id=Fn.import_value(f'Rstudio-Shiny-Fargate-EFS-Small-AccessPoint-Id-{instance}'),
                file_system=file_system_shiny_fg_small,
                )
     
            volume_config_shiny_fg_small= ecs.Volume(
                name=f'efs-volume-rstudio-fg-small-{instance}',
                efs_volume_configuration=ecs.EfsVolumeConfiguration(
                    file_system_id=file_system_shiny_fg_small.file_system_id,
                    transit_encryption='ENABLED',
                    authorization_config=ecs.AuthorizationConfig(
                         access_point_id=access_point_shiny_fg_small.access_point_id,                 
                         )
                    )
                )

            # Mount the Shiny/Rstudio shared file system
            efs_security_group_share = ec2.SecurityGroup.from_security_group_id(
                self, 
                "Efs-SG-share", 
                Fn.import_value(f'Rstudio-Shiny-Fargate-EFS-Share-Security-Group-Id-{instance}'),
                mutable=True,
                )

            file_system_shiny_fg_share=efs.FileSystem.from_file_system_attributes(
                self, 
                f'Shiny-Fargate-EFS-File-System-Share-{instance}',
                file_system_id=Fn.import_value(f'Rstudio-Shiny-Fargate-EFS-File-System-Share-Id-{instance}'),
                security_group=efs_security_group_share,
                )

            access_point_shiny_fg_share = efs.AccessPoint.from_access_point_attributes(
                self, 
                id="access_point_shiny_fg_share", 
                access_point_id=Fn.import_value(f'Rstudio-Shiny-Fargate-EFS-Share-AccessPoint-Id-{instance}'),
                file_system=file_system_shiny_fg_share,
                )
     
            volume_config_shiny_fg_share= ecs.Volume(
                name=f'efs-volume-rstudio-shiny-fg-share-{instance}',
                efs_volume_configuration=ecs.EfsVolumeConfiguration(
                    file_system_id=file_system_shiny_fg_share.file_system_id,
                    transit_encryption='ENABLED',
                    authorization_config=ecs.AuthorizationConfig(
                         access_point_id=access_point_shiny_fg_share.access_point_id,                 
                         )
                    )
                )
                
            # Mount the large file system
            efs_security_group_large = ec2.SecurityGroup.from_security_group_id(
                self, 
                "Efs-SG-large", 
                Fn.import_value(f'Rstudio-Fargate-EFS-Large-Security-Group-Id-{instance}'),
                mutable=True,
                )

            file_system_shiny_fg_large=efs.FileSystem.from_file_system_attributes(
                self, 
                f'Shiny-Fargate-EFS-File-System-Large-{instance}',
                file_system_id=Fn.import_value(f'Rstudio-Fargate-EFS-File-System-Large-Id-{instance}'),
                security_group=efs_security_group_large,
                )

            access_point_shiny_fg_large = efs.AccessPoint.from_access_point_attributes(
                self, 
                id="access_point_shiny_fg_large", 
                access_point_id=Fn.import_value(f'Rstudio-Fargate-EFS-Large-AccessPoint-Id-{instance}'),
                file_system=file_system_shiny_fg_large,
                )
     
            volume_config_shiny_fg_large= ecs.Volume(
                name=f'efs-volume-shiny-fg-large-{instance}',
                efs_volume_configuration=ecs.EfsVolumeConfiguration(
                    file_system_id=file_system_shiny_fg_large.file_system_id,
                    transit_encryption='ENABLED',
                    authorization_config=ecs.AuthorizationConfig(
                         access_point_id=access_point_shiny_fg_large.access_point_id,                 
                         )
                    )
                )

            efs_security_group_instant = ec2.SecurityGroup.from_security_group_id(
                self, 
                "Efs-SG-instant", 
                file_system_rstudio_fg_instant_security_group_id,
                mutable=True,
                )

            file_system_shiny_fg_instant=efs.FileSystem.from_file_system_attributes(
                self, 
                f'Shiny-Fargate-EFS-File-System-Instant-{instance}',
                file_system_id=file_system_rstudio_fg_instant_file_system_id,
                security_group=efs_security_group_instant,
                )

            access_point_shiny_fg_instant = efs.AccessPoint.from_access_point_attributes(self, 
                id="access_point_rstudio_fg_instant", 
                access_point_id=access_point_id_rstudio_fg_instant,
                file_system=file_system_shiny_fg_instant,
                )
     
            volume_config_shiny_fg_instant= ecs.Volume(
                name=f'efs-volume-shiny-fg-instant-{instance}',
                efs_volume_configuration=ecs.EfsVolumeConfiguration(
                    file_system_id=file_system_shiny_fg_instant.file_system_id,
                    transit_encryption='ENABLED',
                    authorization_config=ecs.AuthorizationConfig(
                         access_point_id=access_point_shiny_fg_instant.access_point_id,                 
                         )
                    )
                )

            shiny_cloudwatch_log_kms_key_alias = kms.Alias.from_alias_name(
                self,
                'Rstudio-Cw-' + instance,   
                alias_name= f'alias/cwlogs-rstudio-{instance}',
            )
           
            shiny_logs_container = logs.LogGroup(
                self,
                f'shiny-cw-logs-container-{instance}',
                log_group_name=f'Shiny-cont-fg-{instance}/{id}',
                removal_policy=RemovalPolicy.DESTROY,
                retention=logs.RetentionDays.ONE_WEEK,
                encryption_key=shiny_cloudwatch_log_kms_key_alias,
            )

            shiny_logs_container.node.add_dependency(shiny_cloudwatch_log_kms_key_alias)
            
            shiny_task_fg = ecs.FargateTaskDefinition(
                self, 
                f'Shiny-fg-task-{instance}',
                memory_limit_mib=cont_mem,
                cpu=cont_cpu,
                volumes=[volume_config_shiny_fg_small, volume_config_shiny_fg_share, volume_config_shiny_fg_large, volume_config_shiny_fg_instant],
            )

            shiny_container_fg = shiny_task_fg.add_container(
                f'Shiny-fg-{instance}', 
                #image=ecs.ContainerImage.from_ecr_repository(shiny_image_repo), 
                image=ecs.ContainerImage.from_docker_image_asset(shiny_asset),
                environment= envvars_shiny_cont,
                secrets=secret_vars,
                memory_limit_mib=cont_mem,
                logging=ecs.LogDrivers.aws_logs(
                    stream_prefix=f'Shiny-fg-{instance}', 
                    log_group=shiny_logs_container,
                ),
            )

            shiny_container_fg.node.add_dependency(shiny_logs_container)

            shiny_container_fg.node.add_dependency(shiny_task_fg)

            shiny_container_fg.add_port_mappings(
                ecs.PortMapping(
                    container_port=3838),
                ecs.PortMapping(
                    container_port=22),
                )  

            shiny_container_fg.add_mount_points(
                ecs.MountPoint(
                    container_path='/home',
                    source_volume=volume_config_shiny_fg_small.name,
                    read_only=False,
                 ),
                ecs.MountPoint(
                    container_path='/rstudio_shiny_share',
                    source_volume=volume_config_shiny_fg_share.name,
                    read_only=False,
                 ),
                ecs.MountPoint(
                    container_path='/s3_data_sync/hourly_sync',
                    source_volume=volume_config_shiny_fg_large.name,
                    read_only=False,
                 ),
                ecs.MountPoint(
                    container_path='/s3_data_sync/instant_upload',
                    source_volume=volume_config_shiny_fg_instant.name,
                    read_only=False,
                 )    
            )

            shiny_zone_fg = r53.PublicHostedZone.from_hosted_zone_attributes(
                self, 
                'Shiny-zone-' + instance, 
                hosted_zone_id=Fn.import_value('Shiny-hosted-zone-id-' + instance),
                zone_name=Fn.import_value('Shiny-hosted-zone-name-' + instance),
                )

            CfnOutput(
                self, 
                "ShinyInstanceHostedZoneId-" + instance, 
                export_name="Shiny-fg-instance-hosted-zone-id-" + instance,
                value=shiny_zone_fg.hosted_zone_id,
                )

            CfnOutput(
                self, 
                "ShinyInstanceHostedZoneName-" + instance, 
                export_name='Shiny-fg-instance-hosted-zone-name-' + instance,
                value=shiny_zone_fg.zone_name,
                )

            cert = acm.Certificate.from_certificate_arn(
                self, 
                'Shiny-instance-cert-' + instance, 
                Fn.import_value('Rstudio-cert-arn-' + instance),
                ) 
   
            shiny_service_fg = ecs_patterns.ApplicationLoadBalancedFargateService(
                self, 
                f'Shiny-fg-service-{instance}',
                cluster=cluster_fg,
                memory_limit_mib=cont_mem,
                cpu=cont_cpu,
                task_definition=shiny_task_fg,
                desired_count=number_of_shiny_containers,
                certificate=cert,
                domain_name=shiny_zone_fg.zone_name,
                domain_zone= shiny_zone_fg,
                protocol=ApplicationProtocol.HTTPS,
                platform_version=ecs.FargatePlatformVersion.VERSION1_4,
                health_check_grace_period=cdk.Duration.seconds(900),
            )

            shiny_service_fg.node.add_dependency(shiny_container_fg)

            shiny_service_fg.target_group.configure_health_check(
                healthy_http_codes= '200,301,302'          
            )

            encryption_key.grant_decrypt(shiny_service_fg.task_definition.obtain_execution_role()) # Grant decrypt to task definition
            pubkey.grant_read(shiny_service_fg.task_definition.obtain_execution_role())

            file_system_shiny_fg_large.connections.allow_from(shiny_service_fg.service, Port.tcp(2049));    
            file_system_shiny_fg_small.connections.allow_from(shiny_service_fg.service, Port.tcp(2049));  
            file_system_shiny_fg_instant.connections.allow_from(shiny_service_fg.service, Port.tcp(2049));    
            file_system_shiny_fg_share.connections.allow_from(shiny_service_fg.service, Port.tcp(2049));
            
            shiny_service_fg.service.connections.allow_from(bastion_fg_security_group,Port.tcp(22)); 

            CfnOutput(self, f'ShinyFargateALB-{instance}', 
                export_name=f'Shiny-Fargate-Application-Load-Balancer-Arn-{instance}',
                value=shiny_service_fg.load_balancer.load_balancer_arn,
            )

            

            
