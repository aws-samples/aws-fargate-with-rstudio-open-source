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
from aws_cdk.aws_ecr_assets import DockerImageAsset

class RstudioEC2Stack(cdk.Stack):
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

            rstudio_image_repo_name = self.node.try_get_context("rstudio_image_repo_name")

            if rstudio_image_repo_name is None:
                raise ValueError("Please provide rstudio docker image ecr repository name")

            rstudio_pipeline_account_id = self.node.try_get_context("rstudio_pipeline_account_id")

            if rstudio_pipeline_account_id is None:
                raise ValueError("Please provide central development account id")
            
            rstudio_athena_bucket_name=self.node.try_get_context("rstudio_athena_bucket_name")
            
            if rstudio_athena_bucket_name is None:
                raise ValueError("Please provide name for rstudio Athena bucket")
            
            rstudio_athena_wg_name=self.node.try_get_context("rstudio_athena_wg_name")
            
            if rstudio_athena_wg_name is None:
                raise ValueError("Please provide name for rstudio Athena workgroup")
                
            rstudio_asset = DockerImageAsset(
                self, 
                'Rstudio-image',
                directory="./docimage-rstudio",
                file='Dockerfile', 
                build_args={
                    'RSTUDIO_VERSION': '1.4.1103', 
                    'AWS_ACCOUNT': rstudio_pipeline_account_id,
                    'AWS_REGION': self.region,
                    'IMAGE_REPO': rstudio_image_repo_name
                    }
                )

            cont_mem = cont_mem * 1024

            encryption_key_arn = self.node.try_get_context("encryption_key_arn")

            if encryption_key_arn is None:
                raise ValueError("Please provide encryption key arn")
                
            encryption_key=kms.Key.from_key_arn(self, 'Encryption-Key', key_arn=encryption_key_arn)

            access_key_id_arn = self.node.try_get_context(f"access_key_id_arn")

            if access_key_id_arn is None:
                raise ValueError("Please provide aws account access key id secret manager ARN")
            
            access_key_arn = self.node.try_get_context("access_key_arn")

            if access_key_arn is None:
                raise ValueError("Please provide aws account access key secret manager ARN")  

            rstudio_users = self.node.try_get_context("rstudio_users")

            if rstudio_users is None:
                raise ValueError("Please provide comma-separated list of rstudio frontend users")    
          
            accesskey = sm.Secret.from_secret_attributes(
                self, 
                "ImportedRstudioAccessKey-" + instance, 
                secret_arn=access_key_arn,
                encryption_key=encryption_key
                )
            
            accesskeyid = sm.Secret.from_secret_attributes(
                self, 
                "ImportedRstudioAccessKeyId-" + instance,
                secret_arn=access_key_id_arn,
                encryption_key=encryption_key
                ) 

            secret_vars={
                'AWS_ACCESS_KEY_ID': ecs.Secret.from_secrets_manager(accesskeyid),
                'AWS_ACCESS_KEY': ecs.Secret.from_secrets_manager(accesskey)
                }

            context_string=f"rstudio_{instance}_pass_arn"
            arn_file = open("rstudio_arn.txt", "r")
            readarn = arn_file.readlines()
            for line in readarn:
                arn_data = line.rstrip("\n").split(": ")
                if arn_data[0] == context_string:
                    rstudio_instance_pass_arn = arn_data[1]
                    rstudiopass = sm.Secret.from_secret_attributes(
                        self, 
                        "ImportedRstudioPass-" + instance,
                        secret_arn=rstudio_instance_pass_arn,
                        encryption_key=encryption_key
                        )
                    secret_vars['RSTUDIO_PASS'] = ecs.Secret.from_secrets_manager(rstudiopass)
                    arn_file.close()
                    break

            envvars_cont = {
                'AWS_ACCOUNT': self.account,
                'AWS_REGION': self.region,                
                'AWS_S3_BUCKET': f's3://{rstudio_athena_bucket_name}/Athena-Query',
                'AWS_ATHENA_WG': rstudio_athena_wg_name,
                'RSTUDIO_USERS': rstudio_users,
                'INSTANCE_NAME': instance,
                'INDIVIDUAL_CONT': 'NO'
                } 

            
            secretpass_list = []
            number_of_users = len(rstudio_users.split(','))
            users=rstudio_users.split(",")

            for i in range(number_of_users):
                secretpass_arn=""
                username=users[i]
                username_prefix = username.split('@')
                user_name=username.replace('@','_').replace('.','_')
                context_string=f"{user_name}_pass_arn_{instance}"
                user_exists = False
                arn_file = open("rstudio_arn.txt", "r")
                readarn = arn_file.readlines()
                for line in readarn:
                    arn_data = line.rstrip("\n").split(": ")
                    if arn_data[0] == context_string:
                        secretpass_arn = arn_data[1]
                
                        secretpass_val = sm.Secret.from_secret_attributes(
                            self, 
                            "ImportedSecretRstudioUserPass-" + username_prefix[0].replace('.','-') + "-" + instance,  
                            secret_arn=secretpass_arn,
                            encryption_key=encryption_key
                        ) 

                        secretpass = ecs.Secret.from_secrets_manager(secretpass_val)
                        secretpass_list.append(secretpass)                      
                        secret_vars[arn_data[0]] = secretpass
                        print(secret_vars)

                        arn_file.close()
                        user_exists = True 
                        break 
                if not user_exists:
                    print (f"{username} not found in rstudio_arn.txt")
            """  
            rstudio_repository_arn=f'arn:aws:ecr:{self.region}:{rstudio_pipeline_account_id}:repository/{rstudio_image_repo_name}'
            
            rstudio_image_repo = Repository.from_repository_arn(self, 
                                id=f'Rstudio-Docker-Image-Repo-{instance}',
                                repository_arn=rstudio_repository_arn
            )
            """
            
            ecs_cluster_name = Fn.import_value(f'Rstudio-Cluster-Export-{instance}')
            bastion_security_group_id = Fn.import_value(f'Rstudio-Fargate-Bastion-Security-Group-Id-{instance}')

            bastion_fg_security_group = ec2.SecurityGroup.from_security_group_id(
                self, 
                f'Rstudiuo-FG-Bastion-Security-Group-{instance}',
                bastion_security_group_id,
                ) 

            asg_security_group_id = Fn.import_value(f'Rstudio-EC2-ASG-Security-Group-Id-{instance}')
            asg_security_group = ec2.SecurityGroup.from_security_group_id(self, f'Rstudiuo-EC2-ASG-Security-Group-{instance}',
                asg_security_group_id)

            cluster_ec2 = ecs.Cluster.from_cluster_attributes(
                self, 
                f'Rstudio-ec2-ecs-cluster-{instance}',
                cluster_name=ecs_cluster_name,
                vpc=shared_vpc,
                security_groups=[asg_security_group],
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

            file_system_rstudio_fg_large=efs.FileSystem.from_file_system_attributes(
                self, 
                f'Rstudio-Fargate-EFS-File-System-Large-{instance}',
                file_system_id=Fn.import_value(f'Rstudio-Fargate-EFS-File-System-Large-Id-{instance}'),
                security_group=efs_security_group_large,
                )

            access_point_rstudio_fg_large = efs.AccessPoint.from_access_point_attributes(
                self, 
                id="access_point_rstudio_fg_large", 
                access_point_id=Fn.import_value(f'Rstudio-Fargate-EFS-Large-AccessPoint-Id-{instance}'),
                file_system=file_system_rstudio_fg_large,
                )
     
            volume_config_rstudio_fg_large= ecs.Volume(
                name=f'efs-volume-rstudio-fg-large-{instance}',
                efs_volume_configuration=ecs.EfsVolumeConfiguration(
                    file_system_id=file_system_rstudio_fg_large.file_system_id,
                    transit_encryption='ENABLED',
                    authorization_config=ecs.AuthorizationConfig(
                         access_point_id=access_point_rstudio_fg_large.access_point_id,                 
                         )
                    )
                )
            
            efs_security_group_instant = ec2.SecurityGroup.from_security_group_id(
                self, 
                "Efs-SG-instant", 
                file_system_rstudio_fg_instant_security_group_id,
                mutable=True,
                )

            file_system_rstudio_fg_instant=efs.FileSystem.from_file_system_attributes(
                self, 
                f'Rstudio-Fargate-EFS-File-System-Instant-{instance}',                                                                            
                file_system_id=file_system_rstudio_fg_instant_file_system_id,
                security_group=efs_security_group_instant,
                )

            access_point_rstudio_fg_instant = efs.AccessPoint.from_access_point_attributes(
                self, 
                id="access_point_rstudio_fg_instant", 
                access_point_id=access_point_id_rstudio_fg_instant,
                file_system=file_system_rstudio_fg_instant,
                )
     
            volume_config_rstudio_fg_instant= ecs.Volume(
                name=f'efs-volume-rstudio-fg-instant-{instance}',
                efs_volume_configuration=ecs.EfsVolumeConfiguration(
                    file_system_id=file_system_rstudio_fg_instant.file_system_id,
                    transit_encryption='ENABLED',
                    authorization_config=ecs.AuthorizationConfig(
                         access_point_id=access_point_rstudio_fg_instant.access_point_id,                 
                         )
                    )
                )

            rstudio_cloudwatch_log_kms_key_alias = kms.Alias.from_alias_name(
                self,
                'Rstudio-Cw-' + instance,   
                alias_name= f'alias/cwlogs-rstudio-{instance}',
            )
           
            rstudio_logs_container = logs.LogGroup(
                self,
                f'rstudio-cw-logs-container-{instance}',
                log_group_name=f'Rstudio-cont-ec2-{instance}/{id}',
                removal_policy=RemovalPolicy.DESTROY,
                retention=logs.RetentionDays.ONE_WEEK,
                encryption_key=rstudio_cloudwatch_log_kms_key_alias,
            )

            rstudio_logs_container.node.add_dependency(rstudio_cloudwatch_log_kms_key_alias)
            
            
            rstudio_zone_fg = r53.PublicHostedZone.from_hosted_zone_attributes(
                self, 
                'Rstudio-zone-' + instance, 
                hosted_zone_id=Fn.import_value('Rstudio-hosted-zone-id-' + instance),
                zone_name=Fn.import_value('Rstudio-hosted-zone-name-' + instance),
                )

            CfnOutput(
                self, 
                "RstudioEC2InstanceHostedZoneId-" + instance, 
                export_name="Rstudio-ec2-instance-hosted-zone-id-" + instance,
                value=rstudio_zone_fg.hosted_zone_id,
                )

            CfnOutput(
                self, 
                "RstudioEC2InstanceHostedZoneName-" + instance, 
                export_name='Rstudio-ec2-instance-hosted-zone-name-' + instance,
                value=rstudio_zone_fg.zone_name,
                )

            cert = acm.Certificate.from_certificate_arn(
                self, 
                'Rstudio-instance-cert-' + instance, 
                Fn.import_value('Rstudio-cert-arn-' + instance),
                )     
            
            efs_security_group_small = ec2.SecurityGroup.from_security_group_id(
                self, 
                "Efs-SG-small", 
                Fn.import_value(f'Rstudio-cont-EC2-File-System-Security-Group-Id-{instance}'),
                mutable=True,
                )

            file_system_rstudio_fg_small=efs.FileSystem.from_file_system_attributes(
                    self, 
                    f'Rstudio-Fargate-EFS-File-System-Small-{instance}',
                    file_system_id=Fn.import_value(f'Rstudio-cont-EC2-File-System-Id-{instance}'),
                    security_group=efs_security_group_small,
                    )
    
            access_point_rstudio_fg_small = efs.AccessPoint.from_access_point_attributes(
                    self, 
                    id="access_point_rstudio_fg_small", 
                    access_point_id=Fn.import_value(f'Rstudio-cont-EC2-File-System-AccessPoint-Id-{instance}'),
                    file_system=file_system_rstudio_fg_small,
                    )
            
            volume_config_rstudio_fg_small= ecs.Volume(
                    name=f'efs-volume-rstudio-fg-small-{instance}',
                    efs_volume_configuration=ecs.EfsVolumeConfiguration(
                        file_system_id=file_system_rstudio_fg_small.file_system_id,
                        transit_encryption='ENABLED',
                        authorization_config=ecs.AuthorizationConfig(
                             access_point_id=access_point_rstudio_fg_small.access_point_id,                 
                             )
                        )
                    )
                
            rstudio_task_ec2 = ecs.Ec2TaskDefinition(
                    self, 
                    f'Rstudio-ec2-task-{instance}',
                    volumes=[volume_config_rstudio_fg_small, volume_config_shiny_fg_share, volume_config_rstudio_fg_large, volume_config_rstudio_fg_instant],
                )
    
            rstudio_container_ec2 = rstudio_task_ec2.add_container(
                    f'Rstudio-ec2-{instance}', 
                    #image=ecs.ContainerImage.from_ecr_repository(rstudio_image_repo), 
                    image=ecs.ContainerImage.from_docker_image_asset(rstudio_asset),
                    environment= envvars_cont,
                    secrets=secret_vars,
                    memory_reservation_mib=cont_mem,
                    logging=ecs.LogDrivers.aws_logs(
                        stream_prefix=f'Rstudio-ec2-{instance}', 
                        log_group=rstudio_logs_container,
                    ),
                )
    
            rstudio_container_ec2.node.add_dependency(rstudio_logs_container)
    
            rstudio_container_ec2.node.add_dependency(rstudio_task_ec2)
    
            rstudio_container_ec2.add_port_mappings(
                    ecs.PortMapping(
                        container_port=8787),
                    ecs.PortMapping(
                        container_port=3838),
                    ecs.PortMapping(
                        container_port=22),
                    )    
            rstudio_container_ec2.add_mount_points(
                ecs.MountPoint(
                    container_path='/home',
                    source_volume=volume_config_rstudio_fg_small.name,
                    read_only=False,
                 ),
                 ecs.MountPoint(
                    container_path='/rstudio_shiny_share',
                    source_volume=volume_config_shiny_fg_share.name,
                    read_only=False,
                 ),
                 ecs.MountPoint(
                    container_path='/s3_data_sync/hourly_sync',
                    source_volume=volume_config_rstudio_fg_large.name,
                    read_only=False,
                 ),
                ecs.MountPoint(
                        container_path='/s3_data_sync/instant_upload',
                        source_volume=volume_config_rstudio_fg_instant.name,
                        read_only=False,
                     )    
                )
            rstudio_service_ec2 = ecs_patterns.ApplicationLoadBalancedEc2Service(
                    self, 
                    f'Rstudio-fg-service-{instance}',
                    cluster=cluster_ec2,
                    task_definition=rstudio_task_ec2,
                    desired_count=1,
                    certificate=cert,
                    domain_name=rstudio_zone_fg.zone_name,
                    domain_zone= rstudio_zone_fg,
                    protocol=ApplicationProtocol.HTTPS,
                    health_check_grace_period=cdk.Duration.seconds(900),
                )
    
            encryption_key.grant_decrypt(rstudio_service_ec2.task_definition.obtain_execution_role()) # Grant decrypt to task definition
            accesskey.grant_read(rstudio_service_ec2.task_definition.obtain_execution_role())
            accesskeyid.grant_read(rstudio_service_ec2.task_definition.obtain_execution_role())
            rstudiopass.grant_read(rstudio_service_ec2.task_definition.obtain_execution_role())
            
            number_of_users = len(rstudio_users.split(','))
            users=rstudio_users.split(",")

            for i in range(number_of_users):
                secretpass_list[i].grant_read(rstudio_service_ec2.task_definition.obtain_execution_role())
                
            rstudio_service_ec2.node.add_dependency(rstudio_container_ec2)
    
            rstudio_service_ec2.target_group.configure_health_check(
                    healthy_http_codes= '200,301,302'          
                )
    
            file_system_rstudio_fg_large.connections.allow_from(rstudio_service_ec2.service, Port.tcp(2049));    
            file_system_rstudio_fg_small.connections.allow_from(rstudio_service_ec2.service, Port.tcp(2049));  
            file_system_rstudio_fg_instant.connections.allow_from(rstudio_service_ec2.service, Port.tcp(2049));    
            file_system_shiny_fg_share.connections.allow_from(rstudio_service_ec2.service, Port.tcp(2049))
                
            rstudio_service_ec2.service.connections.allow_from(bastion_fg_security_group,Port.tcp(22)); 

            CfnOutput(self, f'RstudioFargateALB-{instance}', 
                    export_name=f'Rstudio-Fargate-Application-Load-Balancer-Arn-{instance}',
                    value=rstudio_service_ec2.load_balancer.load_balancer_arn,
                )

            

            