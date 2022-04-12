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
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
from aws_cdk import core as cdk

from .instance_domain_stack import InstanceDomainStack


class PipelineStage(cdk.Stage):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        instance: str,
        app_account_id: str,
        network_account_id: str,
        ssm_cross_account_role_name: str,
        ssm_cross_account_lambda_role_name: str,
        ssm_route53_delegation_name: str,
        ssm_route53_delegation_id: str,
        r53_delegation_role_name: str,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        env_dict = {
            "account": app_account_id,
            "region": self.region,
        }

        route53_instance_stack_build = InstanceDomainStack(
            self,
            id=f"Route53-Instance-{instance}",
            instance=instance,
            app_account_id=app_account_id,
            network_account_id=network_account_id,
            ssm_route53_delegation_name=ssm_route53_delegation_name,
            ssm_route53_delegation_id=ssm_route53_delegation_id,
            r53_delegation_role_name=r53_delegation_role_name,
            ssm_cross_account_role_name=ssm_cross_account_role_name,
            ssm_cross_account_lambda_role_name=ssm_cross_account_lambda_role_name,
            env=env_dict,
        )
