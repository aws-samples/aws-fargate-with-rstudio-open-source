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


class PMRdsStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        instance: str,
        vpc: ec2.Vpc,
        db_domain_suffix: str,
        package_db_key_alias: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        package_db_encryption_key = kms.Alias.from_alias_name(
            self,
            id=f"Package-db-kms-key-{instance}",
            alias_name=package_db_key_alias,
        )

        pm_db_cluster = rds.ServerlessCluster(
            self,
            id=f"PostgreSQLCluster-PM-DB-{instance}",
            engine=rds.DatabaseClusterEngine.AURORA_POSTGRESQL,
            cluster_identifier=f"PM-DB-Cluster-{instance}",
            parameter_group=rds.ParameterGroup.from_parameter_group_name(
                self, f"ParameterGroup-PM-DB-{instance}", "default.aurora-postgresql10"
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
                secret_name=f"pm_db_cluster-secret-{instance}",
                encryption_key=package_db_encryption_key,
            ),
            default_database_name=f"{instance}pmdb",
            storage_encryption_key=package_db_encryption_key,
        )

        pm_db_cluster.connections.allow_default_port_from_any_ipv4(
            "Allow all connections from all hosts within VPC"
        )

        pm_usage_db_cluster = rds.ServerlessCluster(
            self,
            id=f"PostgreSQLCluster-PM-Usage-DB-{instance}",
            engine=rds.DatabaseClusterEngine.AURORA_POSTGRESQL,
            cluster_identifier=f"PM-Usage-DB-Cluster-{instance}",
            parameter_group=rds.ParameterGroup.from_parameter_group_name(
                self,
                f"ParameterGroup-PM-Usage-DB-{instance}",
                "default.aurora-postgresql10",
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE),
            scaling=rds.ServerlessScalingOptions(
                auto_pause=Duration.minutes(
                    0
                ),  # default is to pause after 5 minutes of idle time
                min_capacity=rds.AuroraCapacityUnit.ACU_2,  # default is 2 Aurora capacity units (ACUs)
                max_capacity=rds.AuroraCapacityUnit.ACU_32,
            ),
            credentials=rds.Credentials.from_generated_secret(
                "postgres",
                secret_name=f"pm_usage_db_cluster-secret-{instance}",
                encryption_key=package_db_encryption_key,
            ),
            default_database_name=f"{instance}pmusagedb",
            storage_encryption_key=package_db_encryption_key,
        )

        pm_usage_db_cluster.connections.allow_default_port_from_any_ipv4(
            "Allow all connections from all hosts within VPC"
        )

        pm_db_domain_suffix = f"pm.{instance}.{db_domain_suffix}"

        pm_db_zone = r53.PrivateHostedZone(
            self,
            id=f"route53-pm-db-zone-{instance}",
            zone_name=pm_db_domain_suffix,
            vpc=vpc,
        )

        pm_db_domain = f"pm-db-cluster-{instance}.{pm_db_domain_suffix}"
        pm_db_endpoint = pm_db_cluster.cluster_endpoint.socket_address.split(":")[0]

        pm_db_cname = r53.CnameRecord(
            self,
            id=f"route53-pm-db-cname-{instance}",
            domain_name=pm_db_endpoint,
            record_name=pm_db_domain,
            zone=pm_db_zone,
        )

        pm_usage_db_domain = f"pm-usage-db-cluster-{instance}.{pm_db_domain_suffix}"
        pm_usage_db_endpoint = (
            pm_usage_db_cluster.cluster_endpoint.socket_address.split(":")[0]
        )

        pm_usage_db_cname = r53.CnameRecord(
            self,
            id=f"route53-pm-usage-db-cname-{instance}",
            domain_name=pm_usage_db_endpoint,
            record_name=pm_usage_db_domain,
            zone=pm_db_zone,
        )

        # Pass stack variables to other stacks

        self.pm_db_cluster_secret_arn = pm_db_cluster.secret.secret_arn
        self.pm_usage_db_cluster_secret_arn = pm_usage_db_cluster.secret.secret_arn
