#!/usr/bin/env python3

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

import os
import json

from aws_cdk import core as cdk
from aws_cdk.core import App, Aspects
#from cdk_nag import AwsSolutionsChecks
from delegate_zone.pipeline_stack import PipelineStack

app = cdk.App()

# Aspects.of(app).add(AwsSolutionsChecks())

env = cdk.Environment(
    account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
    region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]),
)

instance = app.node.try_get_context("instance")

if instance is None:
    raise ValueError("Please pass instance to use via context (dev/prod/...)")

app_account_id = app.node.try_get_context("app_account_id")

if app_account_id is None:
    raise ValueError("Please supply aws account id where the route53 base domain will be delegated form the central networking account")

network_account_id = app.node.try_get_context("network_account_id")

if network_account_id is None:
    raise ValueError("Please supply the central network account id")

code_repo_name = app.node.try_get_context("code_repo_name")

if code_repo_name is None:
    raise ValueError("Please provide code repository name")

r53_base_domain = app.node.try_get_context("r53_base_domain")

if r53_base_domain is None:
    raise ValueError("Please provide base route 53 domain for the build")

r53_sub_domain = app.node.try_get_context("r53_sub_domain")

if r53_sub_domain is None:
    raise ValueError("Please provide base route 53 subdomain for the build")

sns_email = app.node.try_get_context("sns_email_id")

if sns_email is None:
    raise ValueError(
        "Please provide email id for sending pipeline failure notifications"
    )

ssm_cross_account_role_name = f"zone-delegation-ssm-cross-account-role-{instance}"
ssm_cross_account_lambda_role_name = f"zone-delegation-get-ssm-parameter-lambda-role-{instance}"
ssm_route53_delegation_name = f"/zone-delegation-{instance}/hosted-zone-name"
ssm_route53_delegation_id = f"/zone-delegation-{instance}/hosted-zone-id"
r53_delegation_role_name = f"DnsDelegation-Zone-{instance}"

pipeline_build = PipelineStack(
    app,
    id=f"Zone-Delegation-Pipeline-Stack-{instance}",
    instance=instance,
    app_account_id=app_account_id,
    network_account_id=network_account_id,
    code_repo_name=code_repo_name,
    r53_base_domain=r53_base_domain,
    r53_sub_domain=r53_sub_domain,
    sns_email=sns_email,
    ssm_cross_account_role_name=ssm_cross_account_role_name,
    ssm_cross_account_lambda_role_name=ssm_cross_account_lambda_role_name,
    ssm_route53_delegation_name=ssm_route53_delegation_name,
    ssm_route53_delegation_id=ssm_route53_delegation_id,
    r53_delegation_role_name=r53_delegation_role_name,
    env=env,
)

app.synth()
