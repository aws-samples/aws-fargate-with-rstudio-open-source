#!/usr/bin/env python3

"""
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: MIT-0
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this
 * software and associated documentation files (the "Software"), to deal in the Software
 * without restriction, including without limitation the rights to use, copy, modify,
 * merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
 * INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
 * PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 * OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 """

from aws_cdk import core as cdk
from aws_cdk.core import Fn, CfnOutput,RemovalPolicy,CfnOutput
from aws_cdk.aws_ec2 import Port
from aws_cdk import aws_efs as efs
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_kms as kms

class EfsStack(cdk.Stack):
        def __init__(self, scope: cdk.Construct, id: str, vpc: ec2.Vpc,  **kwargs) -> None:
            super().__init__(scope, id, **kwargs)

            instance = self.node.try_get_context("instance")

            if instance is None:
                raise ValueError("Please pass instance to use via context (dev/prod/...)")

            # Define EFS filesystem to use as destination for Datasync task
            efs_kms_key_alias = kms.Alias.from_alias_name(
                self,
                'Efs-' + instance,   
                alias_name= f'alias/efs-{instance}',
            )

            file_system = efs.FileSystem(
                self, 
                f'destination-file-system-{instance}',
                file_system_name=f'destination-file-system-{instance}',
                vpc=vpc,
                encrypted=True,
                kms_key=efs_kms_key_alias,
                performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
                throughput_mode=efs.ThroughputMode.BURSTING,
                enable_automatic_backups=True,
                removal_policy=RemovalPolicy.DESTROY,
                )

            access_point = efs.AccessPoint(
                self, 
                f'access-point-{instance}',
                file_system=file_system,
                path='/destination-path',
                create_acl= efs.Acl(owner_uid= '1000', owner_gid= '1000', permissions= '755'),      
                )

            self.destination_file_system_id = file_system.file_system_id
            self.destination_file_system_security_group_id = file_system.connections.security_groups[0].security_group_id
            self.destination_file_system_access_point_id=access_point.access_point_id

