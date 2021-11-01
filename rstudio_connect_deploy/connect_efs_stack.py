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
    aws_ec2 as ec2,
    aws_kms as kms,
)
from aws_cdk.core import RemovalPolicy
from aws_cdk.aws_ec2 import Port


class ConnectEfsStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        instance: str,
        vpc: ec2.Vpc,
        connect_efs_key_alias: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        connect_efs_kms_key_alias = kms.Alias.from_alias_name(
            self,
            id="Connect-efs-kms-key--{instance}",
            alias_name=connect_efs_key_alias,
        )

        file_system_connect_ec2 = efs.FileSystem(
            self,
            id=f"Connect-cont-ec2-data-{instance}",
            file_system_name=f"Connect-cont-fs-{instance}",
            vpc=vpc,
            encrypted=True,
            kms_key=connect_efs_kms_key_alias,
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
            throughput_mode=efs.ThroughputMode.BURSTING,
            enable_automatic_backups=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        access_point_connect_ec2 = efs.AccessPoint(
            self,
            id=f"Connect-ec2-access-point-{instance}",
            file_system=file_system_connect_ec2,
            path="/connect-ec2",
            create_acl=efs.Acl(owner_uid="999", owner_gid="999", permissions="755"),
        )

        # Pass stack variables to other stacks

        self.connect_file_system_id = file_system_connect_ec2.file_system_id
        self.connect_efs_security_group_id = (
            file_system_connect_ec2.connections.security_groups[0].security_group_id
        )
        self.connect_efs_access_point_id = access_point_connect_ec2.access_point_id
