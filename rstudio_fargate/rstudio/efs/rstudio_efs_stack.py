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
    aws_efs as efs,
    aws_kms as kms,
    aws_ec2 as ec2,
)
from aws_cdk.core import RemovalPolicy


class RstudioEfsStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        vpc: ec2.Vpc,
        instance: str,
        rstudio_efs_key_alias: str,
        access_point_path_hourly: str,
        access_point_path_instant: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        rstudio_efs_kms_key_alias = kms.Alias.from_alias_name(
            self,
            id=f"Rstudio-Efs-{instance}",
            alias_name=rstudio_efs_key_alias,
        )

        # File system for sharing data between Shiny and RStudio instances
        file_system_rstudio_shiny_share = efs.FileSystem(
            self,
            id=f"Rstudio-shiny-user-data-share-{instance}",
            file_system_name=f"Rstudio-shiny-share-cont-fs-{instance}",
            vpc=vpc,
            encrypted=True,
            kms_key=rstudio_efs_kms_key_alias,
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
            throughput_mode=efs.ThroughputMode.BURSTING,
            enable_automatic_backups=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        access_point_rstudio_shiny_share = efs.AccessPoint(
            self,
            id=f"Rstudio-shiny-share-access-point-{instance}",
            file_system=file_system_rstudio_shiny_share,
            path="/rstudio-shiny-share-path",
            create_acl=efs.Acl(owner_uid="1000", owner_gid="1000", permissions="755"),
        )

        # Hourly sync file filesystem
        file_system_rstudio_hourly = efs.FileSystem(
            self,
            id=f"Rstudio-cont-user-data-hourly-{instance}",
            file_system_name=f"Rstudio-cont-fs-hourly-{instance}",
            vpc=vpc,
            encrypted=True,
            kms_key=rstudio_efs_kms_key_alias,
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
            throughput_mode=efs.ThroughputMode.BURSTING,
            enable_automatic_backups=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        access_point_rstudio_hourly = efs.AccessPoint(
            self,
            id=f"Rstudio-access-point-hourly-{instance}",
            file_system=file_system_rstudio_hourly,
            path=access_point_path_hourly,
            create_acl=efs.Acl(owner_uid="1000", owner_gid="1000", permissions="755"),
        )

        # Instant sync file system
        file_system_rstudio_instant = efs.FileSystem(
            self,
            id=f"Rstudio-cont-user-data-instant-{instance}",
            file_system_name=f"Rstudio-cont-fs-instant-{instance}",
            vpc=vpc,
            encrypted=True,
            kms_key=rstudio_efs_kms_key_alias,
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
            throughput_mode=efs.ThroughputMode.BURSTING,
            enable_automatic_backups=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        access_point_rstudio_instant = efs.AccessPoint(
            self,
            id=f"Rstudio-access-point-instant-{instance}",
            file_system=file_system_rstudio_instant,
            path=access_point_path_instant,
            create_acl=efs.Acl(owner_uid="1000", owner_gid="1000", permissions="755"),
        )

        # Shiny Shared file system to pass to other stacks
        self.file_system_rstudio_shiny_share_file_system_id = (
            file_system_rstudio_shiny_share.file_system_id
        )
        self.file_system_rstudio_shiny_share_security_group_id = (
            file_system_rstudio_shiny_share.connections.security_groups[
                0
            ].security_group_id
        )
        self.access_point_id_rstudio_shiny_share = (
            access_point_rstudio_shiny_share.access_point_id
        )

        # Hourly sync file system to pass to other stacks
        self.file_system_rstudio_hourly_file_system_id = (
            file_system_rstudio_hourly.file_system_id
        )
        self.file_system_rstudio_hourly_security_group_id = (
            file_system_rstudio_hourly.connections.security_groups[0].security_group_id
        )
        self.access_point_id_rstudio_hourly = (
            access_point_rstudio_hourly.access_point_id
        )

        # Instanct sync file system to pass to other stacks
        self.file_system_rstudio_instant_file_system_id = (
            file_system_rstudio_instant.file_system_id
        )
        self.file_system_rstudio_instant_security_group_id = (
            file_system_rstudio_instant.connections.security_groups[0].security_group_id
        )
        self.access_point_id_rstudio_instant = (
            access_point_rstudio_instant.access_point_id
        )
