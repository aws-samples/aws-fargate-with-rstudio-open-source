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

This stack creates the pipeline stage for deployment into the central network account.

"""

from aws_cdk import core as cdk

from .rstudio_route53_stack import RstudioRoute53Stack
from .rstudio_network_account_resources import NetworkAccountResources


class NetworkAccountStage(cdk.Stage):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        instance: str,
        rstudio_account_id: str,
        r53_base_domain: str,
        ssm_route53_delegation_name: str,
        ssm_route53_delegation_id: str,
        r53_delegation_role_name: str,
        ssm_cross_account_role_name: str,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        r53_build = RstudioRoute53Stack(
            self,
            id=f"RstudioRoute53Stack-{instance}",
            instance=instance,
            rstudio_account_id=rstudio_account_id,
            r53_base_domain=r53_base_domain,
            ssm_route53_delegation_name=ssm_route53_delegation_name,
            ssm_route53_delegation_id=ssm_route53_delegation_id,
            r53_delegation_role_name=r53_delegation_role_name,
            ssm_cross_account_role_name=ssm_cross_account_role_name,
            env={
                "account": self.account,
                "region": self.region,
            },
        )

        cross_account_ssm_role_build = NetworkAccountResources(
            self,
            id=f"Network-Account-Resources-{instance}",
            instance=instance,
            rstudio_account_id=rstudio_account_id,
            ssm_cross_account_role_name=ssm_cross_account_role_name,
            env={
                "account": self.account,
                "region": self.region,
            },
        )
