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

from ...custom.ssm_custom_resource import SSMParameterReader
from aws_cdk import core as cdk
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ssm as ssm
from aws_cdk import aws_route53 as r53
from aws_cdk import aws_certificatemanager as acm
from aws_cdk.core import CfnOutput
from aws_cdk.aws_route53 import RecordType, RecordTarget

class RstudioInstanceDomainStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, 
                id: str, 
                instance: str,
                rstudio_account_id: str,
                pipeline_unique_id: str,
                **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        
        network_account_id=self.node.try_get_context("network_account_id")
            
        if network_account_id is None:
            raise ValueError("Please provide account id of the network account")

        ssm_route53_delegation_name=f'/poc/hosted_zone_name-{pipeline_unique_id}'
        ssm_route53_delegation_id=f'/poc/hosted_zone_id-{pipeline_unique_id}'

        # Get the hosted zone id from network account
        ssm_zone_id_reader = SSMParameterReader(
            self, 
            'SSM-Reader-Zone-Id' + instance,
            parameter_name=ssm_route53_delegation_id,
            region=self.region,
            instance=instance,
            pipeline_unique_id=pipeline_unique_id,
            rstudio_account_id=rstudio_account_id
            )
            
        poc_zone_id = ssm_zone_id_reader.get_parameter_value()
            
        # Get the hosted zone name from network account
        ssm_zone_name_reader = SSMParameterReader(
            self, 
            'SSM-Reader-Zone-Name' + instance,
            parameter_name=ssm_route53_delegation_name,
            region=self.region,
            instance=instance,
            pipeline_unique_id=pipeline_unique_id,
            rstudio_account_id=rstudio_account_id
            )
            
        poc_zone_name = ssm_zone_name_reader.get_parameter_value()

        instance_domain_fg =f'{instance}.{poc_zone_name}'
            
        instance_zone_fg = r53.PublicHostedZone(
            self, 
            f'route53-instance-fg-zone-{instance}', 
            zone_name=instance_domain_fg,
            )

        #The role to assume when peforming domain delegation in the root account
        delegation_role = iam.Role.from_role_arn(
            self, 
            'DelegationRole', 
            f'arn:aws:iam::{network_account_id}:role/DnsDelegation-Rstudio-{pipeline_unique_id}'
            )

        # Go to the root account and create NS records for delegation
        domain_delegation=r53.CrossAccountZoneDelegationRecord(
            self,
            "delegate" + instance,
            delegated_zone=instance_zone_fg,
            parent_hosted_zone_id=poc_zone_id,
            delegation_role=delegation_role
            )
                        
        wildcard_domain = f'*.{instance_domain_fg}'

        cert = acm.Certificate(
            self, 
            "Certificate" + instance, 
            domain_name=wildcard_domain,
            validation=acm.CertificateValidation.from_dns(instance_zone_fg),
            )        

        cert.node.add_dependency(domain_delegation)

        rstudio_domain_fg =f'rstudio.{instance_zone_fg.zone_name}'

        rstudio_zone_fg = r53.PublicHostedZone(
            self, 
            f'route53-Rstudio-fg-zone-{instance}', 
            zone_name=rstudio_domain_fg,
            )

        rstudio_recordset_fg = r53.RecordSet(
            self, 
            f'ns-rstudio-fg-record-set-{instance}', 
            zone=instance_zone_fg,
            record_type=RecordType.NS,
            target=RecordTarget.from_values(*rstudio_zone_fg.hosted_zone_name_servers),
            record_name=rstudio_domain_fg,
            )

        rstudio_recordset_fg.node.add_dependency(rstudio_zone_fg)

        shiny_domain_fg =f'shiny.{instance_zone_fg.zone_name}'

        shiny_zone_fg = r53.PublicHostedZone(
            self, 
            f'route53-Shiny-fg-zone-{instance}', 
            zone_name=shiny_domain_fg,
            )

        shiny_recordset_fg = r53.RecordSet(
            self, 
            f'ns-shiny-fg-record-set-{instance}', 
            zone=instance_zone_fg,
            record_type=RecordType.NS,
            target=RecordTarget.from_values(*shiny_zone_fg.hosted_zone_name_servers),
            record_name=shiny_domain_fg,
            )

        shiny_recordset_fg.node.add_dependency(shiny_zone_fg)

        CfnOutput(
            self, 
            "RstudioHostedZoneId-" + instance, 
            export_name="Rstudio-hosted-zone-id-" + instance,
            value=rstudio_zone_fg.hosted_zone_id,
            )
        CfnOutput(
            self, 
            "RstudioHostedZoneName-" + instance, 
            export_name='Rstudio-hosted-zone-name-' + instance,
            value=rstudio_zone_fg.zone_name,
            )

        CfnOutput(
            self, 
            "ShinyHostedZoneId-" + instance, 
            export_name="Shiny-hosted-zone-id-" + instance,
            value=shiny_zone_fg.hosted_zone_id,
            )
        CfnOutput(
            self, 
            "ShinyHostedZoneName-" + instance, 
            export_name='Shiny-hosted-zone-name-' + instance,
            value=shiny_zone_fg.zone_name,
            )

        CfnOutput(
            self, 
            'RstudioCertArn-' + instance, 
            export_name="Rstudio-cert-arn-" + instance,
            value=cert.certificate_arn,
            )