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
from aws_cdk.core import Fn, CfnOutput,RemovalPolicy,CfnOutput
from aws_cdk.aws_ec2 import Port
from aws_cdk import aws_efs as efs
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_kms as kms

class RstudioEfsStack(cdk.Stack):
        def __init__(self, scope: cdk.Construct, id: str, shared_vpc: ec2.Vpc, instance: str,
                    rstudio_individual_containers: bool,
                    rstudio_install_type: str, 
                    **kwargs) -> None:
            super().__init__(scope, id, **kwargs)

            
            rstudio_users = self.node.try_get_context("rstudio_users")

            if rstudio_users is None:
                raise ValueError("Please provide comma-separated list of rstudio frontend users")
                
            rstudio_efs_kms_key_alias = kms.Alias.from_alias_name(
                self,
                'Rstudio-Efs-' + instance,   
                alias_name= f'alias/efs-rstudio-{instance}',
            )
            
            # Define EFS filesystem for rstudio bastion instance
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
            
            # Shiny home file system
            file_system_rstudio_shiny_fg_small = efs.FileSystem(
                self, 
                f'Rstudio-shiny-cont-fg-user-data-small-{instance}',
                file_system_name=f'Rstudio-shiny-cont-fg-fs-small-{instance}',
                vpc=shared_vpc,
                encrypted=True,
                kms_key=rstudio_efs_kms_key_alias,
                performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
                throughput_mode=efs.ThroughputMode.BURSTING,
                enable_automatic_backups=True,
                removal_policy=RemovalPolicy.DESTROY,
            )
    
            access_point_rstudio_shiny_fg_small = efs.AccessPoint(
                self, 
                f'Rstudio-shiny-fg-access-point-small-{instance}',
                file_system=file_system_rstudio_shiny_fg_small,
                path='/rstudio-shiny-path-fg-small',
                create_acl= efs.Acl(owner_uid= '1000', owner_gid= '1000', permissions= '755'),      
                )
                        
            # File system for sharing data between Shiny and RStudio instances
            file_system_rstudio_shiny_share_fg = efs.FileSystem(
                self, 
                f'Rstudio-shiny-fg-user-data-share-{instance}',
                file_system_name=f'Rstudio-shiny-share-cont-fg-fs-{instance}',
                vpc=shared_vpc,
                encrypted=True,
                kms_key=rstudio_efs_kms_key_alias,
                performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
                throughput_mode=efs.ThroughputMode.BURSTING,
                enable_automatic_backups=True,
                removal_policy=RemovalPolicy.DESTROY,
                )

            access_point_rstudio_shiny_share_fg = efs.AccessPoint(
                self, 
                f'Rstudio-shiny-share-fg-access-point-{instance}',
                file_system=file_system_rstudio_shiny_share_fg,
                path='/rstudio-shiny-share-path-fg',
                create_acl= efs.Acl(owner_uid= '1000', owner_gid= '1000', permissions= '755'),      
                )
                
            # Small files filesystem
            if rstudio_install_type == "ec2":
                file_system_rstudio_fg_small = efs.FileSystem(
                    self, 
                    f'Rstudio-cont-EC2-File-System-{instance}',
                    file_system_name=f'Rstudio-cont-EC2-File-System-{instance}',
                    vpc=shared_vpc,
                    encrypted=True,
                    kms_key=rstudio_efs_kms_key_alias,
                    performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
                    throughput_mode=efs.ThroughputMode.BURSTING,
                    enable_automatic_backups=True,
                    removal_policy=RemovalPolicy.DESTROY,
                    )
    
                access_point_rstudio_fg_small = efs.AccessPoint(
                    self, 
                    f'Rstudio-fg-access-point-small-{instance}',
                    file_system=file_system_rstudio_fg_small,
                    path='/rstudio-path-fg-small',
                    create_acl= efs.Acl(owner_uid= '1000', owner_gid= '1000', permissions= '755'),      
                    )
                    
                CfnOutput(self, f'Rstudio-cont-EC2-File-System-Id-{instance}', 
                    export_name=f'Rstudio-cont-EC2-File-System-Id-{instance}',
                    value=file_system_rstudio_fg_small.file_system_id,
                )
    
                CfnOutput(self, f'Rstudio-cont-EC2-File-System-Security-Group-Id-{instance}', 
                    export_name=f'Rstudio-cont-EC2-File-System-Security-Group-Id-{instance}',
                    value=file_system_rstudio_fg_small.connections.security_groups[0].security_group_id,
                )
    
                CfnOutput(self, f'Rstudio-cont-EC2-File-System-AccessPoint-Id-{instance}', 
                    export_name=f'Rstudio-cont-EC2-File-System-AccessPoint-Id-{instance}',
                    value=access_point_rstudio_fg_small.access_point_id,
                )
            else:
                if rstudio_individual_containers:
                    number_of_users = len(rstudio_users.split(','))
                    users=rstudio_users.split(",")
                    
                    for i in range(number_of_users):
                        username_prefix = users[i].split('@')
                        #username=users[i].replace('@','').replace('.','-')                                                                 
                        file_system_rstudio_fg_small_user = efs.FileSystem(
                            self, 
                            f'Rstudio-cont-fg-user-data-small-{instance}' + '-' + username_prefix[0].replace('.','-'),
                            file_system_name=f'Rstudio-cont-fg-fs-small-{instance}' + '-' + username_prefix[0].replace('.','-'),
                            vpc=shared_vpc,
                            encrypted=True,
                            kms_key=rstudio_efs_kms_key_alias,
                            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
                            throughput_mode=efs.ThroughputMode.BURSTING,
                            enable_automatic_backups=True,
                            removal_policy=RemovalPolicy.DESTROY,
                        )
        
                        access_point_rstudio_fg_small_user = efs.AccessPoint(
                            self, 
                            f'Rstudio-fg-access-point-small-{instance}' + '-' + username_prefix[0].replace('.','-'),
                            file_system=file_system_rstudio_fg_small_user,
                            path='/rstudio-path-fg-small',
                            create_acl= efs.Acl(owner_uid= '1000', owner_gid= '1000', permissions= '755'),      
                            )
                            
                        CfnOutput(self, f'Rstudio-Fargate-EFS-File-System-Small-Id-{instance}-' + username_prefix[0].replace('.','-'), 
                            export_name=f'Rstudio-Fargate-EFS-File-System-Small-Id-{instance}-' + username_prefix[0].replace('.','-'),
                            value=file_system_rstudio_fg_small_user.file_system_id,
                        )
            
                        CfnOutput(self, f'Rstudio-Fargate-EFS-Small-Security-Group-Id-{instance}-' + username_prefix[0].replace('.','-'), 
                            export_name=f'Rstudio-Fargate-EFS-Small-Security-Group-Id-{instance}-' + username_prefix[0].replace('.','-'),
                            value=file_system_rstudio_fg_small_user.connections.security_groups[0].security_group_id,
                        )
            
                        CfnOutput(self, f'Rstudio-Fargate-EFS-Small-AccessPoint-Id-{instance}-' + username_prefix[0].replace('.','-'), 
                            export_name=f'Rstudio-Fargate-EFS-Small-AccessPoint-Id-{instance}-' + username_prefix[0].replace('.','-'),
                            value=access_point_rstudio_fg_small_user.access_point_id,
                        )
                else:
                    file_system_rstudio_fg_small = efs.FileSystem(
                        self, 
                        f'Rstudio-cont-fg-user-data-small-{instance}',
                        file_system_name=f'Rstudio-cont-fg-fs-small-{instance}',
                        vpc=shared_vpc,
                        encrypted=True,
                        kms_key=rstudio_efs_kms_key_alias,
                        performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
                        throughput_mode=efs.ThroughputMode.BURSTING,
                        enable_automatic_backups=True,
                        removal_policy=RemovalPolicy.DESTROY,
                        )
        
                    access_point_rstudio_fg_small = efs.AccessPoint(
                        self, 
                        f'Rstudio-fg-access-point-small-{instance}',
                        file_system=file_system_rstudio_fg_small,
                        path='/rstudio-path-fg-small',
                        create_acl= efs.Acl(owner_uid= '1000', owner_gid= '1000', permissions= '755'),      
                        )
                        
                    CfnOutput(self, f'Rstudio-Fargate-EFS-File-System-Small-Id-{instance}', 
                        export_name=f'Rstudio-Fargate-EFS-File-System-Small-Id-{instance}',
                        value=file_system_rstudio_fg_small.file_system_id,
                    )
        
                    CfnOutput(self, f'Rstudio-Fargate-EFS-Small-Security-Group-Id-{instance}', 
                        export_name=f'Rstudio-Fargate-EFS-Small-Security-Group-Id-{instance}',
                        value=file_system_rstudio_fg_small.connections.security_groups[0].security_group_id,
                    )
        
                    CfnOutput(self, f'Rstudio-Fargate-EFS-Small-AccessPoint-Id-{instance}', 
                        export_name=f'Rstudio-Fargate-EFS-Small-AccessPoint-Id-{instance}',
                        value=access_point_rstudio_fg_small.access_point_id,
                    )
        
            
            
            # Large file filesystem
            file_system_rstudio_fg_large = efs.FileSystem(
                self, 
                f'Rstudio-cont-fg-user-data-large-{instance}',
                file_system_name=f'Rstudio-cont-fg-fs-large-{instance}',
                vpc=shared_vpc,
                encrypted=True,
                kms_key=rstudio_efs_kms_key_alias,
                performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
                throughput_mode=efs.ThroughputMode.BURSTING,
                enable_automatic_backups=True,
                removal_policy=RemovalPolicy.DESTROY,
                )

            access_point_rstudio_fg_large = efs.AccessPoint(
                self, 
                f'Rstudio-fg-access-point-large-{instance}',
                file_system=file_system_rstudio_fg_large,
                path='/rstudio-path-fg-large',
                create_acl= efs.Acl(owner_uid= '1000', owner_gid= '1000', permissions= '755'),      
                )
            
            file_system_rstudio_fg_instant = efs.FileSystem(
                self, 
                f'Rstudio-cont-fg-user-data-instant-{instance}',
                file_system_name=f'Rstudio-cont-fg-fs-instant-{instance}',
                vpc=shared_vpc,
                encrypted=True,
                kms_key=rstudio_efs_kms_key_alias,
                performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
                throughput_mode=efs.ThroughputMode.BURSTING,
                enable_automatic_backups=True,
                removal_policy=RemovalPolicy.DESTROY,
                )

            access_point_rstudio_fg_instant = efs.AccessPoint(
                self, 
                f'Rstudio-fg-access-point-instant-{instance}',
                file_system=file_system_rstudio_fg_instant,
                path='/rstudio-path-fg-instant',
                create_acl= efs.Acl(owner_uid= '1000', owner_gid= '1000', permissions= '755'),      
                )

            # Shiny /home filesystem
            CfnOutput(self, f'Rstudio-Shiny-Fargate-EFS-File-System-Small-Id-{instance}', 
                export_name=f'Rstudio-Shiny-Fargate-EFS-File-System-Small-Id-{instance}',
                value=file_system_rstudio_shiny_fg_small.file_system_id,
            )

            CfnOutput(self, f'Rstudio-Shiny-Fargate-EFS-Small-Security-Group-Id-{instance}', 
                export_name=f'Rstudio-Shiny-Fargate-EFS-Small-Security-Group-Id-{instance}',
                value=file_system_rstudio_shiny_fg_small.connections.security_groups[0].security_group_id,
            )

            CfnOutput(self, f'Rstudio-Shiny-Fargate-EFS-Small-AccessPoint-Id-{instance}', 
                export_name=f'Rstudio-Shiny-Fargate-EFS-Small-AccessPoint-Id-{instance}',
                value=access_point_rstudio_shiny_fg_small.access_point_id,
            )
            
            # Shiny Rstudio share 
            CfnOutput(self, f'Rstudio-Shiny-Fargate-EFS-File-System-Share-Id-{instance}', 
                export_name=f'Rstudio-Shiny-Fargate-EFS-File-System-Share-Id-{instance}',
                value=file_system_rstudio_shiny_share_fg.file_system_id,
            )

            CfnOutput(self, f'Rstudio-Shiny-Fargate-EFS-Share-Security-Group-Id-{instance}', 
                export_name=f'Rstudio-Shiny-Fargate-EFS-Share-Security-Group-Id-{instance}',
                value=file_system_rstudio_shiny_share_fg.connections.security_groups[0].security_group_id,
            )

            CfnOutput(self, f'Rstudio-Shiny-Fargate-EFS-Share-AccessPoint-Id-{instance}', 
                export_name=f'Rstudio-Shiny-Fargate-EFS-Share-AccessPoint-Id-{instance}',
                value=access_point_rstudio_shiny_share_fg.access_point_id,
            )
            
            CfnOutput(self, f'Rstudio-Bastion-Fargate-EFS-File-System-Id-{instance}', 
                export_name=f'Rstudio-Bastion-Fargate-EFS-File-System-Id-{instance}',
                value=file_system_bastion_fg.file_system_id,
            )

            CfnOutput(self, f'Rstudio-Bastion-Fargate-EFS-Security-Group-Id-{instance}', 
                export_name=f'Rstudio-Bastion-Fargate-EFS-Security-Group-Id-{instance}',
                value=file_system_bastion_fg.connections.security_groups[0].security_group_id,
            ) 

            CfnOutput(self, f'Rstudio-Bastion-Fargate-EFS-AccessPoint-Id-{instance}', 
                export_name=f'Rstudio-Bastion-Fargate-EFS-AccessPoint-Id-{instance}',
                value=access_point_bastion_fg.access_point_id,
            )   

            CfnOutput(self, f'Rstudio-Fargate-EFS-File-System-Large-Id-{instance}', 
                export_name=f'Rstudio-Fargate-EFS-File-System-Large-Id-{instance}',
                value=file_system_rstudio_fg_large.file_system_id,
            )

            CfnOutput(self, f'Rstudio-Fargate-EFS-Large-Security-Group-Id-{instance}', 
                export_name=f'Rstudio-Fargate-EFS-Large-Security-Group-Id-{instance}',
                value=file_system_rstudio_fg_large.connections.security_groups[0].security_group_id,
            )

            CfnOutput(self, f'Rstudio-Fargate-EFS-Large-AccessPoint-Id-{instance}', 
                export_name=f'Rstudio-Fargate-EFS-Large-AccessPoint-Id-{instance}',
                value=access_point_rstudio_fg_large.access_point_id,
            )
            
            file_system_rstudio_fg_instant_file_system_id=Fn.import_value(f'Rstudio-Fg-Instant-File-System-Id-{instance}')
            file_system_rstudio_fg_instant_security_group_id=Fn.import_value(f'Rstudio-Fg-Instant-Security-Group-Id-{instance}')
            
            CfnOutput(self, f'Rstudio-Fg-Instant-File-System-Id-{instance}', 
                export_name=f'Rstudio-Fg-Instant-File-System-Id-{instance}',
                value=file_system_rstudio_fg_instant.file_system_id
            )

            CfnOutput(self, f'Rstudio-Fg-Instant-Security-Group-Id-{instance}', 
                export_name=f'Rstudio-Fg-Instant-Security-Group-Id-{instance}',
                value=file_system_rstudio_fg_instant.connections.security_groups[0].security_group_id
            )
            
            
            self.file_system_rstudio_fg_instant_file_system_id = file_system_rstudio_fg_instant.file_system_id
            self.file_system_rstudio_fg_instant_security_group_id = file_system_rstudio_fg_instant.connections.security_groups[0].security_group_id
            self.access_point_id_rstudio_fg_instant=access_point_rstudio_fg_instant.access_point_id

