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

This stack creates the hsoted zone to be delegated to rstudio deployment accounts.
The hosted zone is created from a publicly resolvable domain which must pre-exist
in route 53 before running this stack.

"""

from aws_cdk import (
    core as cdk,
    aws_iam as iam,
    aws_ssm as ssm,
    aws_route53 as r53,
    aws_certificatemanager as acm,
)
from aws_cdk.core import CfnOutput
from aws_cdk.aws_route53 import RecordType, RecordTarget


class Route53Stack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        instance: str,
        app_account_id: str,
        r53_base_domain: str,
        r53_sub_domain: str,
        ssm_route53_delegation_name: str,
        ssm_route53_delegation_id: str,
        r53_delegation_role_name: str,
        ssm_cross_account_role_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        principal = []

        principal.append(iam.AccountPrincipal(app_account_id))

        composite_principal = iam.CompositePrincipal(*principal)

        imported_base = r53.HostedZone.from_lookup(
            self,
            id=f"base-hosted-zone-{instance}",
            domain_name=r53_base_domain,
        )

        build_domain = f"{r53_sub_domain}.{r53_base_domain}"

        build_zone = r53.PublicHostedZone(
            self,
            id=f"route53-build-zone-{instance}",
            zone_name=build_domain,
            cross_account_zone_delegation_principal=composite_principal,
        )

        recordset_base = r53.RecordSet(
            self,
            id=f"ns-record-set-base-{instance}",
            zone=imported_base,
            record_type=RecordType.NS,
            target=RecordTarget.from_values(*build_zone.hosted_zone_name_servers),
            record_name=build_domain,
        )

        # This creates policy to allow sub-account make changes in parent domain
        dns_policy = iam.ManagedPolicy(
            self,
            id=f"DnsPolicy-{instance}",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["route53:ChangeResourceRecordSets"],
                    resources=[
                        f"arn:aws:route53:::hostedzone/{build_zone.hosted_zone_id}"
                    ],
                ),
            ],
        )

        delegation_role = iam.Role(
            self,
            id=f"DelegationRole-{instance}",
            role_name=r53_delegation_role_name,
            assumed_by=composite_principal,
        )

        dns_policy.attach_to_role(delegation_role)

        # Retrieve the role so we can grant permissions to it:
        cross_account_role = iam.Role.from_role_arn(
            self,
            id=f"Cross-Account-Role-{instance}",
            role_arn=f"arn:aws:iam::{self.account}:role/{ssm_cross_account_role_name}",
        )

        build_hosted_zone_id = ssm.StringParameter(
            self,
            id=f"build-hosted-zone-id-{instance}",
            allowed_pattern=".*",
            description=f"Application sub domain hosted zone id",
            parameter_name=ssm_route53_delegation_id,
            string_value=build_zone.hosted_zone_id,
            tier=ssm.ParameterTier.ADVANCED,
        )

        build_hosted_zone_id.grant_read(cross_account_role)

        build_hosted_zone_name = ssm.StringParameter(
            self,
            id=f"build-hosted-zone-name-{instance}",
            allowed_pattern=".*",
            description="Application sub domain hosted zone name",
            parameter_name=ssm_route53_delegation_name,
            string_value=build_zone.zone_name,
            tier=ssm.ParameterTier.ADVANCED,
        )

        build_hosted_zone_name.grant_read(cross_account_role)
