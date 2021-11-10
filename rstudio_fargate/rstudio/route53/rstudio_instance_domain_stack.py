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

from ..custom.ssm_custom_resource import SSMParameterReader

from aws_cdk import (
    core as cdk,
    aws_iam as iam,
    aws_ssm as ssm,
    aws_route53 as r53,
    aws_certificatemanager as acm,
)
from aws_cdk.aws_route53 import RecordType, RecordTarget


class InstanceDomainStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        instance: str,
        rstudio_account_id: str,
        rstudio_pipeline_account_id: str,
        network_account_id: str,
        ssm_route53_delegation_name: str,
        ssm_route53_delegation_id: str,
        r53_delegation_role_name: str,
        ssm_cross_account_role_name: str,
        ssm_cross_account_lambda_role_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Get the hosted zone id from network account
        ssm_zone_id_reader = SSMParameterReader(
            self,
            id=f"SSM-Reader-Zone-Id-{instance}",
            parameter_name=ssm_route53_delegation_id,
            region=self.region,
            instance=instance,
            rstudio_account_id=rstudio_account_id,
            network_account_id=network_account_id,
            rstudio_pipeline_account_id=rstudio_pipeline_account_id,
            cross_account_id=network_account_id,
            ssm_cross_account_role_name=ssm_cross_account_role_name,
            ssm_cross_account_lambda_role_name=ssm_cross_account_lambda_role_name,
        )

        build_zone_id = ssm_zone_id_reader.get_parameter_value()

        # Get the hosted zone name from network account
        ssm_zone_name_reader = SSMParameterReader(
            self,
            id=f"SSM-Reader-Zone-Name-{instance}",
            parameter_name=ssm_route53_delegation_name,
            region=self.region,
            instance=instance,
            rstudio_account_id=rstudio_account_id,
            network_account_id=network_account_id,
            rstudio_pipeline_account_id=rstudio_pipeline_account_id,
            cross_account_id=network_account_id,
            ssm_cross_account_role_name=ssm_cross_account_role_name,
            ssm_cross_account_lambda_role_name=ssm_cross_account_lambda_role_name,
        )

        build_zone_name = ssm_zone_name_reader.get_parameter_value()

        instance_domain = f"{instance}.{build_zone_name}"

        instance_zone = r53.PublicHostedZone(
            self,
            id=f"route53-instance-zone-{instance}",
            zone_name=instance_domain,
        )

        # The role to assume when peforming domain delegation in the root account

        delegation_role = iam.Role.from_role_arn(
            self,
            id=f"DelegationRole-{instance}",
            role_arn=f"arn:aws:iam::{network_account_id}:role/{r53_delegation_role_name}",
        )

        # Go to the root account and create NS records for delegation

        domain_delegation = r53.CrossAccountZoneDelegationRecord(
            self,
            id=f"delegate-{instance}",
            delegated_zone=instance_zone,
            parent_hosted_zone_id=build_zone_id,
            delegation_role=delegation_role,
        )

        shiny_wildcard_domain = f"*.{instance_domain}"

        shiny_cert = acm.Certificate(
            self,
            id=f"Shiny-Certificate-{instance}",
            domain_name=shiny_wildcard_domain,
            validation=acm.CertificateValidation.from_dns(instance_zone),
        )

        shiny_cert.node.add_dependency(domain_delegation)

        rstudio_domain = f"rstudio.{instance_zone.zone_name}"

        rstudio_zone = r53.PublicHostedZone(
            self,
            id=f"route53-Rstudio-zone-{instance}",
            zone_name=rstudio_domain,
        )

        rstudio_recordset = r53.RecordSet(
            self,
            id=f"ns-rstudio-record-set-{instance}",
            zone=instance_zone,
            record_type=RecordType.NS,
            target=RecordTarget.from_values(*rstudio_zone.hosted_zone_name_servers),
            record_name=rstudio_domain,
        )

        rstudio_recordset.node.add_dependency(rstudio_zone)

        rstudio_wildcard_domain = f"*.{rstudio_domain}"

        rstudio_cert = acm.Certificate(
            self,
            id=f"Rstudio-Certificate-{instance}",
            domain_name=rstudio_wildcard_domain,
            validation=acm.CertificateValidation.from_dns(rstudio_zone),
        )

        rstudio_cert.node.add_dependency(rstudio_zone)

        shiny_domain = f"shiny.{instance_zone.zone_name}"

        shiny_zone = r53.PublicHostedZone(
            self,
            id=f"route53-Shiny-zone-{instance}",
            zone_name=shiny_domain,
        )

        shiny_recordset = r53.RecordSet(
            self,
            id=f"ns-shiny-record-set-{instance}",
            zone=instance_zone,
            record_type=RecordType.NS,
            target=RecordTarget.from_values(*shiny_zone.hosted_zone_name_servers),
            record_name=shiny_domain,
        )

        shiny_recordset.node.add_dependency(shiny_zone)

        # Pass domains and certificates to other stacks

        self.rstudio_hosted_zone_id = rstudio_zone.hosted_zone_id
        self.rstudio_hosted_zone_name = rstudio_zone.zone_name
        self.shiny_hosted_zone_id = shiny_zone.hosted_zone_id
        self.shiny_hosted_zone_name = shiny_zone.zone_name
        self.rstudio_cert_arn = rstudio_cert.certificate_arn
        self.shiny_cert_arn = shiny_cert.certificate_arn
