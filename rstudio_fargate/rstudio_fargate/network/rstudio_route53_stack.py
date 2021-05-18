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
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ssm as ssm
from aws_cdk import aws_route53 as r53
from aws_cdk import aws_certificatemanager as acm
from aws_cdk.core import CfnOutput
from aws_cdk.aws_route53 import RecordType, RecordTarget

class RstudioRoute53Stack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, id: str, pipeline_unique_id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        r53_base_domain = self.node.try_get_context("r53_base_domain")

        if r53_base_domain is None:
            raise ValueError("Please provide base route 53 domain for the build")

        r53_sub_domain = self.node.try_get_context("r53_sub_domain")

        if r53_sub_domain is None:
            raise ValueError("Please provide base route 53 subdomain for the build")

        rstudio_account_ids = self.node.try_get_context("rstudio_account_ids")

        if rstudio_account_ids is None:
            raise ValueError("Please supply the comma separated aws account ids of the rstudio accounts")
            
        
        ssm_route53_delegation_name=f'/poc/hosted_zone_name-{pipeline_unique_id}'
        ssm_route53_delegation_id=f'/poc/hosted_zone_id-{pipeline_unique_id}'     

        principals = []
        
        for account in rstudio_account_ids.split(","):
            principals.append(
                iam.AccountPrincipal(account)
            )
        
        #for principal in principals
        composite_principal=iam.CompositePrincipal(*principals)
         
        imported_base = r53.HostedZone.from_lookup(
            self, 
            "base-hosted-zone", 
            domain_name=r53_base_domain,
            )
            
        poc_domain = f"{r53_sub_domain}." + r53_base_domain

        poc_zone = r53.PublicHostedZone(
                self, 
                "route53-poc-zone",
                zone_name=poc_domain,
                cross_account_zone_delegation_principal=composite_principal
            )
        
        recordset_base = r53.RecordSet(
            self, 
            "ns-record-set-base", 
            zone=imported_base,
            record_type=RecordType.NS,
            target=RecordTarget.from_values(*poc_zone.hosted_zone_name_servers),
            record_name=poc_domain,
            )
            
        # This creates policy to allow sub-account make changes in parent domain
        dns_policy = iam.ManagedPolicy(
            self, 
            'DnsPolicy', 
            statements=[
                iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=['route53:ChangeResourceRecordSets'],
                resources=['arn:aws:route53:::hostedzone/' + poc_zone.hosted_zone_id ],
                    ),
                ],
            )

        delegation_role = iam.Role(
            self, 
            'DelegationRole', 
            role_name=f'DnsDelegation-Rstudio-{pipeline_unique_id}',
            assumed_by=composite_principal,
          )
    
        dns_policy.attach_to_role(delegation_role)
        
        # Retrieve the role so we can grant permissions to it:
        cross_account_role = iam.Role.from_role_arn(
            self, 
            'Cross-Account-Role',
            f'arn:aws:iam::{self.account}:role/ssm_cross_account_role-{pipeline_unique_id}'
            )
                        
        poc_hosted_zone_id=ssm.StringParameter(
            self, 
            "poc_hosted_zone_id",
            allowed_pattern=".*",
            description="POC domain hosted zone id",
            parameter_name=ssm_route53_delegation_id,
            string_value=poc_zone.hosted_zone_id,
            tier=ssm.ParameterTier.ADVANCED
        )
        
        poc_hosted_zone_id.grant_read(cross_account_role)
        
        poc_hosted_zone_name=ssm.StringParameter(
            self, 
            "poc_hosted_zone_name",
            allowed_pattern=".*",
            description="POC domain hosted zone name",
            parameter_name=ssm_route53_delegation_name,
            string_value=poc_zone.zone_name,
            tier=ssm.ParameterTier.ADVANCED
        )
        
        poc_hosted_zone_name.grant_read(cross_account_role)