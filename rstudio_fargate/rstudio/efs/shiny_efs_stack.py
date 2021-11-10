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


class ShinyEfsStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        vpc: ec2.Vpc,
        instance: str,
        shiny_efs_key_alias: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        rstudio_efs_kms_key_alias = kms.Alias.from_alias_name(
            self,
            id="Rstudio-Efs-{instance}",
            alias_name=shiny_efs_key_alias,
        )

        # Shiny home file system
        file_system_shiny_home = efs.FileSystem(
            self,
            id=f"Rstudio-shiny-cont-user-data-home-{instance}",
            file_system_name=f"Rstudio-shiny-cont-fs-home-{instance}",
            vpc=vpc,
            encrypted=True,
            kms_key=rstudio_efs_kms_key_alias,
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
            throughput_mode=efs.ThroughputMode.BURSTING,
            enable_automatic_backups=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        access_point_shiny_home = efs.AccessPoint(
            self,
            id=f"Shiny-access-point-home-{instance}",
            file_system=file_system_shiny_home,
            path="/shiny-path-home",
            create_acl=efs.Acl(owner_uid="1000", owner_gid="1000", permissions="755"),
        )

        # Instanct sync file system to pass to other stacks
        self.file_system_shiny_home_file_system_id = (
            file_system_shiny_home.file_system_id
        )
        self.file_system_shiny_home_security_group_id = (
            file_system_shiny_home.connections.security_groups[0].security_group_id
        )
        self.access_point_id_shiny_home = access_point_shiny_home.access_point_id
