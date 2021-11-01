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
    aws_ec2 as ec2,
    aws_secretsmanager as sm,
    aws_rds as rds,
    aws_route53 as r53,
    aws_kms as kms,
)
from aws_cdk.core import (
    RemovalPolicy,
    Duration,
)
import json


class ConnectRdsStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        instance: str,
        vpc: ec2.Vpc,
        db_domain_suffix: str,
        connect_db_key_alias: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        connect_db_encryption_key = kms.Alias.from_alias_name(
            self,
            id=f"Connect-db-kms-key-{instance}",
            alias_name=connect_db_key_alias,
        )

        connect_db_cluster = rds.ServerlessCluster(
            self,
            f"PostgreSQLCluster-Connect-DB-{instance}",
            engine=rds.DatabaseClusterEngine.AURORA_POSTGRESQL,
            cluster_identifier=f"Connect-DB-Cluster-{instance}",
            parameter_group=rds.ParameterGroup.from_parameter_group_name(
                self,
                f"ParameterGroup-Connect-DB-{instance}",
                "default.aurora-postgresql10",
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE),
            scaling=rds.ServerlessScalingOptions(
                auto_pause=Duration.minutes(
                    0
                ),  # default is to pause after 5 minutes of idle time
                min_capacity=rds.AuroraCapacityUnit.ACU_4,  # default is 2 Aurora capacity units (ACUs)
                max_capacity=rds.AuroraCapacityUnit.ACU_32,
            ),
            credentials=rds.Credentials.from_generated_secret(
                "postgres",
                secret_name=f"connect_db_cluster-secret-{instance}",
                encryption_key=connect_db_encryption_key,
            ),
            default_database_name=f"{instance}connectdb",
            storage_encryption_key=connect_db_encryption_key,
        )

        connect_db_cluster.connections.allow_default_port_from_any_ipv4(
            "Allow all connections from all hosts within VPC"
        )

        connect_db_domain_suffix = f"connect.{instance}.{db_domain_suffix}"

        connect_db_zone = r53.PrivateHostedZone(
            self,
            f"route53-connect-db-zone-{instance}",
            zone_name=connect_db_domain_suffix,
            vpc=vpc,
        )

        connect_db_domain = f"connect-db-cluster-{instance}.{connect_db_domain_suffix}"
        connect_db_endpoint = connect_db_cluster.cluster_endpoint.socket_address.split(
            ":"
        )[0]

        connect_db_cname = r53.CnameRecord(
            self,
            f"route53-connect-db-cname-{instance}",
            domain_name=connect_db_endpoint,
            record_name=connect_db_domain,
            zone=connect_db_zone,
        )

        # Pass stack variables to other stacks

        self.connect_db_cluster_secret_arn = connect_db_cluster.secret.secret_arn
